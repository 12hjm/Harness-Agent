from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict
from datetime import datetime, timezone

import asyncpg

from app.domain.models import IndexJob, JobStatus


class IndexJobRepository(ABC):
    @abstractmethod
    async def init(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, job: IndexJob) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get(self, job_id: str) -> IndexJob | None:
        raise NotImplementedError


class InMemoryIndexJobRepository(IndexJobRepository):
    def __init__(self):
        self._jobs: dict[str, IndexJob] = {}

    async def init(self) -> None:
        return None

    async def save(self, job: IndexJob) -> None:
        job.updated_at = datetime.now(timezone.utc)
        self._jobs[job.id] = job

    async def get(self, job_id: str) -> IndexJob | None:
        return self._jobs.get(job_id)


class PostgresIndexJobRepository(IndexJobRepository):
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: asyncpg.Pool | None = None

    async def init(self) -> None:
        if self.pool is None:
            self.pool = await asyncpg.create_pool(self.database_url)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS index_jobs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    total_documents INTEGER NOT NULL DEFAULT 0,
                    total_chunks INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                )
                """
            )

    async def save(self, job: IndexJob) -> None:
        await self.init()
        assert self.pool is not None
        job.updated_at = datetime.now(timezone.utc)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO index_jobs
                    (id, status, total_documents, total_chunks, error, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status,
                    total_documents = EXCLUDED.total_documents,
                    total_chunks = EXCLUDED.total_chunks,
                    error = EXCLUDED.error,
                    updated_at = EXCLUDED.updated_at
                """,
                job.id,
                job.status.value,
                job.total_documents,
                job.total_chunks,
                job.error,
                job.created_at,
                job.updated_at,
            )

    async def get(self, job_id: str) -> IndexJob | None:
        await self.init()
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM index_jobs WHERE id = $1", job_id)
        if row is None:
            return None
        return IndexJob(
            id=row["id"],
            status=JobStatus(row["status"]),
            total_documents=row["total_documents"],
            total_chunks=row["total_chunks"],
            error=row["error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def job_to_jsonable(job: IndexJob) -> dict:
    payload = asdict(job)
    payload["status"] = job.status.value
    payload["created_at"] = job.created_at.isoformat()
    payload["updated_at"] = job.updated_at.isoformat()
    return json.loads(json.dumps(payload, ensure_ascii=False))

