from __future__ import annotations

import uuid
from typing import List, Optional

from inventory_system.domain.models import Inventory
from inventory_system.domain.repositories import InventoryRepository


class InventoryService:
    def __init__(self, repository: InventoryRepository) -> None:
        self._repository = repository

    def create(self, name: str, quantity: Optional[int] = None) -> Inventory:
        entity = Inventory(id=str(uuid.uuid4()), name=name, quantity=quantity)
        return self._repository.add(entity)

    def get(self, entity_id: str) -> Optional[Inventory]:
        return self._repository.get(entity_id)

    def list(self) -> List[Inventory]:
        return self._repository.list()

    def delete(self, entity_id: str) -> bool:
        return self._repository.remove(entity_id)
