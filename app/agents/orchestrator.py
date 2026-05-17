"""Orchestrator: plan → run agents in parallel → reflect → synthesize → act."""
import asyncio
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentResponse, BaseAgent
from app.agents.registry import load_agents
from app.db.models import AgentTask
from app.db.repository import save_task, update_task_status
from app.llm.base import LLMMessage, LLMProvider
from app.llm.factory import get_llm_provider

log = logging.getLogger(__name__)

_PLAN_PROMPT = """You are an orchestrator of a multi-agent system.
Given a task, output a JSON plan:
{
  "agents": ["agent_name_1", "agent_name_2"],
  "requests": {
    "agent_name_1": "specific sub-task for this agent",
    "agent_name_2": "specific sub-task for this agent"
  }
}
Use only agents that are available. Respond ONLY with valid JSON."""

_SYNTHESIS_PROMPT = """You are synthesizing agent responses into a final answer.
Be concise, accurate, and actionable. Write in the owner's voice."""


class Orchestrator:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self._provider = provider or get_llm_provider()

    async def run(self, task: AgentTask, session: AsyncSession) -> str:
        await update_task_status(session, task.id, "planning")
        agents = await load_agents(session)

        plan = await self._plan(task.task_text, list(agents.keys()))
        await update_task_status(session, task.id, "running", plan=plan)

        selected = {name: agents[name] for name in plan.get("agents", []) if name in agents}
        requests = plan.get("requests", {})

        results = await self._run_agents(selected, requests)

        await update_task_status(session, task.id, "reflecting", agent_calls=_format_calls(results))

        final = await self._synthesize(task.task_text, results)
        await update_task_status(session, task.id, "done", final_text=final)
        return final

    async def _plan(self, task_text: str, agent_names: list[str]) -> dict:
        messages = [
            LLMMessage(role="system", content=_PLAN_PROMPT),
            LLMMessage(
                role="user",
                content=f"Available agents: {', '.join(agent_names)}\n\nTask: {task_text}",
            ),
        ]
        raw = await self._provider.complete(messages)
        if not raw:
            return {"agents": [], "requests": {}}
        try:
            return json.loads(_strip_fences(raw))
        except json.JSONDecodeError:
            log.warning("Plan JSON parse failed: %s", raw[:200])
            return {"agents": [], "requests": {}}

    async def _run_agents(
        self, agents: dict[str, BaseAgent], requests: dict[str, str]
    ) -> dict[str, AgentResponse]:
        tasks = {
            name: asyncio.create_task(agent.handle(requests.get(name, "")))
            for name, agent in agents.items()
        }
        results = {}
        for name, task in tasks.items():
            try:
                results[name] = await task
            except Exception:
                log.exception("Agent %s failed", name)
                results[name] = AgentResponse(text="[error]", score=0.0)
        return results

    async def _synthesize(self, original_task: str, results: dict[str, AgentResponse]) -> str:
        useful = {name: r for name, r in results.items() if r.text and r.text != "[error]"}
        if not useful:
            return ""
        context_parts = [f"[{name}] (score={r.score:.2f})\n{r.text}" for name, r in useful.items()]
        context = "\n\n".join(context_parts)
        messages = [
            LLMMessage(role="system", content=_SYNTHESIS_PROMPT),
            LLMMessage(
                role="user",
                content=f"Original task: {original_task}\n\nAgent responses:\n{context}",
            ),
        ]
        result = await self._provider.complete(messages)
        return result or ""


def _strip_fences(text: str) -> str:
    """Strip markdown code fences (```json ... ```) from LLM output."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return text.strip()


def _format_calls(results: dict[str, AgentResponse]) -> list[dict]:
    return [
        {
            "agent": name,
            "response": r.text,
            "score": r.score,
            "retries": r.retries,
            "tool_calls": r.tool_calls,
        }
        for name, r in results.items()
    ]
