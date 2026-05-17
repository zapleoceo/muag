from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolResult:
    ok: bool
    data: str          # human-readable summary for LLM context
    raw: dict = field(default_factory=dict)


class BaseTool(ABC):
    name: str
    description: str

    @abstractmethod
    async def run(self, **kwargs) -> ToolResult:
        ...

    def schema(self) -> dict:
        """Return JSON-schema-like description for the orchestrator prompt."""
        return {"name": self.name, "description": self.description}
