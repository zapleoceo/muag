import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from fastapi import FastAPI

from app.config import get_settings
from app.db.database import engine
from app.db.models import Base
from app.triggers.manager import start_trigger_manager, stop_trigger_manager

log = logging.getLogger(__name__)

_bot: Bot | None = None
_dp: Dispatcher | None = None
_polling_task = None


def get_bot() -> Bot | None:
    return _bot


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bot, _dp, _polling_task

    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    # DB
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("DB tables ready")

    # Telegram bot
    if settings.main_bot_token:
        from app.bot.router import router as bot_router
        _bot = Bot(token=settings.main_bot_token)
        _dp = Dispatcher()
        _dp.include_router(bot_router)
        import asyncio
        _polling_task = asyncio.create_task(_start_polling(_bot, _dp))
        log.info("Telegram bot started (polling)")
    else:
        log.warning("MAIN_BOT_TOKEN not set — bot disabled")

    # Triggers
    start_trigger_manager()

    log.info("VERA started")
    yield

    # Shutdown
    stop_trigger_manager()
    if _polling_task:
        _polling_task.cancel()
    if _bot:
        await _bot.session.close()
    await engine.dispose()
    log.info("VERA shutdown")


async def _start_polling(bot: Bot, dp: Dispatcher) -> None:
    import asyncio
    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    except asyncio.CancelledError:
        pass


app = FastAPI(title="VERA — Virtual Executive Response Architecture", lifespan=lifespan)

from app.api.agents_api import router as agents_router
from app.api.credentials import router as creds_router
from app.api.tasks_api import router as tasks_router

app.include_router(agents_router)
app.include_router(creds_router)
app.include_router(tasks_router)


@app.get("/health")
async def health():
    return {"status": "ok", "bot": _bot is not None}
