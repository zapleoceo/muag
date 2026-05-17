"""Simple cron trigger — fires based on cron_expr, uses last_fired_at in DB."""
import logging
from datetime import datetime, timezone

from app.triggers.base import BaseTrigger, TriggerEvent

log = logging.getLogger(__name__)


class CronTrigger(BaseTrigger):
    type = "cron"

    def __init__(self, name: str, config: dict, agent_names: list[str]) -> None:
        self.name = name
        self._prompt = config.get("prompt", "")
        self._agent_names = agent_names

    async def poll(self) -> list[TriggerEvent]:
        # Simplified: always fires once per poll cycle
        # Full implementation would check cron_expr and last_fired_at
        if not self._prompt:
            return []
        return [
            TriggerEvent(
                trigger_name=self.name,
                trigger_type="cron",
                task_text=self._prompt,
                agent_names=self._agent_names,
            )
        ]
