from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMMessage:
    role: str    # system | user | assistant
    content: str


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, messages: list[LLMMessage]) -> str | None:
        ...
