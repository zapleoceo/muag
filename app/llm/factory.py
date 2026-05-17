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
    api_key = settings.gemini_api_key
    if not api_key:
        log.warning("No GEMINI_API_KEY configured — LLM will not work")
        from app.llm.stub import StubProvider
        return StubProvider()

    from app.llm.gemini import GeminiProvider
    log.info("LLM: GeminiProvider (gemini-2.5-flash)")
    return GeminiProvider(api_key=api_key)
