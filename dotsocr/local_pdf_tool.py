# -*- coding: utf-8 -*-
"""本地PDF提取工具（协议兼容版）
- 使用 PyMuPDF(Pymupdf) 或 PyPDF2 进行文本与图片提取，返回与远端dotsocr一致的输出结构
"""
import os, time, re
from typing import Dict, Any, List
from framework_protocol import make_response

NAME = "local_pdf"
VERSION = "v1"


def _extract_text(pdf_path: str) -> str:
    try:
        import fitz
        doc = fitz.open(pdf_path)
        pages = []
        for i in range(len(doc)):
            t = doc[i].get_text("text")
            t = re.sub(r"\s+\n", "\n", t)
            pages.append(t.strip())
        return "\n\n".join(pages)
    except Exception:
        try:
            from PyPDF2 import PdfReader
            r = PdfReader(pdf_path)
            pages = []
            for p in r.pages:
                t = p.extract_text() or ""
                pages.append(t.strip())
            return "\n\n".join(pages)
        except Exception:
            return ""


def _extract_images(pdf_path: str, out_dir: str, max_images: int = 10) -> List[str]:
    paths = []
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
                fn = os.path.join(out_dir, f"page{pi + 1}_img{xref}.png")
                pix.save(fn)
                paths.append(fn)
                cnt += 1
    except Exception:
        pass
    return paths


def call(params: Dict[str, Any]) -> Dict[str, Any]:
    start = time.time()
    pdf_path = params.get("pdf_path")
    out_dir = params.get("out_dir")
    os.makedirs(out_dir, exist_ok=True)
    txt = _extract_text(pdf_path)
    text_path = None
    if txt:
        text_path = os.path.join(out_dir, "extract_text_local.txt")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(txt)
    images = _extract_images(pdf_path, out_dir, max_images=10)
    return make_response(True, data={"images": images, "text_path": text_path}, start_ts=start)