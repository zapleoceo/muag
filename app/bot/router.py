"""Aiogram router — all bot commands and callbacks live here."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot import approval, handler

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 VERA — Virtual Executive Response Architecture\n\n"
        "Команды:\n"
        "/task <текст> — поставить задачу агентам\n"
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
