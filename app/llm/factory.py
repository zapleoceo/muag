import logging

from app.config import get_settings
from app.llm.base import LLMProvider

log = logging.getLogger(__name__)

_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        _provider = _build_provider()
    return _provider


def _build_provider() -> LLMProvider:
    settings = get_settings()

    if settings.gemini_api_key:
        from app.llm.gemini import GeminiProvider
        log.info("LLM: GeminiProvider (gemini-2.5-flash)")
        return GeminiProvider(api_key=settings.gemini_api_key)

    if settings.openai_api_key:
        from app.llm.openai_provider import OpenAIProvider
        log.info("LLM: OpenAIProvider (gpt-4o-mini)")
        return OpenAIProvider(api_key=settings.openai_api_key)

    log.warning("No LLM API key configured — using stub")
    from app.llm.stub import StubProvider
    return StubProvider()
