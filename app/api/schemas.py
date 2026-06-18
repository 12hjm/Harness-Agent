from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str = Field(default="debug-user")
    conversation_id: str = Field(default="debug-conversation")
    message: str


class CitationResponse(BaseModel):
    source: str
    chunk_id: str
    score: float
    text: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]
    conversation_id: str


class ReindexRequest(BaseModel):
    clear_existing: bool = True

