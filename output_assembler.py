# -*- coding: utf-8 -*-
"""
输出整理专家：将调度产出的图片与文本/或PDF源片段，组织为结构化Markdown。
- 方法 compose(params) -> MCP响应：
  params: {
    title: str,
    pdf_path: str,
    text_path: str|None,
    image_dir: str|None,
    images: list[str]|None,
    output_md: str,
    section_ranges: list[tuple[str,int,int]]|None
  }
"""
import os, re, time
from typing import List, Tuple
from framework_protocol import make_response
from llm_proxy import ask as llm_ask


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
    except Exception:
        from PyPDF2 import PdfReader
        r = PdfReader(pdf_path)
        pages = []
        for i, p in enumerate(r.pages):
            t = p.extract_text() or ""
            pages.append((i + 1, t.strip()))
        return pages


def load_text_file(text_path: str) -> str:
    try:
        with open(text_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def build_prompt(section: str, pages_hint: str = "") -> str:
    return (
        f"角色：临床指南解读专家（内分泌）\n"
        f"目标：基于《2024中国糖尿病防治指南》原文撰写‘图文并茂’长文解读。\n"
        f"约束：仅依提供片段撰写；不得臆断；需标注页码（如[p{pages_hint}]）；中文输出、可执行；Markdown结构化。\n"
        f"请生成本节《{section}》解读，包含：执行摘要、核心更新、诊断/评估、治疗路径、特殊人群、随访监测、风险红旗、证据与引用。\n"
    )


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


class OutputAssemblerExpert:
    NAME = "output_assembler"
    VERSION = "v1"

    def compose(self, params: dict) -> dict:
        start_ts = time.time()
        title = params.get("title") or "中国糖尿病防治指南（2024版）临床解读（图文版）"
        pdf_path = params.get("pdf_path")
        text_path = params.get("text_path")
        image_dir = params.get("image_dir")
        images = params.get("images") or []
        output_md = params.get("output_md")
        section_ranges = params.get("section_ranges") or [
            ("总体解读与核心更新", 1, 6),
            ("诊断与评估", 7, 15),
            ("生活方式与初始治疗", 16, 25),
            ("药物治疗路径（T2D）", 26, 45),
            ("并发症与合并症管理", 46, 65),
            ("随访监测与指标", 66, 80),
        ]
        if not output_md:
            return make_response(False, error="缺少output_md文件路径", start_ts=start_ts)

        # 文本准备：优先使用text_path；不足则回退到PDF抽取
        src_text = text_path and load_text_file(text_path) or ""
        use_pdf = (not src_text) or (len(src_text) < 1000)
        if use_pdf:
            if not pdf_path:
                return make_response(False, error="text不足且未提供pdf_path用于回退文本抽取", start_ts=start_ts)
            pages = extract_pdf_text(pdf_path)
        else:
            # 将整段文本视为一个页范围片段，避免丢失
            pages = [(1, src_text)]

        # 图片收集
        if not images and image_dir:
            try:
                images = [os.path.join(image_dir, f) for f in os.listdir(image_dir) if f.lower().endswith(".png")]
                images.sort()
            except Exception:
                images = []

        sections: List[Tuple[str, str]] = []
        for name, s, e in section_ranges:
            chosen = [t for (p, t) in pages if s <= p <= e and t] if use_pdf else [pages[0][1]]
            if not chosen:
                # 无片段时给出占位，避免空节
                sections.append((name, f"本节未找到可用片段（p{s}-{e}），请参考原文。"))
                continue
            text = "\n\n".join(chosen)
            prompt = build_prompt(name, pages_hint=f"{s}-{e}")
            full_q = f"{prompt}\n\n=== 原文片段（p{s}-{e}）===\n{text[:6000]}"
            ok, ans = llm_ask(full_q)
            if not ok:
                ans = f"本节生成失败：{ans}"
            sections.append((name, ans))
            time.sleep(1)

        md = assemble_markdown(title, sections, images)
        os.makedirs(os.path.dirname(output_md) or ".", exist_ok=True)
        with open(output_md, "w", encoding="utf-8") as f:
            f.write(md)
        return make_response(True, data={"output_md": output_md, "images": images}, start_ts=start_ts)