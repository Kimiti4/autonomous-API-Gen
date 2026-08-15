from __future__ import annotations

from typing import Dict, List, Optional

from payment_system.domain.models import Payment, PaymentLedger
from payment_system.domain.repositories import PaymentRepository, PaymentLedgerRepository


class InMemoryPaymentRepository(PaymentRepository):
    def __init__(self) -> None:
        self._store: Dict[str, Payment] = {}

    def get(self, entity_id: str) -> Optional[Payment]:
        return self._store.get(entity_id)

    def list(self) -> List[Payment]:
        return list(self._store.values())

    def add(self, entity: Payment) -> Payment:
        self._store[entity.id] = entity
        return entity

    def remove(self, entity_id: str) -> bool:
        return self._store.pop(entity_id, None) is not None

class InMemoryPaymentLedgerRepository(PaymentLedgerRepository):
    def __init__(self) -> None:
        self._store: Dict[str, PaymentLedger] = {}

    def get(self, entity_id: str) -> Optional[PaymentLedger]:
        return self._store.get(entity_id)

    def list(self) -> List[PaymentLedger]:
        return list(self._store.values())

    def add(self, entity: PaymentLedger) -> PaymentLedger:
        self._store[entity.id] = entity
        return entity

    def remove(self, entity_id: str) -> bool:
        return self._store.pop(entity_id, None) is not None
