from __future__ import annotations

import uuid
from typing import List, Optional

from reservation_system.domain.models import Reservation
from reservation_system.domain.repositories import ReservationRepository


class ReservationService:
    def __init__(self, repository: ReservationRepository) -> None:
        self._repository = repository

    def create(self, name: str, quantity: Optional[int] = None) -> Reservation:
        entity = Reservation(id=str(uuid.uuid4()), name=name, quantity=quantity)
        return self._repository.add(entity)

    def get(self, entity_id: str) -> Optional[Reservation]:
        return self._repository.get(entity_id)

    def list(self) -> List[Reservation]:
        return self._repository.list()

    def delete(self, entity_id: str) -> bool:
        return self._repository.remove(entity_id)
