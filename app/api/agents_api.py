"""CRUD for agents."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_owner
from app.db.database import AsyncSessionLocal
from app.db.models import Agent

router = APIRouter(prefix="/api/agents", dependencies=[Depends(require_owner)])


class AgentIn(BaseModel):
    name: str
    role: str
    system_prompt: str
    bot_token: str | None = None
    bot_username: str | None = None
    tools: list[dict] = []
    kb_namespace: str | None = None
    home_topic_id: int | None = None
    quality_min: float = 0.65
    max_retries: int = 2
    is_active: bool = True


class AgentOut(AgentIn):
    id: int


async def _session() -> AsyncSession:
    async with AsyncSessionLocal() as s:
        yield s


@router.get("/", response_model=list[AgentOut])
async def list_agents(session: AsyncSession = Depends(_session)):
    result = await session.execute(select(Agent))
    return [_to_out(r) for r in result.scalars().all()]


@router.post("/", response_model=AgentOut, status_code=201)
async def create_agent(body: AgentIn, session: AsyncSession = Depends(_session)):
    agent = Agent(**body.model_dump())
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return _to_out(agent)


@router.put("/{agent_id}", response_model=AgentOut)
async def update_agent(agent_id: int, body: AgentIn, session: AsyncSession = Depends(_session)):
    result = await session.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    for key, val in body.model_dump().items():
        setattr(agent, key, val)
    await session.commit()
    return _to_out(agent)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: int, session: AsyncSession = Depends(_session)):
    await session.execute(delete(Agent).where(Agent.id == agent_id))
    await session.commit()


def _to_out(a: Agent) -> AgentOut:
    return AgentOut(
        id=a.id,
        name=a.name,
        role=a.role,
        system_prompt=a.system_prompt,
        bot_token=a.bot_token,
        bot_username=a.bot_username,
        tools=a.tools or [],
        kb_namespace=a.kb_namespace,
        home_topic_id=a.home_topic_id,
        quality_min=a.quality_min,
        max_retries=a.max_retries,
        is_active=a.is_active,
    )
