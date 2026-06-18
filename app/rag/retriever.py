from __future__ import annotations

from app.domain.models import Citation, RetrievedChunk
from app.rag.embeddings import EmbeddingProvider
from app.rag.vector_store import VectorStore


class KnowledgeRetriever:
    def __init__(
        self,
        embeddings: EmbeddingProvider,
        vector_store: VectorStore,
        top_k: int,
        min_score: float,
    ):
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.top_k = top_k
        self.min_score = min_score

    async def retrieve(self, query: str) -> list[RetrievedChunk]:
        embedding = await self.embeddings.embed_query(query)
        return await self.vector_store.search(embedding, top_k=self.top_k)

    def has_sufficient_evidence(self, chunks: list[RetrievedChunk]) -> bool:
        return bool(chunks) and max(item.score for item in chunks) >= self.min_score

    def to_citations(self, chunks: list[RetrievedChunk]) -> list[Citation]:
        return [
            Citation(
                source=item.chunk.source,
                chunk_id=item.chunk.id,
                score=item.score,
                text=item.chunk.text[:280],
            )
            for item in chunks
            if item.score >= self.min_score
        ]

