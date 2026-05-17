"""Owner approval flow — sends action confirmation before agent executes."""
import logging

from aiogram import Bot
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import AgentTask

log = logging.getLogger(__name__)


def build_approval_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Выполнить", callback_data=f"approve:{task_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"reject:{task_id}"),
    ]])


async def ask_owner(bot: Bot, owner_id: int, task_id: int, preview: str) -> None:
    """Send approval request to owner before executing an action task."""
    short = (preview[:300] + "…") if len(preview) > 300 else preview
    text = (
        f"🤖 *Агент хочет выполнить действие* (задача #{task_id}):\n\n"
        f"{short}\n\n"
        f"Подтвердить?"
    )
    await bot.send_message(
        owner_id,
        text,
        parse_mode="Markdown",
        reply_markup=build_approval_keyboard(task_id),
    )
    log.info("Approval requested for task %d", task_id)


async def handle_approve(query: CallbackQuery) -> None:
    task_id = int(query.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AgentTask).where(AgentTask.id == task_id))
        task = result.scalar_one_or_none()
        if task:
            task.owner_approved = True
            await session.commit()

    await query.message.edit_text(
        query.message.text + "\n\n✅ *Одобрено*", parse_mode="Markdown"
    )
    await query.answer("Одобрено")
    log.info("Task %d approved by owner", task_id)


async def handle_reject(query: CallbackQuery) -> None:
    task_id = int(query.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AgentTask).where(AgentTask.id == task_id))
        task = result.scalar_one_or_none()
        if task:
            task.owner_approved = False
            task.status = "failed"
            await session.commit()

    await query.message.edit_text(
        query.message.text + "\n\n❌ *Отменено*", parse_mode="Markdown"
    )
    await query.answer("Отменено")
    log.info("Task %d rejected by owner", task_id)
