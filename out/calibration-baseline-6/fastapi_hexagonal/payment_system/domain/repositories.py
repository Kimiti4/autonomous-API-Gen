from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from payment_system.domain.models import Payment, PaymentLedger


class PaymentRepository(ABC):
    @abstractmethod
    def get(self, entity_id: str) -> Optional[Payment]:
        ...

    @abstractmethod
    def list(self) -> List[Payment]:
        ...

    @abstractmethod
    def add(self, entity: Payment) -> Payment:
        ...

    @abstractmethod
    def remove(self, entity_id: str) -> bool:
        ...

class PaymentLedgerRepository(ABC):
    @abstractmethod
    def get(self, entity_id: str) -> Optional[PaymentLedger]:
        ...

    @abstractmethod
    def list(self) -> List[PaymentLedger]:
        ...

    @abstractmethod
    def add(self, entity: PaymentLedger) -> PaymentLedger:
        ...

    @abstractmethod
    def remove(self, entity_id: str) -> bool:
        ...
