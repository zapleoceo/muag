"""LLM-based quality grader for agent responses."""
import logging

from app.llm.base import LLMMessage, LLMProvider

log = logging.getLogger(__name__)

_GRADER_PROMPT = """You are a quality evaluator.
Given a task and an agent response, output a JSON object with:
- "score": float 0.0–1.0 (1.0 = perfect, 0.0 = completely wrong/useless)
- "feedback": one sentence explaining the score

Respond ONLY with valid JSON, no markdown fences."""


async def grade(provider: LLMProvider, task: str, response: str) -> tuple[float, str]:
    messages = [
        LLMMessage(role="system", content=_GRADER_PROMPT),
        LLMMessage(
            role="user",
            content=f"Task: {task}\n\nAgent response:\n{response}",
        ),
    ]
    raw = await provider.complete(messages)
    if not raw:
        return 0.5, "Grader returned no output"

    import json
    try:
        data = json.loads(raw)
        return float(data.get("score", 0.5)), str(data.get("feedback", ""))
    except (json.JSONDecodeError, ValueError):
        log.warning("Grader JSON parse failed: %s", raw[:200])
        return 0.5, raw[:100]
