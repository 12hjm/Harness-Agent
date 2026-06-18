from __future__ import annotations

from typing import TypedDict

from app.domain.models import Citation, InboundMessage, OutboundMessage, RetrievedChunk


class AgentState(TypedDict, total=False):
    inbound: InboundMessage
    history: list[dict]
    rewritten_query: str
    retrieved_chunks: list[RetrievedChunk]
    has_evidence: bool
    answer: str
    citations: list[Citation]
    outbound: OutboundMessage

