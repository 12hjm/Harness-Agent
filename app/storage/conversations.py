from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import asyncpg

from app.domain.models import InboundMessage, OutboundMessage


class ConversationRepository(ABC):
    @abstractmethod
    async def init(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def append_turn(self, inbound: InboundMessage, outbound: OutboundMessage) -> None:
        raise NotImplementedError

    @abstractmethod
    async def recent_messages(self, conversation_id: str, limit: int = 6) -> list[dict[str, Any]]:
        raise NotImplementedError


class InMemoryConversationRepository(ConversationRepository):
    def __init__(self):
        self._messages: dict[str, list[dict[str, Any]]] = {}

    async def init(self) -> None:
        return None

    async def append_turn(self, inbound: InboundMessage, outbound: OutboundMessage) -> None:
        rows = self._messages.setdefault(inbound.conversation_id, [])
        rows.append(
            {
                "role": "user",
                "content": inbound.content,
                "platform": inbound.platform.value,
                "message_id": inbound.message_id,
                "created_at": inbound.created_at.isoformat(),
            }
        )
        rows.append(
            {
                "role": "assistant",
                "content": outbound.content,
                "platform": outbound.platform.value,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    async def recent_messages(self, conversation_id: str, limit: int = 6) -> list[dict[str, Any]]:
        return self._messages.get(conversation_id, [])[-limit:]


class PostgresConversationRepository(ConversationRepository):
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: asyncpg.Pool | None = None

    async def init(self) -> None:
        if self.pool is None:
            self.pool = await asyncpg.create_pool(self.database_url)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id BIGSERIAL PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    message_id TEXT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            await conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS messages_message_id_idx
                ON messages(message_id)
                WHERE message_id IS NOT NULL
                """
            )

    async def append_turn(self, inbound: InboundMessage, outbound: OutboundMessage) -> None:
        await self.init()
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO conversations (id, platform, updated_at)
                    VALUES ($1, $2, now())
                    ON CONFLICT (id) DO UPDATE SET updated_at = now()
                    """,
                    inbound.conversation_id,
                    inbound.platform.value,
                )
                await conn.execute(
                    """
                    INSERT INTO messages (conversation_id, message_id, role, content, metadata, created_at)
                    VALUES ($1, $2, 'user', $3, $4::jsonb, $5)
                    ON CONFLICT (message_id) DO NOTHING
                    """,
                    inbound.conversation_id,
                    inbound.message_id,
                    inbound.content,
                    json.dumps(inbound.metadata, ensure_ascii=False),
                    inbound.created_at,
                )
                await conn.execute(
                    """
                    INSERT INTO messages (conversation_id, role, content, metadata)
                    VALUES ($1, 'assistant', $2, $3::jsonb)
                    """,
                    outbound.conversation_id,
                    outbound.content,
                    json.dumps(outbound.metadata, ensure_ascii=False),
                )

    async def recent_messages(self, conversation_id: str, limit: int = 6) -> list[dict[str, Any]]:
        await self.init()
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT role, content, metadata, created_at
                FROM messages
                WHERE conversation_id = $1
                ORDER BY id DESC
                LIMIT $2
                """,
                conversation_id,
                limit,
            )
        return [dict(row) for row in reversed(rows)]

