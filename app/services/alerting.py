"""Error alerting — sends critical errors to owner via Telegram."""
import logging

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)

_TG_API = "https://api.telegram.org/bot{token}/sendMessage"


async def alert_owner(message: str) -> None:
    """Send an alert message to the owner's Telegram."""
    settings = get_settings()
    if not settings.main_bot_token or not settings.owner_telegram_id:
        return

    text = f"🚨 *VERA Alert*\n\n{message}"
    url = _TG_API.format(token=settings.main_bot_token)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json={
                "chat_id": settings.owner_telegram_id,
                "text": text,
                "parse_mode": "Markdown",
            })
    except Exception:
        log.exception("Failed to send alert to owner")


class AlertingHandler(logging.Handler):
    """Logging handler that sends CRITICAL/ERROR logs to Telegram owner."""

    def __init__(self, loop=None) -> None:
        super().__init__(level=logging.ERROR)
        self._loop = loop
        self._last_alerts: dict[str, float] = {}
        self._cooldown = 300  # 5 min cooldown per message signature

    def emit(self, record: logging.LogRecord) -> None:
        import asyncio
        import time

        sig = f"{record.name}:{record.levelno}"
        now = time.monotonic()
        if now - self._last_alerts.get(sig, 0) < self._cooldown:
            return
        self._last_alerts[sig] = now

        msg = f"[{record.levelname}] {record.name}\n{record.getMessage()}"
        if record.exc_info:
            import traceback
            tb = "".join(traceback.format_exception(*record.exc_info))
            msg += f"\n\n```\n{tb[-800:]}\n```"

        try:
            loop = self._loop or asyncio.get_event_loop()
            loop.create_task(alert_owner(msg))
        except RuntimeError:
            pass  # no event loop available (shutdown)
