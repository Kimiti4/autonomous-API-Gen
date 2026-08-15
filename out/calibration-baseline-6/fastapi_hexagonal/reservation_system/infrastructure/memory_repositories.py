from __future__ import annotations

from typing import Dict, List, Optional

from reservation_system.domain.models import Reservation
from reservation_system.domain.repositories import ReservationRepository


class InMemoryReservationRepository(ReservationRepository):
    def __init__(self) -> None:
        self._store: Dict[str, Reservation] = {}

    def get(self, entity_id: str) -> Optional[Reservation]:
        return self._store.get(entity_id)

    def list(self) -> List[Reservation]:
        return list(self._store.values())

    def add(self, entity: Reservation) -> Reservation:
        self._store[entity.id] = entity
        return entity

    def remove(self, entity_id: str) -> bool:
        return self._store.pop(entity_id, None) is not None
