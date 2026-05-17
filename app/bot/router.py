"""Aiogram router — all bot commands and callbacks live here."""
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot import approval, handler

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 VERA — Virtual Executive Response Architecture\n\n"
        "Просто напиши мне что нужно сделать — в личку или упомяни в группе.\n\n"
        "Команды:\n"
        "/status — последние задачи\n"
        "/agents — список активных агентов"
    )


@router.message(Command("task"))
async def cmd_task(message: Message) -> None:
    await handler.handle_task(message)


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    await handler.handle_status(message)


@router.message(Command("agents"))
async def cmd_agents(message: Message) -> None:
    await handler.handle_agents(message)


@router.callback_query(F.data.startswith("approve:"))
async def cb_approve(query: CallbackQuery) -> None:
    await approval.handle_approve(query)


@router.callback_query(F.data.startswith("reject:"))
async def cb_reject(query: CallbackQuery) -> None:
    await approval.handle_reject(query)


# ─── Free-form messages ────────────────────────────────────────────────────

@router.message(F.chat.type == "private")
async def msg_private(message: Message) -> None:
    """Any message in DM from owner → treat as task."""
    await handler.handle_free_message(message)


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def msg_group(message: Message, bot: Bot) -> None:
    """Group message mentioning the bot → strip mention, treat as task."""
    await handler.handle_group_mention(message, bot)
