import logging

import google.generativeai as genai

from app.llm.base import LLMMessage, LLMProvider

log = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)

    async def complete(self, messages: list[LLMMessage]) -> str | None:
        # Gemini SDK is sync; run in thread to keep async contract
        import asyncio

        def _call() -> str | None:
            history = []
            system_text = ""
            for m in messages:
                if m.role == "system":
                    system_text = m.content
                elif m.role == "user":
                    history.append({"role": "user", "parts": [m.content]})
                elif m.role == "assistant":
                    history.append({"role": "model", "parts": [m.content]})

            model = self._model
            if system_text:
                model = genai.GenerativeModel(
                    self._model.model_name,
                    system_instruction=system_text,
                )
            chat = model.start_chat(history=history[:-1] if len(history) > 1 else [])
            last = history[-1]["parts"][0] if history else ""
            resp = chat.send_message(last)
            return resp.text if resp.text else None

        try:
            return await asyncio.get_event_loop().run_in_executor(None, _call)
        except Exception:
            log.exception("Gemini complete failed")
            return None
