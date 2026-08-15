from __future__ import annotations

from typing import Dict, List, Optional

from notification_system.domain.models import Notification, NotificationLedger
from notification_system.domain.repositories import NotificationRepository, NotificationLedgerRepository


class InMemoryNotificationRepository(NotificationRepository):
    def __init__(self) -> None:
        self._store: Dict[str, Notification] = {}

    def get(self, entity_id: str) -> Optional[Notification]:
        return self._store.get(entity_id)

    def list(self) -> List[Notification]:
        return list(self._store.values())

    def add(self, entity: Notification) -> Notification:
        self._store[entity.id] = entity
        return entity

    def remove(self, entity_id: str) -> bool:
        return self._store.pop(entity_id, None) is not None

class InMemoryNotificationLedgerRepository(NotificationLedgerRepository):
    def __init__(self) -> None:
        self._store: Dict[str, NotificationLedger] = {}

    def get(self, entity_id: str) -> Optional[NotificationLedger]:
        return self._store.get(entity_id)

    def list(self) -> List[NotificationLedger]:
        return list(self._store.values())

    def add(self, entity: NotificationLedger) -> NotificationLedger:
        self._store[entity.id] = entity
        return entity

    def remove(self, entity_id: str) -> bool:
        return self._store.pop(entity_id, None) is not None
