from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from order_system.domain.models import Order


class OrderRepository(ABC):
    @abstractmethod
    def get(self, entity_id: str) -> Optional[Order]:
        ...

    @abstractmethod
    def list(self) -> List[Order]:
        ...

    @abstractmethod
    def add(self, entity: Order) -> Order:
        ...

    @abstractmethod
    def remove(self, entity_id: str) -> bool:
        ...
