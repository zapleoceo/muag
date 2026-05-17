"""TelegramAgent — orchestrator communicates with agents via their Telegram topics.

Flow:
  1. Orchestrator posts task to agent's home_topic_id via main bot
  2. Agent's own bot reads the message and replies
  3. Orchestrator polls for the reply (with timeout)
  4. Returns reply text as AgentResponse
"""
import asyncio
import logging

import httpx

from app.agents.base import AgentResponse, BaseAgent
from app.config import get_settings

log = logging.getLogger(__name__)

_TG_API = "https://api.telegram.org/bot{token}"
_REPLY_TIMEOUT = 60   # seconds to wait for agent reply
_POLL_INTERVAL = 2    # seconds between reply checks


class TelegramAgent(BaseAgent):
    """Wraps a real Telegram bot as an agent — posts task, waits for reply."""

    def __init__(
        self,
        name: str,
        role: str,
        bot_token: str,
        home_topic_id: int,
        office_group_id: int,
    ) -> None:
        self.name = name
        self.role = role
        self._bot_token = bot_token
        self._topic_id = home_topic_id
        self._group_id = office_group_id

    async def handle(self, request: str, context: str = "") -> AgentResponse:
        sent_msg_id = await self._send_task(request)
        if not sent_msg_id:
            return AgentResponse(text="[failed to send task]", score=0.0)

        reply = await self._wait_for_reply(sent_msg_id)
        return AgentResponse(
            text=reply or "[no reply within timeout]",
            score=0.8 if reply else 0.0,
        )

    async def _send_task(self, text: str) -> int | None:
        settings = get_settings()
        token = settings.main_bot_token
        url = f"{_TG_API.format(token=token)}/sendMessage"
        payload = {
            "chat_id": self._group_id,
            "message_thread_id": self._topic_id,
            "text": f"🎯 {text}",
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload)
                data = resp.json()
                if data.get("ok"):
                    return data["result"]["message_id"]
        except Exception:
            log.exception("TelegramAgent %s: failed to send task", self.name)
        return None

    async def _wait_for_reply(self, task_msg_id: int) -> str | None:
        """Poll getUpdates for a reply to task_msg_id in our topic."""
        settings = get_settings()
        token = self._bot_token
        url = f"{_TG_API.format(token=token)}/getUpdates"
        offset = 0
        deadline = asyncio.get_event_loop().time() + _REPLY_TIMEOUT

        while asyncio.get_event_loop().time() < deadline:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(url, params={"offset": offset, "timeout": 0})
                    data = resp.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    reply_to = msg.get("reply_to_message", {})
                    if (
                        msg.get("message_thread_id") == self._topic_id
                        and reply_to.get("message_id") == task_msg_id
                    ):
                        return msg.get("text", "")
            except Exception:
                log.exception("TelegramAgent %s: poll error", self.name)

            await asyncio.sleep(_POLL_INTERVAL)

        log.warning("TelegramAgent %s: reply timeout for msg %d", self.name, task_msg_id)
        return None
