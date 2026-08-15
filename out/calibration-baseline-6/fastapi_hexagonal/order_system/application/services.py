from __future__ import annotations

import uuid
from typing import List, Optional

from order_system.domain.models import Order
from order_system.domain.repositories import OrderRepository


class OrderService:
    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    def create(self, name: Optional[str] = None) -> Order:
        entity = Order(id=str(uuid.uuid4()), name=name)
        return self._repository.add(entity)

    def get(self, entity_id: str) -> Optional[Order]:
        return self._repository.get(entity_id)

    def list(self) -> List[Order]:
        return self._repository.list()

    def delete(self, entity_id: str) -> bool:
        return self._repository.remove(entity_id)
