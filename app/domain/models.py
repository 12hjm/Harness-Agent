from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


class Platform(StrEnum):
    DEBUG = "debug"
    WECOM = "wecom"
    FEISHU = "feishu"


@dataclass(frozen=True)
class InboundMessage:
    platform: Platform
    user_id: str
    conversation_id: str
    content: str
    message_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class Citation:
    source: str
    chunk_id: str
    score: float
    text: str


@dataclass(frozen=True)
class OutboundMessage:
    platform: Platform
    conversation_id: str
    content: str
    citations: list[Citation] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Document:
    id: str
    source: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentChunk:
    id: str
    document_id: str
    source: str
    chunk_index: int
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: DocumentChunk
    score: float


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class IndexJob:
    id: str
    status: JobStatus = JobStatus.PENDING
    total_documents: int = 0
    total_chunks: int = 0
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

