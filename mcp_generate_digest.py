# -*- coding: utf-8 -*-
"""
MCP一体化生成管线：
1) 自动安装依赖
2) 总调度专家提取PDF图片与文本（远端优先，失败回退本地）
3) 输出整理专家调用LLM生成结构化Markdown

使用：
python mcp_generate_digest.py --pdf <path_to_pdf> --out_dir <images_dir> --output_md <md_path> --dpi 200
"""
import os, json
from framework_protocol import AutoInstallerExpert
from mcp_orchestrator import run as orchestrate_extract
from output_assembler import OutputAssemblerExpert


def pipeline(pdf: str, out_dir: str, output_md: str, dpi: int = 200):
    # 1) 自动安装
    auto = AutoInstallerExpert()
    ensure = auto.ensure({"packages": ["requests", "pymupdf", "PyPDF2"]})
    if not ensure.get("ok"):
        return ensure

    # 2) 调度提取
    os.makedirs(out_dir, exist_ok=True)
    resp = orchestrate_extract(pdf, out_dir, dpi)
    if not resp.get("ok"):
        return resp
    images = resp["data"].get("images", [])
    text_path = resp["data"].get("text_path")

    # 3) 输出整理
    assembler = OutputAssemblerExpert()
    assemble_resp = assembler.compose({
        "title": "中国糖尿病防治指南（2024版）临床解读（图文版）",
        "pdf_path": pdf,
        "text_path": text_path,
        "image_dir": out_dir,
        "images": images,
        "output_md": output_md,
    })
    return assemble_resp


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--output_md", required=True)
    ap.add_argument("--dpi", type=int, default=200)
    args = ap.parse_args()
    result = pipeline(args.pdf, args.out_dir, args.output_md, args.dpi)
    print(json.dumps(result, ensure_ascii=False, indent=2))