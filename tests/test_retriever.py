import pytest

from app.domain.models import DocumentChunk
from app.rag.embeddings import HashEmbeddingProvider
from app.rag.retriever import KnowledgeRetriever
from app.rag.vector_store import InMemoryVectorStore


@pytest.mark.asyncio
async def test_retriever_detects_sufficient_evidence():
    embeddings = HashEmbeddingProvider(dimensions=64)
    store = InMemoryVectorStore()
    chunk = DocumentChunk(
        id="chunk-1",
        document_id="doc-1",
        source="sample.md",
        chunk_index=0,
        text="退款通常会在 3-7 个工作日内原路返回",
    )
    await store.upsert_chunks([chunk], await embeddings.embed_texts([chunk.text]))
    retriever = KnowledgeRetriever(embeddings, store, top_k=3, min_score=0.1)

    results = await retriever.retrieve("退款 3-7 个工作日")

    assert results
    assert retriever.has_sufficient_evidence(results)
    assert retriever.to_citations(results)[0].source == "sample.md"

