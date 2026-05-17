"""Polling loop — loads triggers from DB and fires tasks."""
import asyncio
import logging

from app.db.database import AsyncSessionLocal
from app.db.models import AgentTask
from app.db.repository import get_active_triggers, save_task
from app.triggers.base import BaseTrigger

log = logging.getLogger(__name__)

_POLL_INTERVAL = 60  # seconds
_task_ref: asyncio.Task | None = None
# Persistent trigger instances so they keep state (e.g. last_update_id for Telegram)
_instances: dict[int, BaseTrigger] = {}


def start_trigger_manager() -> None:
    global _task_ref
    if _task_ref and not _task_ref.done():
        return
    _task_ref = asyncio.create_task(_loop())
    log.info("TriggerManager started")


def stop_trigger_manager() -> None:
    global _task_ref
    if _task_ref:
        _task_ref.cancel()
        _task_ref = None


async def _loop() -> None:
    while True:
        try:
            async with AsyncSessionLocal() as session:
                trigger_rows = await get_active_triggers(session)
                for row in trigger_rows:
                    trigger = _get_or_build(row)
                    if not trigger:
                        continue
                    events = await trigger.poll()
                    for event in events:
                        task = AgentTask(
                            trigger_type=event.trigger_type,
                            trigger_data=event.raw_data,
                            task_text=event.task_text,
                            topic_thread_id=event.topic_thread_id,
                            status="queued",
                        )
                        await save_task(session, task)
                        log.info(
                            "Queued task from trigger '%s': %s",
                            row.name,
                            event.task_text[:80],
                        )
        except asyncio.CancelledError:
            return
        except Exception:
            log.exception("TriggerManager loop error")

        await asyncio.sleep(_POLL_INTERVAL)


def _get_or_build(row) -> BaseTrigger | None:
    if row.id in _instances:
        return _instances[row.id]

    trigger = _build_trigger(row)
    if trigger:
        _instances[row.id] = trigger
    return trigger


def _build_trigger(row) -> BaseTrigger | None:
    try:
        if row.type == "cron":
            from app.triggers.cron import CronTrigger
            return CronTrigger(
                name=row.name,
                config=row.config or {},
                agent_names=row.agent_names or [],
            )

        if row.type == "telegram":
            from app.triggers.telegram_trigger import TelegramTrigger
            return TelegramTrigger(
                config=row.config or {},
                agent_names=row.agent_names or [],
            )

        if row.type == "gmail":
            from app.triggers.gmail_trigger import GmailTrigger
            return GmailTrigger(name=row.name, config=row.config or {}, agent_names=row.agent_names or [])

        if row.type == "instagram":
            from app.triggers.instagram_trigger import InstagramTrigger
            return InstagramTrigger(name=row.name, config=row.config or {}, agent_names=row.agent_names or [])

        log.debug("No trigger handler for type: %s", row.type)
        return None
    except Exception:
        log.exception("Failed to build trigger '%s'", row.name)
        return None
