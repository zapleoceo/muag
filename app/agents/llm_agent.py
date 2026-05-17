"""Generic LLM-backed agent with optional tools and reflection."""
import json
import logging

from app.agents.base import AgentResponse, BaseAgent
from app.agents.reflection import grade
from app.llm.base import LLMMessage, LLMProvider
from app.tools.base import BaseTool

log = logging.getLogger(__name__)


class LLMAgent(BaseAgent):
    def __init__(
        self,
        name: str,
        role: str,
        system_prompt: str,
        provider: LLMProvider,
        tools: list[BaseTool],
        quality_min: float = 0.65,
        max_retries: int = 2,
    ) -> None:
        self.name = name
        self.role = role
        self._system_prompt = system_prompt
        self._provider = provider
        self._tools = {t.name: t for t in tools}
        self._quality_min = quality_min
        self._max_retries = max_retries

    async def handle(self, request: str, context: str = "") -> AgentResponse:
        messages = self._build_messages(request, context)
        feedback = ""
        retries = 0

        for attempt in range(self._max_retries + 1):
            if feedback:
                messages.append(
                    LLMMessage(role="user", content=f"[Revise your answer. Feedback: {feedback}]")
                )

            raw = await self._provider.complete(messages)
            if not raw:
                return AgentResponse(text="", score=0.0, retries=attempt)

            # Check for tool calls embedded in response
            tool_calls, clean_text = await self._maybe_run_tools(raw, messages)

            score, feedback = await grade(self._provider, request, clean_text)
            log.info("%s attempt %d score=%.2f", self.name, attempt, score)

            if score >= self._quality_min or attempt == self._max_retries:
                return AgentResponse(
                    text=clean_text,
                    score=score,
                    tool_calls=tool_calls,
                    retries=attempt,
                )
            retries = attempt + 1

        return AgentResponse(text=raw or "", score=0.0, retries=retries)

    def _build_messages(self, request: str, context: str) -> list[LLMMessage]:
        tools_desc = "\n".join(f"- {t.schema()['name']}: {t.schema()['description']}" for t in self._tools.values())
        system = self._system_prompt
        if tools_desc:
            system += f"\n\nAvailable tools:\n{tools_desc}\nTo use a tool, output: TOOL:<name> ARGS:<json>"

        msgs = [LLMMessage(role="system", content=system)]
        if context:
            msgs.append(LLMMessage(role="user", content=f"[Context]\n{context}"))
        msgs.append(LLMMessage(role="user", content=request))
        return msgs

    async def _maybe_run_tools(
        self, raw: str, messages: list[LLMMessage]
    ) -> tuple[list[dict], str]:
        tool_calls: list[dict] = []
        lines = raw.split("\n")
        result_lines = []

        for line in lines:
            if line.startswith("TOOL:"):
                parts = line.split(" ARGS:", 1)
                tool_name = parts[0].replace("TOOL:", "").strip()
                args = json.loads(parts[1]) if len(parts) > 1 else {}
                if tool := self._tools.get(tool_name):
                    result = await tool.run(**args)
                    tool_calls.append({"tool": tool_name, "args": args, "result": result.data})
                    messages.append(LLMMessage(role="assistant", content=line))
                    messages.append(
                        LLMMessage(role="user", content=f"[Tool result for {tool_name}]: {result.data}")
                    )
                    # Re-complete after tool result
                    continuation = await self._provider.complete(messages)
                    if continuation:
                        result_lines.append(continuation)
                    continue
            result_lines.append(line)

        return tool_calls, "\n".join(result_lines).strip() or raw
