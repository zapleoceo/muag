import logging
from contextlib import asynccontextmanager
from pathlib import Path

from aiogram import Bot, Dispatcher
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db.database import engine
from app.db.models import Base
from app.triggers.manager import start_trigger_manager, stop_trigger_manager

log = logging.getLogger(__name__)

_bot: Bot | None = None
_dp: Dispatcher | None = None
_polling_task = None

_STATIC = Path(__file__).parent.parent / "static"


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
        from aiogram import BaseMiddleware
        from aiogram.types import TelegramObject

        class LogAllMiddleware(BaseMiddleware):
            async def __call__(self, handler, event: TelegramObject, data: dict):
                import sys
                print(f"[VERA-MW] type={type(event).__name__} data={str(event)[:400]}", flush=True, file=sys.stderr)
                return await handler(event, data)

        from app.bot.router import router as bot_router
        _bot = Bot(token=settings.main_bot_token)
        _dp = Dispatcher()
        _dp.update.outer_middleware(LogAllMiddleware())
        _dp.include_router(bot_router)
        import asyncio
        _polling_task = asyncio.create_task(_start_polling(_bot, _dp))
        log.info("Telegram bot started (polling)")
    else:
        log.warning("MAIN_BOT_TOKEN not set — bot disabled")

    # Agent bots (one polling task per agent with bot_token)
    from app.agents.runner import start_agent_runners
    await start_agent_runners()

    # Triggers
    start_trigger_manager()

    # Error alerting — sends CRITICAL/ERROR logs to owner via Telegram
    import asyncio as _asyncio
    from app.services.alerting import AlertingHandler
    alerting_handler = AlertingHandler(loop=_asyncio.get_event_loop())
    logging.getLogger().addHandler(alerting_handler)

    log.info("VERA started")
    yield

    # Shutdown
    from app.agents.runner import stop_agent_runners
    await stop_agent_runners()
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

# Static UI
if _STATIC.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")

from app.api.agents_api import router as agents_router
from app.api.credentials import router as creds_router
from app.api.tasks_api import router as tasks_router
from app.api.triggers_api import router as triggers_router
from app.api.webhook import router as webhook_router

app.include_router(agents_router)
app.include_router(creds_router)
app.include_router(tasks_router)
app.include_router(triggers_router)
app.include_router(webhook_router)


@app.get("/")
async def index():
    index_file = _STATIC / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"status": "ok", "ui": "not found"}


@app.get("/health")
async def health():
    return {"status": "ok", "bot": _bot is not None}
