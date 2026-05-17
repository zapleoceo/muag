"""Loads agents from DB and instantiates them with tools."""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.agents.llm_agent import LLMAgent
from app.db.models import Agent as AgentModel
from app.db.repository import get_active_agents
from app.llm.factory import get_llm_provider
from app.tools.registry import build_tools

log = logging.getLogger(__name__)


async def load_agents(session: AsyncSession) -> dict[str, BaseAgent]:
    rows = await get_active_agents(session)
    agents: dict[str, BaseAgent] = {}
    for row in rows:
        agent = await _instantiate(row, session)
        if agent:
            agents[row.name] = agent
    log.info("Loaded %d agents", len(agents))
    return agents


async def _instantiate(row: AgentModel, session: AsyncSession) -> BaseAgent | None:
    try:
        tools = await build_tools(row.tools or [], session)
        return LLMAgent(
            name=row.name,
            role=row.role,
            system_prompt=row.system_prompt,
            provider=get_llm_provider(),
            tools=tools,
            quality_min=row.quality_min or 0.65,
            max_retries=row.max_retries or 2,
        )
    except Exception:
        log.exception("Failed to instantiate agent %s", row.name)
        return None
