"""
子 Agent C — 可视化看板（Plotly + 离线 HTML）
职责：生成可交互 Plotly 页面，作为「作品看板」主入口。
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from ..llm_factory import chat_model, llm_enabled


def _pick_numeric(df: pd.DataFrame) -> List[str]:
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


def _pick_categorical(df: pd.DataFrame, max_card: int = 24) -> List[str]:
    out = []
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            continue
        try:
            n = df[c].nunique(dropna=True)
        except Exception:
            continue
        if n <= max_card and n >= 2:
            out.append(c)
    return out[:5]


def _viz(state: Dict[str, Any]) -> Dict[str, Any]:
    df: pd.DataFrame = state["dataframe"]
    session_dir: Path = state["session_dir"]
    figures_html: List[str] = []

    nums = _pick_numeric(df)
    cats = _pick_categorical(df)

    if nums:
        c0 = nums[0]
        try:
            fig1 = px.histogram(df.dropna(subset=[c0]), x=c0, nbins=min(40, max(10, int(len(df) ** 0.5))), title="分布：%s" % c0)
            figures_html.append(fig1.to_html(include_plotlyjs="cdn", full_html=False))
        except Exception:
            pass

    if len(nums) >= 2:
        d2 = df[[nums[0], nums[1]]].dropna()
        if len(d2) > 1:
            fig2 = px.scatter(d2, x=nums[0], y=nums[1], title="散点：%s vs %s" % (nums[0], nums[1]))
            figures_html.append(fig2.to_html(include_plotlyjs=False, full_html=False))
    if cats and nums:
        cat, val = cats[0], nums[0]
        sub = df.groupby(cat, dropna=True)[val].mean().reset_index().sort_values(val, ascending=False).head(15)
        fig3 = px.bar(sub, x=cat, y=val, title="分组均值：%s（按 %s）" % (val, cat))
        figures_html.append(fig3.to_html(include_plotlyjs=False, full_html=False))

    if len(nums) >= 3:
        z = df[nums[: min(8, len(nums))]].corr(numeric_only=True)
        fig4 = go.Figure(
            data=go.Heatmap(z=z.values, x=list(z.columns), y=list(z.index), colorscale="RdBu", zmid=0)
        )
        fig4.update_layout(title="数值列相关热力图（节选）")
        figures_html.append(fig4.to_html(include_plotlyjs=False, full_html=False))

    if not figures_html:
        fig = px.scatter(x=[0, 1], y=[0, 1], title="数据无可视化列，占位图")
        figures_html.append(fig.to_html(include_plotlyjs="cdn", full_html=False))

    board_path = session_dir / "dashboard.html"
    narrative = ""
    if llm_enabled():
        llm = chat_model(temperature=0.25)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是子 Agent「可视化说明」。用中文 3～6 句说明下面看板应如何阅读、亮点图卡、注意误导；"
                    "不要重复统计细节。",
                ),
                ("human", "用户目标：{goal}\n已生成图卡数：{n}\n分析节选：\n{clip}"),
            ]
        )
        chain = prompt | llm | StrOutputParser()
        narrative = chain.invoke(
            {
                "goal": (state.get("user_query") or "")[:1500],
                "n": len(figures_html),
                "clip": (state.get("analytics_markdown") or "")[:3000],
            }
        ).strip()
    else:
        narrative = "（未配置 API Key）以下为自动生成的交互图卡。"

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>多 Agent 数据分析师 — 交互看板</title>
<style>
body{font-family:Segoe UI,system-ui,sans-serif;margin:24px;background:#0f172a;color:#e2e8f0;}
h1{font-size:1.35rem;color:#38bdf8;}
section{background:#1e293b;border-radius:12px;padding:16px;margin-bottom:20px;}
.viz{margin-top:12px;}
</style>
</head>
<body>
<h1>作品看板 · 会话 %s</h1>
<section><h2>看板导读（子 Agent C）</h2><p>%s</p></section>
%s
</body>
</html>""" % (
        state.get("session_id", ""),
        html.escape(narrative),
        "\n".join('<section class="viz">%s</section>' % h for h in figures_html),
    )
    board_path.write_text(html, encoding="utf-8")

    manifest = {
        "session_id": state.get("session_id"),
        "charts": len(figures_html),
        "columns": list(df.columns),
    }
    (session_dir / "viz_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    state["dashboard_path"] = str(board_path)
    state["viz_narrative"] = narrative
    return state


def run_viz_chain() -> RunnableLambda:
    return RunnableLambda(_viz)
