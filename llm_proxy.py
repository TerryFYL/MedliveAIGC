# -*- coding: utf-8 -*-
"""
LLM代理：封装Medlive GPT-5调用。
- 提供 ask(question: str) -> (ok: bool, answer: str)
- 复用 generate_diabetes_digest.py 中的鉴权逻辑与模型Key
"""
import time, hashlib, requests

MODEL_KEY = "model-20250811154752-vr0n93"
API_KEY = "crqGkYW3wbYMQ9P"  # 取自 test_all_models.py


def ask(question: str, timeout: int = 60):
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
        r = requests.post(url, data=data, headers=headers, timeout=timeout)
        if r.status_code == 200:
            js = r.json()
            if js.get("status") is True:
                return True, js.get("data", {}).get("answer", "")
            return False, f"API错误: {js.get('message', '未知')}"
        return False, f"HTTP错误: {r.status_code}"
    except Exception as e:
        return False, f"异常: {e}"