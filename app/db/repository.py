from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Agent, AgentTask, AgentTrigger, ToolCredential


async def get_active_agents(session: AsyncSession) -> list[Agent]:
    result = await session.execute(select(Agent).where(Agent.is_active == True))
    return list(result.scalars().all())


async def get_agent_by_name(session: AsyncSession, name: str) -> Agent | None:
    result = await session.execute(select(Agent).where(Agent.name == name))
    return result.scalar_one_or_none()


async def save_task(session: AsyncSession, task: AgentTask) -> AgentTask:
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def update_task_status(session: AsyncSession, task_id: int, status: str, **fields) -> None:
    await session.execute(
        update(AgentTask)
        .where(AgentTask.id == task_id)
        .values(status=status, **fields)
    )
    await session.commit()


async def get_active_triggers(session: AsyncSession) -> list[AgentTrigger]:
    result = await session.execute(select(AgentTrigger).where(AgentTrigger.is_active == True))
    return list(result.scalars().all())


async def get_credential(session: AsyncSession, type_: str) -> ToolCredential | None:
    result = await session.execute(
        select(ToolCredential)
        .where(ToolCredential.type == type_, ToolCredential.is_active == True)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_all_credentials(session: AsyncSession) -> list[ToolCredential]:
    result = await session.execute(select(ToolCredential))
    return list(result.scalars().all())
