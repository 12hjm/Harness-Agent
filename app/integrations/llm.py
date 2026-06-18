from __future__ import annotations

from abc import ABC, abstractmethod

from openai import AsyncOpenAI

from app.domain.models import RetrievedChunk


class LLMProvider(ABC):
    @abstractmethod
    async def rewrite_query(self, question: str, history: list[dict]) -> str:
        raise NotImplementedError

    @abstractmethod
    async def answer(self, question: str, chunks: list[RetrievedChunk]) -> str:
        raise NotImplementedError


class MockLLMProvider(LLMProvider):
    async def rewrite_query(self, question: str, history: list[dict]) -> str:
        return question.strip()

    async def answer(self, question: str, chunks: list[RetrievedChunk]) -> str:
        context = "\n".join(f"- {item.chunk.text}" for item in chunks[:2])
        return f"根据知识库内容，{question}\n\n参考信息：\n{context}"


class OpenAICompatibleLLMProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str, model: str, timeout_seconds: float = 30.0):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout_seconds)
        self.model = model

    async def rewrite_query(self, question: str, history: list[dict]) -> str:
        history_text = "\n".join(f"{row.get('role')}: {row.get('content')}" for row in history[-6:])
        response = await self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": "你是客服问答检索助手。请结合对话历史，把用户最新问题改写成独立、清晰的中文检索查询。只输出改写后的查询。",
                },
                {"role": "user", "content": f"对话历史：\n{history_text}\n\n最新问题：{question}"},
            ],
        )
        return response.choices[0].message.content.strip() or question

    async def answer(self, question: str, chunks: list[RetrievedChunk]) -> str:
        context = "\n\n".join(
            f"[{index}] 来源：{item.chunk.source}\n{item.chunk.text}"
            for index, item in enumerate(chunks, start=1)
        )
        response = await self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是中文客服助手。必须只基于给定知识库片段回答。"
                        "如果片段不足以回答，说明暂未找到可靠答案。"
                        "答案要简洁、可执行，并在末尾列出引用来源编号。"
                    ),
                },
                {"role": "user", "content": f"用户问题：{question}\n\n知识库片段：\n{context}"},
            ],
        )
        return response.choices[0].message.content.strip()

