from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.domain.models import DocumentChunk, IndexJob, JobStatus
from app.rag.chunker import recursive_character_splitter
from app.rag.document_loader import load_documents_from_dir
from app.rag.embeddings import EmbeddingProvider
from app.rag.vector_store import VectorStore
from app.storage.jobs import IndexJobRepository


class KnowledgeBaseIndexer:
    def __init__(
        self,
        kb_dir: Path,
        chunk_size: int,
        chunk_overlap: int,
        embeddings: EmbeddingProvider,
        vector_store: VectorStore,
        jobs: IndexJobRepository,
    ):
        self.kb_dir = kb_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.jobs = jobs

    async def start_reindex(self, clear_existing: bool = True) -> IndexJob:
        job = IndexJob(id=str(uuid4()), status=JobStatus.RUNNING)
        await self.jobs.save(job)
        await self.reindex(job, clear_existing=clear_existing)
        return job

    async def reindex(self, job: IndexJob, clear_existing: bool = True) -> None:
        try:
            if clear_existing:
                await self.vector_store.clear()
            documents = load_documents_from_dir(self.kb_dir)
            chunks: list[DocumentChunk] = []
            for document in documents:
                texts = recursive_character_splitter(
                    document.content,
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                )
                chunks.extend(
                    DocumentChunk(
                        id=f"{document.id}-{index}",
                        document_id=document.id,
                        source=document.source,
                        chunk_index=index,
                        text=text,
                        metadata=document.metadata,
                    )
                    for index, text in enumerate(texts)
                )

            if chunks:
                embeddings = await self.embeddings.embed_texts([chunk.text for chunk in chunks])
                await self.vector_store.upsert_chunks(chunks, embeddings)

            job.status = JobStatus.SUCCEEDED
            job.total_documents = len(documents)
            job.total_chunks = len(chunks)
            job.error = None
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error = str(exc)
        finally:
            await self.jobs.save(job)

