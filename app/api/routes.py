from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.api.schemas import ChatRequest, ChatResponse, ReindexRequest
from app.core.container import AppContainer, get_container
from app.core.security import require_admin_token
from app.domain.models import InboundMessage, JobStatus, Platform
from app.storage.jobs import job_to_jsonable

router = APIRouter()


@router.get("/healthz")
async def healthz(container: AppContainer = Depends(get_container)) -> dict:
    return {"status": "ok", "app": container.settings.app_name}


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, container: AppContainer = Depends(get_container)) -> ChatResponse:
    inbound = InboundMessage(
        platform=Platform.DEBUG,
        user_id=payload.user_id,
        conversation_id=payload.conversation_id,
        content=payload.message,
    )
    outbound = await container.agent.answer(inbound)
    return ChatResponse(
        answer=outbound.content,
        citations=[citation.__dict__ for citation in outbound.citations],
        conversation_id=outbound.conversation_id,
    )


@router.post("/admin/kb/reindex", dependencies=[Depends(require_admin_token)])
async def reindex(
    payload: ReindexRequest,
    background_tasks: BackgroundTasks,
    container: AppContainer = Depends(get_container),
) -> dict:
    from app.domain.models import IndexJob
    from uuid import uuid4

    job = IndexJob(id=str(uuid4()), status=JobStatus.RUNNING)
    await container.jobs.save(job)
    background_tasks.add_task(container.indexer.reindex, job, payload.clear_existing)
    return job_to_jsonable(job)


@router.get("/admin/kb/jobs/{job_id}", dependencies=[Depends(require_admin_token)])
async def get_job(job_id: str, container: AppContainer = Depends(get_container)) -> dict:
    job = await container.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job_to_jsonable(job)
