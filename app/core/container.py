from __future__ import annotations

from functools import lru_cache

from app.agent.graph import CustomerServiceAgent
from app.core.config import Settings, get_settings
from app.integrations.llm import LLMProvider, MockLLMProvider, OpenAICompatibleLLMProvider
from app.rag.embeddings import EmbeddingProvider, HashEmbeddingProvider, OpenAICompatibleEmbeddingProvider
from app.rag.indexer import KnowledgeBaseIndexer
from app.rag.retriever import KnowledgeRetriever
from app.rag.vector_store import InMemoryVectorStore, QdrantVectorStore, VectorStore
from app.storage.conversations import (
    ConversationRepository,
    InMemoryConversationRepository,
    PostgresConversationRepository,
)
from app.storage.idempotency import IdempotencyStore, InMemoryIdempotencyStore, RedisIdempotencyStore
from app.storage.jobs import IndexJobRepository, InMemoryIndexJobRepository, PostgresIndexJobRepository


class AppContainer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.embeddings = self._build_embeddings()
        self.vector_store = self._build_vector_store()
        self.conversations = self._build_conversations()
        self.idempotency = self._build_idempotency()
        self.jobs = self._build_jobs()
        self.llm = self._build_llm()
        self.retriever = KnowledgeRetriever(
            embeddings=self.embeddings,
            vector_store=self.vector_store,
            top_k=settings.retrieval_top_k,
            min_score=settings.retrieval_min_score,
        )
        self.agent = CustomerServiceAgent(
            llm=self.llm,
            retriever=self.retriever,
            conversations=self.conversations,
            fallback_message=settings.fallback_message,
        )
        self.indexer = KnowledgeBaseIndexer(
            kb_dir=settings.kb_dir,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            embeddings=self.embeddings,
            vector_store=self.vector_store,
            jobs=self.jobs,
        )

    async def init(self) -> None:
        await self.vector_store.ensure_ready()
        await self.conversations.init()
        await self.jobs.init()

    def _build_embeddings(self) -> EmbeddingProvider:
        if self.settings.embedding_provider == "openai_compatible":
            return OpenAICompatibleEmbeddingProvider(
                api_key=self.settings.embedding_api_key,
                base_url=self.settings.embedding_base_url,
                model=self.settings.embedding_model,
                dimensions=self.settings.embedding_dimensions,
            )
        return HashEmbeddingProvider(dimensions=self.settings.embedding_dimensions)

    def _build_vector_store(self) -> VectorStore:
        if self.settings.vector_store == "qdrant":
            return QdrantVectorStore(
                url=self.settings.qdrant_url,
                collection_name=self.settings.qdrant_collection,
                dimensions=self.settings.embedding_dimensions,
            )
        return InMemoryVectorStore()

    def _build_conversations(self) -> ConversationRepository:
        if self.settings.conversation_store == "postgres":
            return PostgresConversationRepository(self.settings.database_url)
        return InMemoryConversationRepository()

    def _build_idempotency(self) -> IdempotencyStore:
        if self.settings.idempotency_store == "redis":
            return RedisIdempotencyStore(self.settings.redis_url)
        return InMemoryIdempotencyStore()

    def _build_jobs(self) -> IndexJobRepository:
        if self.settings.conversation_store == "postgres":
            return PostgresIndexJobRepository(self.settings.database_url)
        return InMemoryIndexJobRepository()

    def _build_llm(self) -> LLMProvider:
        if self.settings.llm_provider == "openai_compatible":
            return OpenAICompatibleLLMProvider(
                api_key=self.settings.llm_api_key,
                base_url=self.settings.llm_base_url,
                model=self.settings.llm_model,
                timeout_seconds=self.settings.llm_timeout_seconds,
            )
        return MockLLMProvider()


@lru_cache
def get_container() -> AppContainer:
    return AppContainer(get_settings())

