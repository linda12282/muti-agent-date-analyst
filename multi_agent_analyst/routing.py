"""主 Agent 路由：闲聊 / 纯文本分析 / 数据文件全链路。"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from .llm_factory import chat_model, llm_enabled


class AnalysisMode(str, Enum):
    smalltalk = "smalltalk"
    text_only = "text_only"
    data_pipeline = "data_pipeline"


class RouteDecision(BaseModel):
    mode: AnalysisMode = Field(description="smalltalk=寒暄闲聊; text_only=无文件时的文本/观点分析; data_pipeline=有表格文件时的完整数分+看板")


def _rule_route(user_text: str, has_file: bool) -> RouteDecision:
    t = (user_text or "").strip()
    low = t.lower()
    if has_file:
        return RouteDecision(mode=AnalysisMode.data_pipeline)
    if len(t) < 2:
        return RouteDecision(mode=AnalysisMode.smalltalk)
    hi = ("你好", "您好", "hi", "hello", "在吗", "谢谢", "再见", "早上好", "晚上好")
    if any(h in low for h in hi) and len(t) < 40:
        return RouteDecision(mode=AnalysisMode.smalltalk)
    if re.search(r"(分析|总结|归纳|解读|观点|建议|评价|含义)", t):
        return RouteDecision(mode=AnalysisMode.text_only)
    return RouteDecision(mode=AnalysisMode.text_only)


def route_user_intent(user_text: str, has_file: bool) -> RouteDecision:
    if has_file:
        return RouteDecision(mode=AnalysisMode.data_pipeline)
    if not llm_enabled():
        return _rule_route(user_text, has_file)
    llm = chat_model(temperature=0)
    structured = llm.with_structured_output(RouteDecision)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是路由子模块。根据用户是否上传了数据文件与文本内容，选择唯一模式："
                "smalltalk（寒暄、感谢、无实质分析需求）；"
                "text_only（无文件，但用户需要观点提炼、文案解读、开放讨论等）；"
                "data_pipeline（用户上传了表格/数据文件，需要统计与可视化）。"
                "无文件时绝不选 data_pipeline。",
            ),
            ("human", "是否附带数据文件：{has_file}\n用户输入：\n{text}"),
        ]
    )
    chain = prompt | structured
    try:
        out = chain.invoke({"has_file": "是" if has_file else "否", "text": user_text[:4000]})
        if isinstance(out, RouteDecision):
            if not has_file and out.mode == AnalysisMode.data_pipeline:
                return RouteDecision(mode=AnalysisMode.text_only)
            return out
    except Exception:
        pass
    return _rule_route(user_text, has_file)
