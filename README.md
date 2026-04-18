# 多 Agent 数据分析师

作品说明：基于 **LangChain**（`langchain-core` + `langchain-openai`）与 **FastAPI** 的多智能体数据分析应用。

## 功能概述

- **主 Agent**：用户意图路由（闲聊 / 纯文本分析 / 数据文件全链路）与任务编排。
- **子 Agent A**：表格文件解析与数据画像（CSV / XLSX / TSV / JSONL 等）。
- **子 Agent B**：统计摘要与大模型业务解读（Markdown）。
- **子 Agent C**：Plotly 交互看板（离线 `dashboard.html`）与看板导读。

无上传文件时可进行寒暄或开放文本分析；上传文件后生成报告与看板访问路径。

## 环境与运行

1. Python **3.9+**（推荐 3.10～3.12）。
2. 创建虚拟环境并安装依赖：

```bash
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -U pip
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

3. 配置环境变量：复制 `.env.example` 为 `.env`，填写 `OPENAI_API_KEY` 等

4. 启动：

```bash
python -m multi_agent_analyst
```

5. 浏览器访问（端口与 `PORT`、`ANALYST_PUBLIC_BASE_URL` 保持一致，默认 **http://127.0.0.1:8765/** ）。

6. 健康检查：`GET /health`，响应 JSON 中含 `web_app_url`。

示例数据：`sample_data/demo_sales.csv`。

## 仓库目录

详见 **`仓库结构说明.txt`**。设计说明文档：**`作品介绍.docx`**。可选从源码重建 Word：`pip install python-docx` 后执行 `python scripts/build_intro_docx.py`。

## 技术栈

FastAPI、Uvicorn、Pandas、OpenPyXL、Plotly、LangChain Core、OpenAI 兼容接口。

## 安全说明

不执行用户提交的任意 Python/SQL；表格分析为白盒统计与受控可视化。

