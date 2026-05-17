"""Read-only API for triggers list (UI display)."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_owner
from app.db.database import AsyncSessionLocal
from app.db.models import AgentTrigger

router = APIRouter(prefix="/api/triggers", dependencies=[Depends(require_owner)])


async def _session() -> AsyncSession:
    async with AsyncSessionLocal() as s:
        yield s


@router.get("/", response_model=list[dict])
async def list_triggers(session: AsyncSession = Depends(_session)):
    result = await session.execute(select(AgentTrigger))
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "type": r.type,
            "agent_names": r.agent_names or [],
            "is_active": r.is_active,
            "topic_thread_id": r.topic_thread_id,
            "last_fired_at": r.last_fired_at.isoformat() if r.last_fired_at else None,
        }
        for r in rows
    ]
