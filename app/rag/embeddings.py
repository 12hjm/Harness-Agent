from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod

from openai import AsyncOpenAI


class EmbeddingProvider(ABC):
    dimensions: int

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    async def embed_query(self, text: str) -> list[float]:
        return (await self.embed_texts([text]))[0]


class HashEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        values = [0.0] * self.dimensions
        tokens = [token for token in text.lower().split() if token] or [text]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            values[index] += sign
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, base_url: str, model: str, dimensions: int):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.dimensions = dimensions

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        all_embeddings: list[list[float]] = []
        batch_size = 64
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = await self.client.embeddings.create(input=batch, model=self.model)
            all_embeddings.extend(item.embedding for item in response.data)
        return all_embeddings

