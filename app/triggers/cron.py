"""Cron trigger — fires tasks based on cron expression."""
import logging
from datetime import datetime, timezone

from app.triggers.base import BaseTrigger, TriggerEvent

log = logging.getLogger(__name__)


class CronTrigger(BaseTrigger):
    type = "cron"

    def __init__(self, name: str, config: dict, agent_names: list[str]) -> None:
        self.name = name
        self._prompt: str = config.get("prompt", "")
        self._cron_expr: str = config.get("cron_expr", "")
        self._agent_names: list[str] = agent_names
        self._last_fired: datetime | None = None

    async def poll(self) -> list[TriggerEvent]:
        if not self._prompt or not self._cron_expr:
            return []

        now = datetime.now(timezone.utc)
        if not self._should_fire(now):
            return []

        self._last_fired = now
        log.info("CronTrigger '%s' fired", self.name)
        return [
            TriggerEvent(
                trigger_name=self.name,
                trigger_type="cron",
                task_text=self._prompt,
                raw_data={"fired_at": now.isoformat()},
                agent_names=self._agent_names,
            )
        ]

    def _should_fire(self, now: datetime) -> bool:
        """Check if the cron expression matches the current minute."""
        if self._last_fired is None:
            # First run — fire immediately if expression is valid
            return _is_valid_cron(self._cron_expr)

        elapsed_minutes = (now - self._last_fired).total_seconds() / 60
        interval = _cron_to_interval_minutes(self._cron_expr)
        return elapsed_minutes >= interval


def _is_valid_cron(expr: str) -> bool:
    parts = expr.strip().split()
    return len(parts) == 5


def _cron_to_interval_minutes(expr: str) -> float:
    """
    Parse simple cron expressions to a polling interval in minutes.
    Supports:
      */N * * * *  →  every N minutes
      0 */H * * *  →  every H hours
      0 H * * *    →  daily at hour H (24h interval)
    Falls back to 60 minutes for anything else.
    """
    parts = expr.strip().split()
    if len(parts) != 5:
        return 60.0

    minute, hour = parts[0], parts[1]

    # */N * * * *  →  every N minutes
    if minute.startswith("*/") and hour == "*":
        try:
            return float(minute[2:])
        except ValueError:
            pass

    # 0 */H * * *  →  every H hours
    if minute == "0" and hour.startswith("*/"):
        try:
            return float(hour[2:]) * 60
        except ValueError:
            pass

    # 0 H * * *  →  once a day
    if minute == "0" and hour.isdigit():
        return 24 * 60

    return 60.0
