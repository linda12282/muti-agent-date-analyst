"""
FastAPI：上传数据 + 自然语言 → 主 Agent 编排 → 返回「作品链接」（看板 / 报告）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import OUTPUT_SESSIONS, public_base_url
from .orchestrator import MainAnalystOrchestrator

app = FastAPI(title="Multi-Agent Data Analyst", version="0.1.0")
_orch = MainAnalystOrchestrator()


@app.on_event("startup")
def _ensure_output_dir() -> None:
    OUTPUT_SESSIONS.mkdir(parents=True, exist_ok=True)
    root = public_base_url().rstrip("/") + "/"
    print("\n======== 多 Agent 数据分析师 · 网页版验收入口 ========")
    print("请在浏览器打开（整体产品，非单次会话）：")
    print("  %s" % root)
    print("（若经反向代理访问，请把 .env 中 ANALYST_PUBLIC_BASE_URL 设为对外一致地址）")
    print("====================================================\n")

_TEMPLATES = Path(__file__).resolve().parent / "templates"


@app.get("/health")
def health() -> Dict[str, str]:
    base = public_base_url().rstrip("/") + "/"
    return {
        "status": "ok",
        "web_app_url": base,
        "message": "整体网页版入口：用浏览器打开 web_app_url 即可检验上传/分析/看板全链路",
    }


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    p = _TEMPLATES / "index.html"
    if not p.exists():
        return "<h1>missing templates/index.html</h1>"
    return p.read_text(encoding="utf-8")


@app.post("/api/analyze")
async def api_analyze(
    query: str = Form(""),
    file: Optional[UploadFile] = File(None),
):
    raw = await file.read() if file and file.filename else None
    fn = file.filename if file else None
    if raw is not None and len(raw) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件过大（>25MB）")
    try:
        out = _orch.run(user_query=query or "", file_bytes=raw, filename=fn)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="分析失败：%s" % exc) from exc

    base = public_base_url().rstrip("/")
    web_root = base + "/"
    return {
        "web_app_url": web_root,
        "web_app_note": "这是「整体网页版」链接：复制到浏览器即可打开本数据分析师工作台（上传数据、文本分析、查看说明）。用于落地验收请以该链接为准。",
        "session_id": out.session_id,
        "mode": out.mode,
        "reply_markdown": out.reply_markdown,
        "dashboard_url": out.dashboard_url,
        "report_url": out.report_url,
        "result_note": "dashboard_url / report_url 为本次运行生成的子页面，便于深入查看；对外演示「一个产品」请用 web_app_url。",
        "trace": out.trace,
        "public_base_url": base,
        "hint": "若返回的链接打不开，请把 ANALYST_PUBLIC_BASE_URL 改成你实际访问服务时的协议+主机+端口（与浏览器地址栏一致）。",
    }


@app.get("/sessions/{session_id}/dashboard.html")
def get_dashboard(session_id: str) -> FileResponse:
    path = OUTPUT_SESSIONS / session_id / "dashboard.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="看板不存在或未生成")
    return FileResponse(path, media_type="text/html; charset=utf-8")


@app.get("/sessions/{session_id}/report.md")
def get_report(session_id: str) -> FileResponse:
    path = OUTPUT_SESSIONS / session_id / "report.md"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="报告不存在")
    return FileResponse(path, media_type="text/plain; charset=utf-8")


@app.get("/sessions/{session_id}/profile.json")
def get_profile(session_id: str) -> FileResponse:
    path = OUTPUT_SESSIONS / session_id / "profile.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="profile 不存在")
    return FileResponse(path, media_type="application/json; charset=utf-8")


# 静态挂载 output，便于直接访问 /output/sessions/... （可选）
if OUTPUT_SESSIONS.exists():
    app.mount("/output", StaticFiles(directory=str(OUTPUT_SESSIONS.parent)), name="output")
