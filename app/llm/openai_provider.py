import logging

from app.llm.base import LLMMessage, LLMProvider

log = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        import openai
        self._client = openai.AsyncOpenAI(api_key=api_key)
        self._model = model

    async def complete(self, messages: list[LLMMessage]) -> str | None:
        try:
            payload = [{"role": m.role, "content": m.content} for m in messages]
            resp = await self._client.chat.completions.create(
                model=self._model,
                messages=payload,
            )
            return resp.choices[0].message.content if resp.choices else None
        except Exception:
            log.exception("OpenAI complete failed")
            return None
