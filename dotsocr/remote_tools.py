# -*- coding: utf-8 -*-
"""
远端 dots-ocr 工具（协议化）：与 test_image_ocr.py / test_pdf_ocr.py 保持一致的接口调用。
- call_pdf(params): 上传PDF，支持 image_extract 与 dpi，保存返回内容到 out_dir。
- call_image(params): 上传图片，支持 image_extract，保存返回内容到 out_dir。
返回统一结构：{"ok": bool, "error": str|None, "data": {"images": list[str], "text_path": str|None}}
"""
import os, time, json, zipfile
from typing import List

import requests

DOTS_URL = "http://dots-ocr.mlproject.cn/extract"


def _save_response_payload(resp: requests.Response, out_dir: str, base_name: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    ctype = resp.headers.get("Content-Type", "")
    images: List[str] = []
    text_path = None

    try:
        # JSON优先解析
        if "application/json" in ctype:
            js = resp.json()
            # 尝试多种字段约定
            if isinstance(js, dict):
                # 可能返回 text 或 texts
                text = js.get("text") or js.get("ocr_text") or js.get("data") if isinstance(js.get("data"), str) else None
                if text:
                    text_path = os.path.join(out_dir, f"{base_name}_remote_text.txt")
                    with open(text_path, "w", encoding="utf-8") as f:
                        f.write(text)
                # 可能返回 images(base64) 或 文件名列表（服务端落地路径不可用时忽略）
                if isinstance(js.get("images"), list):
                    # 若为base64，本工具不解码，服务端一般不会直接返回base64
                    # 这里只记录占位，不保存
                    pass
            return {"images": images, "text_path": text_path}
        # ZIP或二进制：保存并尝试解压
        if "application/zip" in ctype or "application/octet-stream" in ctype:
            zip_path = os.path.join(out_dir, f"{base_name}_remote_images.zip")
            with open(zip_path, "wb") as f:
                f.write(resp.content)
            try:
                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(out_dir)
                # 收集解压后的图片
                for root, _, files in os.walk(out_dir):
                    for fn in files:
                        if fn.lower().endswith(('.png', '.jpg', '.jpeg')):
                            images.append(os.path.join(root, fn))
            except Exception:
                pass
            return {"images": images, "text_path": text_path}
        # 文本：直接落地
        text_path = os.path.join(out_dir, f"{base_name}_remote_text.txt")
        try:
            body = resp.text
        except Exception:
            body = ""
        with open(text_path, "w", encoding="utf-8", errors="ignore") as f:
            f.write(body)
        return {"images": images, "text_path": text_path}
    except Exception as e:
        return {"images": images, "text_path": text_path}


def call_pdf(params: dict) -> dict:
    pdf_path = params.get("pdf_path")
    out_dir = params.get("out_dir") or os.path.dirname(pdf_path) or "."
    dpi = params.get("dpi", 200)
    image_extract = params.get("image_extract", True)
    start = time.time()
    if not pdf_path or not os.path.exists(pdf_path):
        return {"ok": False, "error": "pdf_path不存在", "data": {}, "meta": {"duration_ms": int((time.time()-start)*1000)}}
    files=[('file',(os.path.basename(pdf_path), open(pdf_path,'rb'), 'application/pdf'))]
    payload = {"image_extract": str(bool(image_extract)).lower(), "dpi": str(dpi)}
    try:
        resp = requests.request("POST", DOTS_URL, headers={}, data=payload, files=files, timeout=60)
        parsed = _save_response_payload(resp, out_dir, os.path.splitext(os.path.basename(pdf_path))[0])
        return {"ok": True, "error": None, "data": {"images": parsed.get("images", []), "text_path": parsed.get("text_path")}, "meta": {"duration_ms": int((time.time()-start)*1000)}}
    except Exception as e:
        return {"ok": False, "error": f"远端PDF提取异常: {e}", "data": {}, "meta": {"duration_ms": int((time.time()-start)*1000)}}


def call_image(params: dict) -> dict:
    image_path = params.get("image_path")
    out_dir = params.get("out_dir") or os.path.dirname(image_path) or "."
    start = time.time()
    if not image_path or not os.path.exists(image_path):
        return {"ok": False, "error": "image_path不存在", "data": {}, "meta": {"duration_ms": int((time.time()-start)*1000)}}
    files=[('file',(os.path.basename(image_path), open(image_path,'rb'), 'application/images'))]
    payload = {"image_extract": "true"}
    try:
        resp = requests.request("POST", DOTS_URL, headers={}, data=payload, files=files, timeout=60)
        parsed = _save_response_payload(resp, out_dir, os.path.splitext(os.path.basename(image_path))[0])
        return {"ok": True, "error": None, "data": {"images": parsed.get("images", []), "text_path": parsed.get("text_path")}, "meta": {"duration_ms": int((time.time()-start)*1000)}}
    except Exception as e:
        return {"ok": False, "error": f"远端图片提取异常: {e}", "data": {}, "meta": {"duration_ms": int((time.time()-start)*1000)}}