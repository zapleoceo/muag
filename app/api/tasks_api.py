"""Task queue: submit tasks, view status, trigger orchestrator."""
import asyncio

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import Orchestrator
from app.api.auth import require_owner
from app.db.database import AsyncSessionLocal
from app.db.models import AgentTask
from app.db.repository import save_task

router = APIRouter(prefix="/api/tasks", dependencies=[Depends(require_owner)])


class TaskIn(BaseModel):
    task_text: str
    trigger_type: str = "manual"
    topic_thread_id: int | None = None


async def _session() -> AsyncSession:
    async with AsyncSessionLocal() as s:
        yield s


@router.post("/", status_code=202)
async def submit_task(body: TaskIn, session: AsyncSession = Depends(_session)):
    task = AgentTask(
        trigger_type=body.trigger_type,
        task_text=body.task_text,
        topic_thread_id=body.topic_thread_id,
        status="queued",
    )
    task = await save_task(session, task)
    from app.services.limiter import run_with_limit
    asyncio.create_task(run_with_limit(_run_task(task.id)))
    return {"task_id": task.id, "status": "queued"}


@router.get("/", response_model=list[dict])
async def list_tasks(limit: int = 20, session: AsyncSession = Depends(_session)):
    result = await session.execute(
        select(AgentTask).order_by(AgentTask.id.desc()).limit(limit)
    )
    return [_to_dict(t) for t in result.scalars().all()]


@router.get("/{task_id}")
async def get_task(task_id: int, session: AsyncSession = Depends(_session)):
    result = await session.execute(select(AgentTask).where(AgentTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        return {"error": "not found"}
    return _to_dict(task)


async def _run_task(task_id: int) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AgentTask).where(AgentTask.id == task_id))
        task = result.scalar_one_or_none()
        if task:
            await Orchestrator().run(task, session)


def _to_dict(t: AgentTask) -> dict:
    return {
        "id": t.id,
        "trigger_type": t.trigger_type,
        "task_text": t.task_text,
        "status": t.status,
        "final_text": t.final_text,
        "agent_calls": t.agent_calls,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }
