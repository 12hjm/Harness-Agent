from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.container import get_container
from app.core.logging import configure_logging, get_logger


configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    container = get_container()
    await container.init()
    logger.info("app_started", app=container.settings.app_name)
    yield
    logger.info("app_stopped")


app = FastAPI(title="RAG Agent Customer Service", version="0.1.0", lifespan=lifespan)
app.include_router(router)

