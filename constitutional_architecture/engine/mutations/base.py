from abc import ABC, abstractmethod
from typing import Any

from constitutional_architecture.isr.model.isr import ISR


class MutationOperator(ABC):
    @property
    @abstractmethod
    def identifier(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @abstractmethod
    def apply(self, isr: ISR, target_id: str, params: dict[str, Any] | None = None) -> ISR:
        ...
