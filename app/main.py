import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.db.database import engine
from app.db.models import Base
from app.triggers.manager import start_trigger_manager, stop_trigger_manager

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("DB tables ready")

    start_trigger_manager()
    log.info("VERA started")

    yield

    stop_trigger_manager()
    await engine.dispose()
    log.info("VERA shutdown")


app = FastAPI(title="VERA — Virtual Executive Response Architecture", lifespan=lifespan)

from app.api.agents_api import router as agents_router
from app.api.credentials import router as creds_router
from app.api.tasks_api import router as tasks_router

app.include_router(agents_router)
app.include_router(creds_router)
app.include_router(tasks_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
