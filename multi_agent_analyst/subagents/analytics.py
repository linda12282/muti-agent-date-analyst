"""
子 Agent B — 分析解读（LangChain）
职责：在 profile + 统计摘要基础上输出业务化解读（中文 Markdown）。
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from ..llm_factory import chat_model, llm_enabled


def _numeric_digest(df: pd.DataFrame) -> str:
    num = df.select_dtypes(include=["number"])
    if num.shape[1] == 0:
        return "无数值列，跳过相关性摘要。"
    lines = ["数值列摘要（describe 节选）："]
    lines.append(num.describe().transpose().head(20).to_string())
    if num.shape[1] >= 2:
        corr = num.corr(numeric_only=True)
        lines.append("\n相关性 Top（|r|>0.5 且非对角）：")
        pairs = []
        cols = list(corr.columns)
        for i, a in enumerate(cols):
            for b in cols[i + 1 :]:
                v = corr.loc[a, b]
                if pd.notna(v) and abs(float(v)) > 0.5:
                    pairs.append((a, b, float(v)))
        pairs.sort(key=lambda x: -abs(x[2]))
        for a, b, v in pairs[:12]:
            lines.append("  %s vs %s : %.3f" % (a, b, v))
    return "\n".join(lines)


def _analytics(state: Dict[str, Any]) -> Dict[str, Any]:
    df: pd.DataFrame = state["dataframe"]
    digest = _numeric_digest(df)
    template = (
        "## 统计摘要\n"
        + digest
        + "\n\n## 子 Agent「分析解读」输出\n"
    )
    if not llm_enabled():
        state["analytics_markdown"] = template + "（未配置 API Key）请配置 OPENAI_API_KEY 后获得大模型深度解读。"
        return state
    llm = chat_model(temperature=0.2)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是子 Agent「分析解读」。结合用户目标与统计摘要，输出中文 Markdown："
                "## 关键发现 ## 风险与异常 ## 可行动建议。避免空话，引用具体列名与数量级。",
            ),
            (
                "human",
                "用户目标：\n{goal}\n\n数据准备说明：\n{prep}\n\n列与预览：\n{profile}\n\n{digest}",
            ),
        ]
    )
    chain = prompt | llm | StrOutputParser()
    body = chain.invoke(
        {
            "goal": (state.get("user_query") or "")[:2000],
            "prep": (state.get("prep_narrative") or "")[:4000],
            "profile": str(state.get("profile", {}))[:8000],
            "digest": digest[:8000],
        }
    )
    state["analytics_markdown"] = template + body.strip()
    return state


def run_analytics_chain() -> RunnableLambda:
    return RunnableLambda(_analytics)
