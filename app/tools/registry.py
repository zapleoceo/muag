"""Loads tool instances by fetching credentials from myAI internal API."""
import logging

import httpx

from app.config import get_settings
from app.tools.base import BaseTool

log = logging.getLogger(__name__)


async def build_tools(tool_configs: list[dict]) -> list[BaseTool]:
    tools: list[BaseTool] = []
    for cfg in tool_configs:
        tool = await _build_tool(cfg)
        if tool:
            tools.append(tool)
    return tools


async def _fetch_cred(type_: str) -> dict | None:
    settings = get_settings()
    url = f"{settings.muai_api_url}/api/internal/vera-credentials/{type_}"
    headers = {"Authorization": f"Bearer {settings.muai_api_secret}"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()["data"]
    except Exception:
        log.exception("Failed to fetch credential %s from myAI", type_)
        return None


async def _build_tool(cfg: dict) -> BaseTool | None:
    type_ = cfg.get("type", "")
    try:
        if type_ == "perplexity":
            cred = await _fetch_cred("perplexity")
            if not cred:
                log.warning("No perplexity credential in myAI")
                return None
            from app.tools.perplexity_api import PerplexityTool
            return PerplexityTool(api_key=cred["api_key"])

        if type_ == "poster":
            cred = await _fetch_cred("poster")
            if not cred:
                log.warning("No poster credential in myAI")
                return None
            from app.tools.poster_api import PosterTool
            return PosterTool(token=cred["token"])

        if type_ == "trello":
            cred = await _fetch_cred("trello")
            if not cred:
                log.warning("No trello credential in myAI")
                return None
            from app.tools.trello_api import TrelloTool
            return TrelloTool(api_key=cred["api_key"], token=cred["token"])

        if type_ == "gmail":
            cred = await _fetch_cred("gmail")
            if not cred:
                log.warning("No gmail credential in myAI")
                return None
            from app.tools.gmail_api import GmailTool
            import json
            return GmailTool(credentials_json=json.dumps(cred))

        if type_ == "muai_rag":
            from app.tools.muai_rag import MuaiRagTool
            return MuaiRagTool()

        log.warning("Unknown tool type: %s", type_)
        return None
    except Exception:
        log.exception("Failed to build tool %s", type_)
        return None
