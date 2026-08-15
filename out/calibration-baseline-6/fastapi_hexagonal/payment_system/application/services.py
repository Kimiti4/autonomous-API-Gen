from __future__ import annotations

import uuid
from typing import List, Optional

from payment_system.domain.models import Payment, PaymentLedger
from payment_system.domain.repositories import PaymentRepository, PaymentLedgerRepository


class PaymentService:
    def __init__(self, repository: PaymentRepository) -> None:
        self._repository = repository

    def create(self, owner_id: str, name: str, price: float, occurred_at: datetime, status: Literal['active', 'pending', 'closed'], attachment: bytes, payload: Optional[dict] = None, active: Optional[bool] = None, quantity: Optional[int] = None) -> Payment:
        entity = Payment(id=str(uuid.uuid4()), owner_id=owner_id, name=name, price=price, occurred_at=occurred_at, status=status, attachment=attachment, payload=payload, active=active, quantity=quantity)
        return self._repository.add(entity)

    def get(self, entity_id: str) -> Optional[Payment]:
        return self._repository.get(entity_id)

    def list(self) -> List[Payment]:
        return self._repository.list()

    def delete(self, entity_id: str) -> bool:
        return self._repository.remove(entity_id)

class PaymentLedgerService:
    def __init__(self, repository: PaymentLedgerRepository) -> None:
        self._repository = repository

    def create(self, reference_id: str) -> PaymentLedger:
        entity = PaymentLedger(id=str(uuid.uuid4()), reference_id=reference_id)
        return self._repository.add(entity)

    def get(self, entity_id: str) -> Optional[PaymentLedger]:
        return self._repository.get(entity_id)

    def list(self) -> List[PaymentLedger]:
        return self._repository.list()

    def delete(self, entity_id: str) -> bool:
        return self._repository.remove(entity_id)
