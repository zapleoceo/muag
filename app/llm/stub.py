from app.llm.base import LLMMessage, LLMProvider


class StubProvider(LLMProvider):
    async def complete(self, messages: list[LLMMessage]) -> str | None:
        last = next((m.content for m in reversed(messages) if m.role == "user"), "")
        return f"[stub] echo: {last}"
