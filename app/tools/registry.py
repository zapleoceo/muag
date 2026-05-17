"""Loads tool instances from DB credentials and tool config from Agent.tools JSONB."""
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import get_credential
from app.tools.base import BaseTool

log = logging.getLogger(__name__)


async def build_tools(tool_configs: list[dict], session: AsyncSession) -> list[BaseTool]:
    tools: list[BaseTool] = []
    for cfg in tool_configs:
        tool = await _build_tool(cfg, session)
        if tool:
            tools.append(tool)
    return tools


async def _build_tool(cfg: dict, session: AsyncSession) -> BaseTool | None:
    type_ = cfg.get("type", "")
    try:
        if type_ == "perplexity":
            cred = await get_credential(session, "perplexity")
            if not cred:
                log.warning("No perplexity credential in DB")
                return None
            from app.tools.perplexity_api import PerplexityTool
            return PerplexityTool(api_key=cred.credentials["api_key"])

        if type_ == "poster":
            cred = await get_credential(session, "poster")
            if not cred:
                log.warning("No poster credential in DB")
                return None
            from app.tools.poster_api import PosterTool
            return PosterTool(token=cred.credentials["token"])

        if type_ == "trello":
            cred = await get_credential(session, "trello")
            if not cred:
                log.warning("No trello credential in DB")
                return None
            from app.tools.trello_api import TrelloTool
            return TrelloTool(
                api_key=cred.credentials["api_key"],
                token=cred.credentials["token"],
            )

        if type_ == "gmail":
            cred = await get_credential(session, "gmail")
            if not cred:
                log.warning("No gmail credential in DB")
                return None
            from app.tools.gmail_api import GmailTool
            return GmailTool(credentials_json=cred.credentials["credentials_json"])

        if type_ == "muai_rag":
            from app.tools.muai_rag import MuaiRagTool
            return MuaiRagTool()

        log.warning("Unknown tool type: %s", type_)
        return None
    except Exception:
        log.exception("Failed to build tool %s", type_)
        return None
