# -*- coding: utf-8 -*-
"""MCP风格总调度：调用意图识别专家 + 自动安装专家 + dotsocr工具。
使用方式：
python mcp_orchestrator.py --pdf "<pdf_path>" --out_dir "<out_dir>" --dpi 200
"""
import os, json
from framework_protocol import IntentExpert, OrchestratorExpert, AutoInstallerExpert
from dotsocr import remote_tools, local_pdf_tool


def run(pdf_path: str, out_dir: str, dpi: int = 200):
    # 自动安装（确保requests与pymupdf可用）
    auto = AutoInstallerExpert()
    auto.ensure({"packages": ["requests", "pymupdf", "PyPDF2"]})

    # 意图识别
    intent = IntentExpert().identify({"text": "从PDF中提取图片与文本并用于生成图文版"})

    # 注册工具并调度（远端优先，失败回退本地）
    tools = {"dotsocr_pdf": remote_tools.call_pdf}
    orch = OrchestratorExpert()
    resp = orch.orchestrate({"pdf_path": pdf_path, "out_dir": out_dir, "dpi": dpi}, tools)
    if not resp.get("ok"):
        # 远端失败，回退到本地
        resp = local_pdf_tool.call({"pdf_path": pdf_path, "out_dir": out_dir})
        # 将本地返回适配成Orchestrator的统一格式
        if resp.get("ok"):
            data = resp.get("data", {})
            return {"ok": True, "error": None, "data": {"images": data.get("images", []), "text_path": data.get("text_path")}}
        return resp
    return resp


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--dpi", type=int, default=200)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    result = run(args.pdf, args.out_dir, args.dpi)
    print(json.dumps(result, ensure_ascii=False, indent=2))