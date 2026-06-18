from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_name: str = "RAG Agent Customer Service"
    public_base_url: str = "http://localhost:8000"

    llm_provider: str = "mock"
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_api_key: str = ""
    llm_model: str = "qwen-plus"
    llm_timeout_seconds: float = 30.0

    embedding_provider: str = "hash"
    embedding_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-v3"
    embedding_dimensions: int = 1024

    conversation_store: str = "memory"
    vector_store: str = "memory"
    idempotency_store: str = "memory"
    database_url: str = "postgresql://rag:rag_password@localhost:5432/rag"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "kb_chunks"

    kb_dir: Path = Path("data/kb")
    chunk_size: int = 700
    chunk_overlap: int = 100
    retrieval_top_k: int = 5
    retrieval_min_score: float = 0.62
    fallback_message: str = "抱歉，我暂时没有在知识库中找到可靠答案。请换一种问法，或稍后联系人工客服。"

    admin_token: str = Field(default="dev-admin-token")

    wecom_token: str = ""
    wecom_encoding_aes_key: str = ""
    wecom_corp_id: str = ""

    feishu_verification_token: str = ""
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_encrypt_key: str = ""

    rate_limit_per_minute: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()

