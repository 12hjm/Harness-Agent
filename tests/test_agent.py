import pytest

from app.agent.graph import CustomerServiceAgent
from app.domain.models import DocumentChunk, InboundMessage, Platform
from app.integrations.llm import MockLLMProvider
from app.rag.embeddings import HashEmbeddingProvider
from app.rag.retriever import KnowledgeRetriever
from app.rag.vector_store import InMemoryVectorStore
from app.storage.conversations import InMemoryConversationRepository


@pytest.mark.asyncio
async def test_agent_answers_with_citation_when_knowledge_matches():
    embeddings = HashEmbeddingProvider(dimensions=64)
    store = InMemoryVectorStore()
    chunk = DocumentChunk(
        id="chunk-1",
        document_id="doc-1",
        source="sample.md",
        chunk_index=0,
        text="客服在线时间为周一至周五 09:00-18:00",
    )
    await store.upsert_chunks([chunk], await embeddings.embed_texts([chunk.text]))
    retriever = KnowledgeRetriever(embeddings, store, top_k=3, min_score=0.0)
    conversations = InMemoryConversationRepository()
    agent = CustomerServiceAgent(MockLLMProvider(), retriever, conversations, "兜底")

    outbound = await agent.answer(
        InboundMessage(
            platform=Platform.DEBUG,
            user_id="u1",
            conversation_id="c1",
            content="客服在线时间",
        )
    )

    assert "客服在线时间" in outbound.content
    assert outbound.citations
