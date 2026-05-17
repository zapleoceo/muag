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


@router.message()
async def msg_any(message: Message, bot: Bot) -> None:
    """Catch-all: route by chat type."""
    chat_type = message.chat.type if message.chat else ""

    if chat_type == "private":
        await handler.handle_free_message(message)
    elif chat_type in ("group", "supergroup"):
        await handler.handle_group_mention(message, bot)
