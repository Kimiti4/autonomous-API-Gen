from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from notification_system.domain.models import Notification, NotificationLedger


class NotificationRepository(ABC):
    @abstractmethod
    def get(self, entity_id: str) -> Optional[Notification]:
        ...

    @abstractmethod
    def list(self) -> List[Notification]:
        ...

    @abstractmethod
    def add(self, entity: Notification) -> Notification:
        ...

    @abstractmethod
    def remove(self, entity_id: str) -> bool:
        ...

class NotificationLedgerRepository(ABC):
    @abstractmethod
    def get(self, entity_id: str) -> Optional[NotificationLedger]:
        ...

    @abstractmethod
    def list(self) -> List[NotificationLedger]:
        ...

    @abstractmethod
    def add(self, entity: NotificationLedger) -> NotificationLedger:
        ...

    @abstractmethod
    def remove(self, entity_id: str) -> bool:
        ...
