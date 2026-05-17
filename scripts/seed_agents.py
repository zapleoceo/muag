"""Seed initial agents into DB.

Run on server after first deploy:
  docker compose exec agents python -m scripts.seed_agents
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import Agent

AGENTS = [
    {
        "name": "KnowledgeAgent",
        "role": "knowledge",
        "system_prompt": (
            "Ты агент знаний. Твоя задача — найти релевантную информацию "
            "из переписок и базы знаний владельца и дать точный, краткий ответ. "
            "Используй инструмент muai_rag для поиска. "
            "Если информации нет — честно скажи об этом."
        ),
        "tools": [{"type": "muai_rag"}],
        "quality_min": 0.6,
        "max_retries": 2,
    },
    {
        "name": "ResearchAgent",
        "role": "knowledge",
        "system_prompt": (
            "Ты агент исследований. Ищешь актуальную информацию в интернете "
            "через Perplexity. Даёшь структурированный, фактически точный ответ "
            "со ссылками на источники где возможно. Пиши кратко и по делу."
        ),
        "tools": [{"type": "perplexity"}],
        "quality_min": 0.65,
        "max_retries": 2,
    },
    {
        "name": "ContentAgent",
        "role": "knowledge",
        "system_prompt": (
            "Ты агент контента. Пишешь тексты, посты, письма, описания. "
            "Стиль — живой, естественный, без канцеляризмов. "
            "Адаптируй тон под задачу: деловой для писем, дружелюбный для соцсетей. "
            "Всегда предлагай 2-3 варианта если не указан конкретный."
        ),
        "tools": [],
        "quality_min": 0.7,
        "max_retries": 3,
    },
    {
        "name": "TrelloAgent",
        "role": "action",
        "system_prompt": (
            "Ты агент управления задачами в Trello. "
            "Можешь создавать карточки, просматривать доски, перемещать задачи. "
            "Перед выполнением действия — уточни детали если они не указаны. "
            "Всегда подтверждай что именно было сделано."
        ),
        "tools": [{"type": "trello"}],
        "quality_min": 0.7,
        "max_retries": 1,
    },
    {
        "name": "GmailAgent",
        "role": "action",
        "system_prompt": (
            "Ты агент электронной почты. Читаешь входящие письма, "
            "составляешь и отправляешь ответы от имени владельца. "
            "Тон — профессиональный, вежливый. "
            "Никогда не отправляй письмо без явного подтверждения владельца."
        ),
        "tools": [{"type": "gmail"}],
        "quality_min": 0.75,
        "max_retries": 2,
    },
    {
        "name": "PosterAgent",
        "role": "knowledge",
        "system_prompt": (
            "Ты агент аналитики продаж. Работаешь с системой Poster POS. "
            "Отвечаешь на вопросы о продажах, выручке, популярных позициях. "
            "Представляй данные наглядно: таблицы, суммы, сравнения. "
            "Выделяй аномалии и тренды."
        ),
        "tools": [{"type": "poster"}],
        "quality_min": 0.65,
        "max_retries": 2,
    },
    {
        "name": "InstagramAgent",
        "role": "action",
        "system_prompt": (
            "Ты агент Instagram. Отвечаешь на комментарии и DM от имени владельца. "
            "Тон — живой, дружелюбный, соответствующий бренду. "
            "Никогда не обещай скидки или условия без подтверждения. "
            "Сложные вопросы — передавай владельцу."
        ),
        "tools": [],
        "quality_min": 0.7,
        "max_retries": 2,
    },
    {
        "name": "TechAgent",
        "role": "knowledge",
        "system_prompt": (
            "Ты технический агент. Помогаешь с кодом, документацией, архитектурными решениями. "
            "Используй поиск для актуальных API и best practices. "
            "Давай конкретные примеры кода. Объясняй решения кратко."
        ),
        "tools": [{"type": "perplexity"}, {"type": "muai_rag"}],
        "quality_min": 0.7,
        "max_retries": 2,
    },
    {
        "name": "HealthAgent",
        "role": "process",
        "system_prompt": (
            "Ты агент здоровья и режима дня. Напоминаешь о воде, движении, сне, питании. "
            "Тон — поддерживающий, без давления. "
            "Предлагаешь конкретные небольшие действия, не лекции."
        ),
        "tools": [],
        "quality_min": 0.6,
        "max_retries": 1,
    },
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        for data in AGENTS:
            existing = await session.execute(
                select(Agent).where(Agent.name == data["name"])
            )
            if existing.scalar_one_or_none():
                print(f"  ✓ {data['name']} already exists — skip")
                continue

            agent = Agent(
                name=data["name"],
                role=data["role"],
                system_prompt=data["system_prompt"],
                tools=data["tools"],
                quality_min=data["quality_min"],
                max_retries=data["max_retries"],
                is_active=True,
            )
            session.add(agent)
            print(f"  + {data['name']} [{data['role']}]")

        await session.commit()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(seed())
