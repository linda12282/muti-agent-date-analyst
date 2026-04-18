"""LangChain ChatOpenAI 工厂（兼容 SiliconFlow 等网关）。"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from langchain_openai import ChatOpenAI


def chat_model(*, temperature: float = 0.15, model: Optional[str] = None) -> ChatOpenAI:
    m = (model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")).strip()
    kwargs: Dict[str, Any] = {
        "model": m,
        "temperature": temperature,
        "timeout": 90,
        "api_key": os.getenv("OPENAI_API_KEY", "").strip() or None,
    }
    base = os.getenv("OPENAI_BASE_URL", "").strip()
    if base:
        kwargs["base_url"] = base
    return ChatOpenAI(**kwargs)


def llm_enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())
