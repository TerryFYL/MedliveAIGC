# -*- coding: utf-8 -*-
import os, time, hashlib, requests, re
from typing import List, Tuple

PDF_PATH = r"e:\BaiduSyncdisk\博士后经历\内部0_AIGC平台搭建\04AIGCFrameWork\knowledgedata\P3-P9,P10-4,P12-3,P13-16 中华医学会糖尿病学分会. 中国糖尿病防治指南(2024版) [J]. 中华糖尿病杂志, 2024.pdf"
OUTPUT_MD = r"e:\BaiduSyncdisk\博士后经历\内部0_AIGC平台搭建\04AIGCFrameWork\指南解读_中国糖尿病防治指南2024_图文版.md"
IMG_DIR = r"e:\BaiduSyncdisk\博士后经历\内部0_AIGC平台搭建\04AIGCFrameWork\digest_images"
MODEL_KEY = "model-20250811154752-vr0n93"
API_KEY = "crqGkYW3wbYMQ9P"  # 取自 test_all_models.py


def extract_pdf_text(pdf_path) -> List[Tuple[int, str]]:
    try:
        import fitz
        doc = fitz.open(pdf_path)
        pages = []
        for i in range(len(doc)):
            t = doc[i].get_text("text")
            t = re.sub(r"\s+\n", "\n", t)
            pages.append((i + 1, t.strip()))
        return pages
    except Exception as e:
        try:
            from PyPDF2 import PdfReader
            r = PdfReader(pdf_path)
            pages = []
            for i, p in enumerate(r.pages):
                t = p.extract_text() or ""
                pages.append((i + 1, t.strip()))
            return pages
        except Exception as e2:
            raise RuntimeError(f"无法提取PDF文本: {e} / {e2}")


def extract_pdf_images(pdf_path, img_dir, max_images=8) -> List[str]:
    os.makedirs(img_dir, exist_ok=True)
    saved = []
    try:
        import fitz
        doc = fitz.open(pdf_path)
        cnt = 0
        for pi in range(len(doc)):
            if cnt >= max_images:
                break
            page = doc[pi]
            for img in page.get_images(full=True):
                if cnt >= max_images:
                    break
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                if pix.n > 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                if pix.width < 200 or pix.height < 200:
                    continue
                fn = os.path.join(img_dir, f"page{pi + 1}_img{xref}.png")
                pix.save(fn)
                saved.append(fn)
                cnt += 1
    except Exception as e:
        print(f"图片提取失败: {e}")
    return saved


def build_prompt(section: str, pages_hint: str = "") -> str:
    return (
        f"角色：临床指南解读专家（内分泌）\n"
        f"目标：基于《2024中国糖尿病防治指南》原文撰写‘图文并茂’长文解读。\n"
        f"约束：仅依提供片段撰写；不得臆断；需标注页码（如[p{pages_hint}]）；中文输出、可执行；Markdown结构化。\n"
        f"请生成本节《{section}》解读，包含：执行摘要、核心更新、诊断/评估、治疗路径、特殊人群、随访监测、风险红旗、证据与引用。\n"
    )


def call_gpt5(question: str) -> Tuple[bool, str]:
    ts = int(time.time())
    params = {"project_id": "131", "timestamp": str(ts), "user_id": "3790046"}
    raw = "".join(f"{k}{params[k]}" for k in sorted(params.keys()))
    inner = hashlib.md5(raw.encode()).hexdigest()
    token = hashlib.md5((inner + API_KEY).encode()).hexdigest().upper()
    url = "https://chat001.medlive.cn/api/project/chat"
    data = {
        "project_id": 131,
        "timestamp": ts,
        "user_id": "3790046",
        "question": question,
        "chat_id": "",
        "stream": 0,
        "model_key": MODEL_KEY,
    }
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.post(url, data=data, headers=headers, timeout=60)
        if r.status_code == 200:
            js = r.json()
            if js.get("status") is True:
                return True, js.get("data", {}).get("answer", "")
            return False, f"API错误: {js.get('message', '未知')}"
        return False, f"HTTP错误: {r.status_code}"
    except Exception as e:
        return False, f"异常: {e}"


def assemble_markdown(title: str, sections: List[Tuple[str, str]], images: List[str]) -> str:
    md = [f"# {title}", "", 
          "> 依据《2024中国糖尿病防治指南》原文生成，内容附页码引用；图片为指南原图或示意图。", ""]
    for i, (name, content) in enumerate(sections, start=1):
        md.append(f"---\n\n## {i}. {name}\n")
        md.append(content)
        if i <= len(images):
            img_path = images[i - 1].replace("\\", "/")
            md.append(f"\n![{name}示意图]({img_path})")
        md.append("\n")
    return "\n".join(md)


def generate(pdf_path: str, output_md: str, img_dir: str):
    pages = extract_pdf_text(pdf_path)
    ranges = [
        ("总体解读与核心更新", 1, 6),
        ("诊断与评估", 7, 15),
        ("生活方式与初始治疗", 16, 25),
        ("药物治疗路径（T2D）", 26, 45),
        ("并发症与合并症管理", 46, 65),
        ("随访监测与指标", 66, 80),
    ]
    sections = []
    for name, s, e in ranges:
        chosen = [t for (p, t) in pages if s <= p <= e and t]
        if not chosen:
            continue
        text = "\n\n".join(chosen)
        prompt = build_prompt(name, pages_hint=f"{s}-{e}")
        full_q = f"{prompt}\n\n=== 原文片段（p{s}-{e}）===\n{text[:6000]}"
        ok, ans = call_gpt5(full_q)
        if not ok:
            ans = f"本节生成失败：{ans}"
        sections.append((name, ans))
        time.sleep(1)
    images = extract_pdf_images(pdf_path, img_dir, max_images=6)
    md = assemble_markdown("中国糖尿病防治指南（2024版）临床解读（图文版）", sections, images)
    with open(output_md, "w", encoding="utf-8") as f:
        f.write(md)
    return output_md, images


if __name__ == "__main__":
    pdf = PDF_PATH
    out = OUTPUT_MD
    img_dir = IMG_DIR
    p, imgs = generate(pdf, out, img_dir)
    print(f"✅ 已生成: {p}")
    if imgs:
        print("🖼️ 图片:")
        for i in imgs:
            print(" -", i)