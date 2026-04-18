"""
主 Agent：用户交互 + 任务拆解 + 分发三个子 Agent（数据准备 / 分析解读 / 可视化看板）。
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .chains_text import smalltalk_reply, text_analysis_reply
from .config import OUTPUT_SESSIONS, public_base_url
from .routing import AnalysisMode, route_user_intent
from .subagents import run_analytics_chain, run_data_prep_chain, run_viz_chain


def _json_safe(obj: Any) -> Any:
    import math

    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


@dataclass
class AnalystResult:
    session_id: str
    mode: str
    reply_markdown: str
    dashboard_url: Optional[str] = None
    report_url: Optional[str] = None
    trace: List[str] = field(default_factory=list)


class MainAnalystOrchestrator:
    """主 Agent：路由 + 子 Agent 编排（LangChain Runnable 在子模块内）。"""

    def __init__(self) -> None:
        self._prep = run_data_prep_chain()
        self._analytics = run_analytics_chain()
        self._viz = run_viz_chain()

    def run(
        self,
        user_query: str,
        file_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
    ) -> AnalystResult:
        has_file = bool(file_bytes and filename)
        decision = route_user_intent(user_query or "", has_file)
        trace: List[str] = ["主Agent: 路由=%s" % decision.mode.value]

        if decision.mode == AnalysisMode.smalltalk:
            trace.append("主Agent: 委派闲聊回复")
            text = smalltalk_reply(user_query or "你好")
            sid = uuid.uuid4().hex[:12]
            d = OUTPUT_SESSIONS / sid
            d.mkdir(parents=True, exist_ok=True)
            (d / "report.md").write_text("# 会话记录\n\n" + text, encoding="utf-8")
            self._write_session_meta(
                sid,
                {
                    "mode": "smalltalk",
                    "trace": trace,
                    "user_query": user_query,
                },
            )
            base = public_base_url()
            return AnalystResult(
                session_id=sid,
                mode="smalltalk",
                reply_markdown=text,
                dashboard_url=None,
                report_url="%s/sessions/%s/report.md" % (base, sid),
                trace=trace,
            )

        if decision.mode == AnalysisMode.text_only:
            trace.append("主Agent: 无文件 → 文本分析链")
            body = text_analysis_reply(user_query or "")
            sid = uuid.uuid4().hex[:12]
            report = "# 文本分析\n\n" + body
            d = OUTPUT_SESSIONS / sid
            d.mkdir(parents=True, exist_ok=True)
            (d / "report.md").write_text(report, encoding="utf-8")
            self._write_session_meta(
                sid,
                {"mode": "text_only", "trace": trace + ["主Agent: 文本分析完成"], "user_query": user_query},
            )
            base = public_base_url()
            return AnalystResult(
                session_id=sid,
                mode="text_only",
                reply_markdown=body,
                dashboard_url=None,
                report_url="%s/sessions/%s/report.md" % (base, sid),
                trace=trace,
            )

        # data_pipeline
        assert file_bytes is not None and filename
        sid = uuid.uuid4().hex[:12]
        session_dir = OUTPUT_SESSIONS / sid
        session_dir.mkdir(parents=True, exist_ok=True)

        state: Dict[str, Any] = {
            "user_query": user_query,
            "file_bytes": file_bytes,
            "filename": filename,
            "session_id": sid,
            "session_dir": session_dir,
        }
        trace.append("主Agent: 子Agent A 数据准备")
        state = self._prep.invoke(state)
        trace.append("主Agent: 子Agent B 分析解读")
        state = self._analytics.invoke(state)
        trace.append("主Agent: 子Agent C 可视化看板")
        state = self._viz.invoke(state)

        report_md = self._build_report_md(state, trace)
        (session_dir / "report.md").write_text(report_md, encoding="utf-8")

        prof_path = session_dir / "profile.json"
        prof_path.write_text(
            json.dumps(_json_safe(state.get("profile", {})), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self._write_session_meta(
            sid,
            {
                "mode": "data_pipeline",
                "trace": trace + ["子AgentA: 解析完成", "子AgentB: 解读完成", "子AgentC: 看板已生成"],
                "user_query": user_query,
                "filename": filename,
                "file_format": state.get("file_format"),
            },
        )

        base = public_base_url()
        dash_url = "%s/sessions/%s/dashboard.html" % (base, sid)
        rep_url = "%s/sessions/%s/report.md" % (base, sid)
        summary = (
            "## 分析完成\n\n"
            "- **交互看板**：%s\n"
            "- **全文报告**：%s\n\n"
            "### 主 Agent 摘要\n数据已走「准备 → 解读 → 看板」三子 Agent；详情见报告与看板。\n"
        ) % (dash_url, rep_url)

        return AnalystResult(
            session_id=sid,
            mode="data_pipeline",
            reply_markdown=summary,
            dashboard_url=dash_url,
            report_url=rep_url,
            trace=trace
            + [
                "子AgentA: 数据准备",
                "子AgentB: 分析解读",
                "子AgentC: 可视化",
            ],
        )

    def _write_session_meta(self, sid: str, meta: Dict[str, Any]) -> None:
        d = OUTPUT_SESSIONS / sid
        d.mkdir(parents=True, exist_ok=True)
        (d / "session.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _build_report_md(self, state: Dict[str, Any], trace: List[str]) -> str:
        parts = [
            "# 多 Agent 数据分析报告",
            "",
            "## 编排轨迹",
            "\n".join("- %s" % t for t in trace),
            "",
            "## 数据准备（子 Agent A）",
            str(state.get("prep_narrative", "")),
            "",
            "## 分析解读（子 Agent B）",
            str(state.get("analytics_markdown", "")),
            "",
            "## 可视化说明（子 Agent C）",
            str(state.get("viz_narrative", "")),
            "",
            "## 作品链接",
            "- 看板：`dashboard.html`（与本报告同目录，或由 Web 服务同前缀访问）",
        ]
        return "\n".join(parts)
