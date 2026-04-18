"""
子 Agent A — 数据准备（LangChain RunnableLambda）
职责：解析文件、生成 profile + 中文数据准备说明。
"""

from __future__ import annotations

from typing import Any, Dict

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from ..io_loaders import df_profile, load_tabular
from ..llm_factory import chat_model, llm_enabled


def _prep(state: Dict[str, Any]) -> Dict[str, Any]:
    raw: bytes = state["file_bytes"]
    fn: str = state["filename"]
    df, fmt = load_tabular(fn, raw)
    profile = df_profile(df)
    narrative = "（未配置 API Key）已完成结构化摘要。"
    if llm_enabled():
        llm = chat_model(temperature=0.1)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是子 Agent「数据准备」。根据 profile 用中文列出：数据含义推测、列质量、缺失与异常风险；"
                    "勿编造列名。",
                ),
                ("human", "用户目标：{goal}\nprofile：\n{profile}"),
            ]
        )
        chain = prompt | llm | StrOutputParser()
        narrative = chain.invoke(
            {"goal": (state.get("user_query") or "")[:2000], "profile": str(profile)[:12000]}
        ).strip()
    return {
        **state,
        "dataframe": df,
        "file_format": fmt,
        "profile": profile,
        "prep_narrative": narrative,
    }


def run_data_prep_chain() -> RunnableLambda:
    return RunnableLambda(_prep)
