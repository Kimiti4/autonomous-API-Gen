from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from reservation_system.domain.models import Reservation


class ReservationRepository(ABC):
    @abstractmethod
    def get(self, entity_id: str) -> Optional[Reservation]:
        ...

    @abstractmethod
    def list(self) -> List[Reservation]:
        ...

    @abstractmethod
    def add(self, entity: Reservation) -> Reservation:
        ...

    @abstractmethod
    def remove(self, entity_id: str) -> bool:
        ...
