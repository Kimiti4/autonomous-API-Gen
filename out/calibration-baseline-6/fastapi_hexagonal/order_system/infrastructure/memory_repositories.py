from __future__ import annotations

from typing import Dict, List, Optional

from order_system.domain.models import Order
from order_system.domain.repositories import OrderRepository


class InMemoryOrderRepository(OrderRepository):
    def __init__(self) -> None:
        self._store: Dict[str, Order] = {}

    def get(self, entity_id: str) -> Optional[Order]:
        return self._store.get(entity_id)

    def list(self) -> List[Order]:
        return list(self._store.values())

    def add(self, entity: Order) -> Order:
        self._store[entity.id] = entity
        return entity

    def remove(self, entity_id: str) -> bool:
        return self._store.pop(entity_id, None) is not None
