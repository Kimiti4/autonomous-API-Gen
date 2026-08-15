from __future__ import annotations

import uuid
from typing import List, Optional

from notification_system.domain.models import Notification, NotificationLedger
from notification_system.domain.repositories import NotificationRepository, NotificationLedgerRepository


class NotificationService:
    def __init__(self, repository: NotificationRepository) -> None:
        self._repository = repository

    def create(self, quantity: int, name: Optional[str] = None, price: Optional[float] = None) -> Notification:
        entity = Notification(id=str(uuid.uuid4()), quantity=quantity, name=name, price=price)
        return self._repository.add(entity)

    def get(self, entity_id: str) -> Optional[Notification]:
        return self._repository.get(entity_id)

    def list(self) -> List[Notification]:
        return self._repository.list()

    def delete(self, entity_id: str) -> bool:
        return self._repository.remove(entity_id)

class NotificationLedgerService:
    def __init__(self, repository: NotificationLedgerRepository) -> None:
        self._repository = repository

    def create(self, reference_id: str) -> NotificationLedger:
        entity = NotificationLedger(id=str(uuid.uuid4()), reference_id=reference_id)
        return self._repository.add(entity)

    def get(self, entity_id: str) -> Optional[NotificationLedger]:
        return self._repository.get(entity_id)

    def list(self) -> List[NotificationLedger]:
        return self._repository.list()

    def delete(self, entity_id: str) -> bool:
        return self._repository.remove(entity_id)
