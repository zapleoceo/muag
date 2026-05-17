"""Command and free-form message handlers."""
import asyncio
import logging
import re

from aiogram import Bot
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


async def handle_free_message(message: Message) -> None:
    """DM from owner — any text is a task."""
    if not _is_owner(message):
        return
    text = (message.text or message.caption or "").strip()
    if not text:
        return
    await _dispatch(message, text, trigger_type="dm")


async def handle_group_mention(message: Message, bot: Bot) -> None:
    """Group message — only react if bot is mentioned."""
    if not _is_owner(message):
        return

    text = message.text or message.caption or ""
    me = await bot.me()
    username = me.username or ""

    # Check mention via entities (reliable)
    mentioned = False
    clean = text
    if message.entities:
        for ent in message.entities:
            if ent.type == "mention":
                mention_text = text[ent.offset: ent.offset + ent.length]
                if mention_text.lstrip("@").lower() == username.lower():
                    mentioned = True
                    # Remove the mention from text
                    clean = (text[: ent.offset] + text[ent.offset + ent.length:]).strip()
                    break

    # Fallback: plain @username in text
    if not mentioned and username and f"@{username}" in text:
        mentioned = True
        clean = text.replace(f"@{username}", "").strip()

    if not mentioned or not clean:
        return

    await _dispatch(message, clean, trigger_type="mention")


async def handle_task(message: Message) -> None:
    """/task <text> command."""
    if not _is_owner(message):
        return
    text = re.sub(r"^/task\S*", "", message.text or "").strip()
    if not text:
        await message.answer("❌ Укажи задачу: /task <текст>")
        return
    await _dispatch(message, text, trigger_type="command")


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

    icons = {"queued": "⏳", "planning": "🗺", "running": "⚙️",
             "reflecting": "🔍", "done": "✅", "failed": "❌"}
    lines = []
    for t in tasks:
        icon = icons.get(t.status, "•")
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
        await message.answer("Активных агентов нет.")
        return

    lines = []
    for a in agents:
        tools = ", ".join(t.get("type", "?") for t in (a.tools or []))
        lines.append(f"🤖 *{a.name}* [{a.role}]\n   Инструменты: {tools or '—'}")

    await message.answer("\n\n".join(lines), parse_mode="Markdown")


async def _dispatch(message: Message, text: str, trigger_type: str) -> None:
    """Save task and run orchestrator in background, reply with result."""
    status_msg = await message.answer("⏳ Принял, запускаю агентов…")

    async with AsyncSessionLocal() as session:
        task = AgentTask(trigger_type=trigger_type, task_text=text, status="queued")
        task = await save_task(session, task)
        task_id = task.id

    asyncio.create_task(_run_and_reply(task_id, message, status_msg.message_id))


async def _run_and_reply(task_id: int, message: Message, status_msg_id: int) -> None:
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(AgentTask).where(AgentTask.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                return
            final = await Orchestrator().run(task, session)

        if final:
            await message.answer(
                f"✅ *Результат #{task_id}:*\n\n{final}",
                parse_mode="Markdown",
            )
        else:
            await message.answer(f"⚠️ Задача #{task_id} завершена, но ответа нет.")
    except Exception:
        log.exception("Task %d failed", task_id)
        await message.answer(f"❌ Задача #{task_id} завершилась с ошибкой.")
