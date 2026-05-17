"""HTTP LLM provider — delegates to myAI's /api/internal/llm/complete endpoint."""
import logging

import httpx

from app.llm.base import LLMMessage, LLMProvider

log = logging.getLogger(__name__)


class HttpLLMProvider(LLMProvider):
    def __init__(self, base_url: str, secret: str) -> None:
        self._url = base_url.rstrip("/") + "/api/internal/llm/complete"
        self._headers = {"Authorization": f"Bearer {secret}"}

    async def complete(self, messages: list[LLMMessage]) -> str | None:
        payload = {"messages": [{"role": m.role, "content": m.content} for m in messages]}
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(self._url, json=payload, headers=self._headers)
                resp.raise_for_status()
                return resp.json().get("text")
        except Exception:
            log.exception("HttpLLMProvider request failed")
            return None
