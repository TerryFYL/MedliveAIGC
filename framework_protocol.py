# -*- coding: utf-8 -*-
"""
MCP风格最简交互协议：定义工具与专家角色的统一调用接口。
- Tool：实现 register() 与 call(params) 两个函数；
- Expert：实现 identify(params)/orchestrate(params)/ensure(params) 等明确职责；
- 所有入参与出参均为 dict，包含以下规范字段：
  request: {"name": str, "version": str, "params": dict, "meta": {"trace_id": str}}
  response: {"ok": bool, "error": str|None, "data": {…}, "meta": {"duration_ms": int}}
"""
import time, uuid


def make_request(name: str, version: str, params: dict) -> dict:
    return {
        "name": name,
        "version": version,
        "params": params or {},
        "meta": {"trace_id": str(uuid.uuid4())}
    }


def make_response(ok: bool, data: dict = None, error: str = None, start_ts: float = None) -> dict:
    dur = int((time.time() - start_ts) * 1000) if start_ts else 0
    return {"ok": ok, "error": error, "data": data or {}, "meta": {"duration_ms": dur}}


# 三位专家角色的职责模板
class IntentExpert:
    """意图识别专家：解析任务文本，选择需要的工具与步骤"""
    NAME = "intent_expert"
    VERSION = "v1"

    def identify(self, params: dict) -> dict:
        text = (params.get("text") or "").lower()
        intents = []
        if "图片" in params.get("text", "") or "image" in text:
            intents.append("extract_images_from_pdf")
        if "pdf" in text:
            intents.append("extract_text_from_pdf")
        if "生成" in params.get("text", "") and "markdown" in text:
            intents.append("compose_markdown_digest")
        return {"intents": intents or ["extract_images_from_pdf"], "confidence": 0.8}


class OrchestratorExpert:
    """总调度专家：串联工具，保证成功路线与失败回退"""
    NAME = "orchestrator"
    VERSION = "v1"

    def orchestrate(self, params: dict, tools: dict) -> dict:
        start = time.time()
        pdf_path = params.get("pdf_path")
        out_dir = params.get("out_dir")
        dpi = params.get("dpi", 200)
        # 工具以函数形式传入，直接调用
        tool_call = tools["dotsocr_pdf"]
        try:
            resp_pdf = tool_call({"pdf_path": pdf_path, "out_dir": out_dir, "dpi": dpi, "image_extract": True})
        except Exception as e:
            return make_response(False, error=f"dotsocr_pdf异常: {e}", start_ts=start)
        if not resp_pdf.get("ok"):
            return make_response(False, error=f"dotsocr_pdf失败: {resp_pdf.get('error')}", start_ts=start)
        images = resp_pdf["data"].get("images", [])
        text_path = resp_pdf["data"].get("text_path")
        return make_response(True, data={"images": images, "text_path": text_path}, start_ts=start)


class AutoInstallerExpert:
    """自动安装与代码保障专家：确保依赖与必要文件存在"""
    NAME = "autoinstaller"
    VERSION = "v1"

    def ensure(self, params: dict) -> dict:
        start = time.time()
        import importlib, subprocess, sys
        pkgs = params.get("packages", [])
        installed = []
        for p in pkgs:
            try:
                importlib.import_module(p)
                installed.append((p, "ok"))
            except Exception:
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", p])
                    installed.append((p, "installed"))
                except Exception as e:
                    return make_response(False, error=f"安装失败: {p} -> {e}", start_ts=start)
        return make_response(True, data={"installed": installed}, start_ts=start)