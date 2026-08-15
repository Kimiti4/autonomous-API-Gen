from __future__ import annotations

from typing import Dict, List, Optional

from inventory_system.domain.models import Inventory
from inventory_system.domain.repositories import InventoryRepository


class InMemoryInventoryRepository(InventoryRepository):
    def __init__(self) -> None:
        self._store: Dict[str, Inventory] = {}

    def get(self, entity_id: str) -> Optional[Inventory]:
        return self._store.get(entity_id)

    def list(self) -> List[Inventory]:
        return list(self._store.values())

    def add(self, entity: Inventory) -> Inventory:
        self._store[entity.id] = entity
        return entity

    def remove(self, entity_id: str) -> bool:
        return self._store.pop(entity_id, None) is not None
