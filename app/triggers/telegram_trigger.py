"""Telegram trigger — reads new messages in the office group, creates tasks.

Pattern detected:
  @agent_name: <task text>           — task for specific agent
  /vera <task text>                  — task for orchestrator (all agents)
"""
import logging

import httpx

from app.config import get_settings
from app.triggers.base import BaseTrigger, TriggerEvent

log = logging.getLogger(__name__)

_TG_API = "https://api.telegram.org/bot{token}"
_VERA_CMD = "/vera"


class TelegramTrigger(BaseTrigger):
    name = "telegram"
    type = "telegram"

    def __init__(self, config: dict, agent_names: list[str]) -> None:
        self._config = config
        self._agent_names = agent_names
        self._last_update_id: int = 0

    async def poll(self) -> list[TriggerEvent]:
        settings = get_settings()
        token = settings.main_bot_token
        if not token:
            return []

        url = f"{_TG_API.format(token=token)}/getUpdates"
        params = {"offset": self._last_update_id + 1, "timeout": 0, "allowed_updates": ["message"]}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            log.exception("TelegramTrigger poll failed")
            return []

        events: list[TriggerEvent] = []
        for update in data.get("result", []):
            self._last_update_id = max(self._last_update_id, update["update_id"])
            event = self._parse_update(update)
            if event:
                events.append(event)

        return events

    def _parse_update(self, update: dict) -> TriggerEvent | None:
        msg = update.get("message", {})
        text: str = msg.get("text", "")
        chat_id: int = msg.get("chat", {}).get("id", 0)
        thread_id: int | None = msg.get("message_thread_id")

        office_group = get_settings().office_group_id
        if office_group and chat_id != office_group:
            return None

        if not text:
            return None

        # /vera <task> — route to all agents via orchestrator
        if text.startswith(_VERA_CMD):
            task_text = text.removeprefix(_VERA_CMD).strip()
            if not task_text:
                return None
            return TriggerEvent(
                trigger_name="telegram",
                trigger_type="telegram",
                task_text=task_text,
                raw_data={"chat_id": chat_id, "thread_id": thread_id, "update": update},
                agent_names=[],
                topic_thread_id=thread_id,
            )

        # @AgentName: <task>
        for name in self._agent_names:
            prefix = f"@{name}:"
            if text.lower().startswith(prefix.lower()):
                task_text = text[len(prefix):].strip()
                if task_text:
                    return TriggerEvent(
                        trigger_name="telegram",
                        trigger_type="telegram",
                        task_text=task_text,
                        raw_data={"chat_id": chat_id, "thread_id": thread_id},
                        agent_names=[name],
                        topic_thread_id=thread_id,
                    )

        return None
