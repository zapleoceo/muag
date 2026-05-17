"""Webhook trigger endpoint — POST /webhook/{name} creates a task."""
import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import AgentTask, AgentTrigger
from app.db.repository import save_task

log = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook")


class WebhookPayload(BaseModel):
    text: str | None = None
    data: dict = {}


@router.post("/{name}", status_code=202)
async def receive_webhook(name: str, request: Request) -> dict:
    """Accept external webhook and create a task for the matching trigger."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AgentTrigger).where(
                AgentTrigger.name == name,
                AgentTrigger.type == "webhook",
                AgentTrigger.is_active == True,
            )
        )
        trigger = result.scalar_one_or_none()

    if not trigger:
        raise HTTPException(status_code=404, detail=f"Webhook trigger '{name}' not found or inactive")

    # Parse body
    try:
        body = await request.json()
    except Exception:
        body = {}

    # Build task text from template or raw body
    template: str = trigger.config.get("task_template", "")
    if template:
        task_text = template.format(**body) if body else template
    else:
        task_text = body.get("text") or str(body)[:500]

    async with AsyncSessionLocal() as session:
        task = AgentTask(
            trigger_type="webhook",
            trigger_data=body,
            task_text=task_text,
            status="queued",
        )
        task = await save_task(session, task)

    log.info("Webhook '%s' created task %d: %s", name, task.id, task_text[:80])
    return {"task_id": task.id, "status": "queued"}
