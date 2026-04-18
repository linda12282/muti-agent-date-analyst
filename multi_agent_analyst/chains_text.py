"""无文件路径：闲聊与纯文本分析（LangChain LCEL）。"""

from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from .llm_factory import chat_model, llm_enabled


def smalltalk_reply(user_text: str) -> str:
    if not llm_enabled():
        return (
            "你好，我是多 Agent 数据分析师的主 Agent。\n"
            "你可以上传 **Excel / CSV** 做统计与交互看板；也可以直接发一段文字让我做观点提炼。\n"
            "（当前未配置 OPENAI_API_KEY，以上为固定欢迎语。）"
        )
    llm = chat_model(temperature=0.4)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "你是专业但友好的数据分析师助手，简短中文回复用户寒暄或闲聊。"),
            ("human", "{text}"),
        ]
    )
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"text": user_text[:2000]}).strip()


def text_analysis_reply(user_text: str) -> str:
    if not llm_enabled():
        return (
            "（未配置 OPENAI_API_KEY）无法进行大模型文本分析。\n"
            "请配置密钥后重试；或上传数据文件走「数据准备→分析→可视化」全链路。"
        )
    llm = chat_model(temperature=0.25)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是主 Agent 委派的「文本分析」子能力。对用户输入做结构化中文输出："
                "## 理解 ## 要点 ## 风险或歧义 ## 建议下一步。保持简洁。",
            ),
            ("human", "{text}"),
        ]
    )
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"text": user_text[:12000]}).strip()
