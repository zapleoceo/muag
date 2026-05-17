"""Command handlers: /task, /status, /agents."""
import asyncio
import logging

from aiogram.types import Message
from sqlalchemy import select

from app.agents.orchestrator import Orchestrator
from app.config import get_settings
from app.db.database import AsyncSessionLocal
from app.db.models import Agent, AgentTask
from app.db.repository import save_task

log = logging.getLogger(__name__)


def _is_owner(message: Message) -> bool:
    return message.from_user and message.from_user.id == get_settings().owner_telegram_id


async def handle_task(message: Message) -> None:
    if not _is_owner(message):
        return

    text = (message.text or "").removeprefix("/task").strip()
    if not text:
        await message.answer("❌ Укажи задачу: /task <текст>")
        return

    status_msg = await message.answer("⏳ Принял задачу, запускаю агентов...")

    async with AsyncSessionLocal() as session:
        task = AgentTask(
            trigger_type="command",
            task_text=text,
            status="queued",
        )
        task = await save_task(session, task)
        task_id = task.id

    asyncio.create_task(_run_and_reply(task_id, message, status_msg.message_id))


async def handle_status(message: Message) -> None:
    if not _is_owner(message):
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AgentTask).order_by(AgentTask.id.desc()).limit(5)
        )
        tasks = result.scalars().all()

    if not tasks:
        await message.answer("Задач пока нет.")
        return

    lines = []
    for t in tasks:
        icon = {"queued": "⏳", "planning": "🗺", "running": "⚙️",
                "reflecting": "🔍", "done": "✅", "failed": "❌"}.get(t.status, "•")
        short = (t.task_text[:60] + "…") if len(t.task_text) > 60 else t.task_text
        lines.append(f"{icon} #{t.id} [{t.status}] {short}")

    await message.answer("\n".join(lines))


async def handle_agents(message: Message) -> None:
    if not _is_owner(message):
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Agent).where(Agent.is_active == True))
        agents = result.scalars().all()

    if not agents:
        await message.answer("Активных агентов нет.\nДобавь через API: POST /api/agents/")
        return

    lines = []
    for a in agents:
        tools = ", ".join(t.get("type", "?") for t in (a.tools or []))
        lines.append(f"🤖 *{a.name}* [{a.role}]\n   Инструменты: {tools or '—'}")

    await message.answer("\n\n".join(lines), parse_mode="Markdown")


async def _run_and_reply(task_id: int, message: Message, status_msg_id: int) -> None:
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(AgentTask).where(AgentTask.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                return
            final = await Orchestrator().run(task, session)

        if final:
            await message.answer(f"✅ *Результат задачи #{task_id}:*\n\n{final}", parse_mode="Markdown")
        else:
            await message.answer(f"⚠️ Задача #{task_id} завершена, но ответа нет.")
    except Exception:
        log.exception("Task %d failed", task_id)
        await message.answer(f"❌ Задача #{task_id} завершилась с ошибкой. Проверь логи.")
