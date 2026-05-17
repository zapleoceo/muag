from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class TriggerEvent:
    trigger_name: str
    trigger_type: str
    task_text: str
    raw_data: dict = field(default_factory=dict)
    agent_names: list[str] = field(default_factory=list)
    topic_thread_id: int | None = None


class BaseTrigger(ABC):
    name: str
    type: str

    @abstractmethod
    async def poll(self) -> list[TriggerEvent]:
        """Return new events since last poll. Must be idempotent."""
        ...
