from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AgentResponse:
    text: str
    score: float = 1.0          # quality score assigned by reflection (0.0–1.0)
    tool_calls: list[dict] = field(default_factory=list)
    retries: int = 0


class BaseAgent(ABC):
    name: str
    role: str   # knowledge | action | process

    @abstractmethod
    async def handle(self, request: str, context: str = "") -> AgentResponse:
        ...
