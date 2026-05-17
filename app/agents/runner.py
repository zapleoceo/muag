"""AgentRunner — starts a separate aiogram polling loop per agent bot_token."""
import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import Agent

log = logging.getLogger(__name__)

# active bot instances keyed by agent name
_bots: dict[str, Bot] = {}
_tasks: dict[str, asyncio.Task] = {}


async def start_agent_runners() -> None:
    """Load all agents with bot_token from DB and start polling."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Agent).where(Agent.is_active == True, Agent.bot_token.isnot(None))
        )
        agents = result.scalars().all()

    for agent in agents:
        if agent.name not in _tasks or _tasks[agent.name].done():
            await _start_agent(agent.name, agent.bot_token, agent.home_topic_id)

    log.info("AgentRunner: %d agent bots started", len(_tasks))


async def stop_agent_runners() -> None:
    for name, task in _tasks.items():
        task.cancel()
        log.info("AgentRunner: stopped bot for %s", name)
    for bot in _bots.values():
        await bot.session.close()
    _tasks.clear()
    _bots.clear()


async def _start_agent(name: str, token: str, home_topic_id: int | None) -> None:
    bot = Bot(token=token)
    dp = Dispatcher()
    router = _build_agent_router(name, home_topic_id)
    dp.include_router(router)
    _bots[name] = bot
    _tasks[name] = asyncio.create_task(
        _poll(bot, dp, name),
        name=f"agent-bot-{name}",
    )
    log.info("AgentRunner: started bot for %s (topic=%s)", name, home_topic_id)


async def _poll(bot: Bot, dp: Dispatcher, name: str) -> None:
    try:
        await dp.start_polling(bot, allowed_updates=["message"])
    except asyncio.CancelledError:
        pass
    except Exception:
        log.exception("AgentRunner: bot %s polling crashed", name)


def _build_agent_router(agent_name: str, home_topic_id: int | None) -> Router:
    """Each agent bot responds to messages in its own topic thread."""
    router = Router()

    @router.message()
    async def handle_message(message: Message) -> None:
        # Only respond in the agent's home topic
        if home_topic_id and message.message_thread_id != home_topic_id:
            return

        text = message.text or message.caption or ""
        if not text:
            return

        log.info("Agent %s received: %s", agent_name, text[:80])

        # Run orchestrator targeted at this single agent
        from app.agents.orchestrator import Orchestrator
        from app.db.database import AsyncSessionLocal
        from app.db.models import AgentTask
        from app.db.repository import save_task

        async with AsyncSessionLocal() as session:
            task = AgentTask(
                trigger_type="telegram",
                task_text=text,
                topic_thread_id=home_topic_id,
                status="queued",
            )
            task = await save_task(session, task)
            # Override plan to use only this agent
            from app.agents.registry import load_agents
            agents = await load_agents(session)
            agent = agents.get(agent_name)
            if not agent:
                await message.reply(f"⚠️ Агент {agent_name} не найден в реестре.")
                return
            response = await agent.handle(text)
            await session.commit()

        await message.reply(response.text or "🤷 Нет ответа")

    return router
