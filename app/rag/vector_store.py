from __future__ import annotations

import math
from uuid import NAMESPACE_URL, uuid5
from abc import ABC, abstractmethod

from app.domain.models import DocumentChunk, RetrievedChunk


class VectorStore(ABC):
    @abstractmethod
    async def ensure_ready(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def upsert_chunks(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> int:
        raise NotImplementedError

    @abstractmethod
    async def search(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        raise NotImplementedError

    @abstractmethod
    async def clear(self) -> None:
        raise NotImplementedError


class InMemoryVectorStore(VectorStore):
    def __init__(self):
        self._rows: list[tuple[DocumentChunk, list[float]]] = []

    async def ensure_ready(self) -> None:
        return None

    async def upsert_chunks(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> int:
        existing_ids = {chunk.id for chunk in chunks}
        self._rows = [(chunk, emb) for chunk, emb in self._rows if chunk.id not in existing_ids]
        self._rows.extend(zip(chunks, embeddings))
        return len(chunks)

    async def search(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        scored = [
            RetrievedChunk(chunk=chunk, score=_cosine_similarity(embedding, row_embedding))
            for chunk, row_embedding in self._rows
        ]
        return sorted(scored, key=lambda item: item.score, reverse=True)[:top_k]

    async def clear(self) -> None:
        self._rows.clear()


class QdrantVectorStore(VectorStore):
    def __init__(self, url: str, collection_name: str, dimensions: int):
        from qdrant_client import AsyncQdrantClient

        self.client = AsyncQdrantClient(url=url)
        self.collection_name = collection_name
        self.dimensions = dimensions

    async def ensure_ready(self) -> None:
        from qdrant_client.http import models

        collections = await self.client.get_collections()
        names = {collection.name for collection in collections.collections}
        if self.collection_name not in names:
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(size=self.dimensions, distance=models.Distance.COSINE),
            )

    async def upsert_chunks(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> int:
        from qdrant_client.http import models

        await self.ensure_ready()
        points = [
            models.PointStruct(
                id=_qdrant_point_id(chunk.id),
                vector=embedding,
                payload={
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "source": chunk.source,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    **chunk.metadata,
                },
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]
        await self.client.upsert(collection_name=self.collection_name, points=points)
        return len(points)

    async def search(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        await self.ensure_ready()
        results = await self.client.search(
            collection_name=self.collection_name,
            query_vector=embedding,
            limit=top_k,
            with_payload=True,
        )
        chunks: list[RetrievedChunk] = []
        for result in results:
            payload = result.payload or {}
            chunk = DocumentChunk(
                id=str(payload.get("chunk_id", result.id)),
                document_id=str(payload.get("document_id", "")),
                source=str(payload.get("source", "")),
                chunk_index=int(payload.get("chunk_index", 0)),
                text=str(payload.get("text", "")),
                metadata={
                    k: v
                    for k, v in payload.items()
                    if k not in {"chunk_id", "document_id", "source", "chunk_index", "text"}
                },
            )
            chunks.append(RetrievedChunk(chunk=chunk, score=float(result.score)))
        return chunks

    async def clear(self) -> None:
        from qdrant_client.http import exceptions

        try:
            await self.client.delete_collection(collection_name=self.collection_name)
        except (exceptions.UnexpectedResponse, ValueError):
            pass
        await self.ensure_ready()


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    numerator = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if not norm_a or not norm_b:
        return 0.0
    return numerator / (norm_a * norm_b)


def _qdrant_point_id(chunk_id: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"rag-agent:{chunk_id}"))
