from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from inventory_system.domain.models import Inventory


class InventoryRepository(ABC):
    @abstractmethod
    def get(self, entity_id: str) -> Optional[Inventory]:
        ...

    @abstractmethod
    def list(self) -> List[Inventory]:
        ...

    @abstractmethod
    def add(self, entity: Inventory) -> Inventory:
        ...

    @abstractmethod
    def remove(self, entity_id: str) -> bool:
        ...
