from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from subscription_system.domain.models import Subscription, SubscriptionLedger


class SubscriptionRepository(ABC):
    @abstractmethod
    def get(self, entity_id: str) -> Optional[Subscription]:
        ...

    @abstractmethod
    def list(self) -> List[Subscription]:
        ...

    @abstractmethod
    def add(self, entity: Subscription) -> Subscription:
        ...

    @abstractmethod
    def remove(self, entity_id: str) -> bool:
        ...

class SubscriptionLedgerRepository(ABC):
    @abstractmethod
    def get(self, entity_id: str) -> Optional[SubscriptionLedger]:
        ...

    @abstractmethod
    def list(self) -> List[SubscriptionLedger]:
        ...

    @abstractmethod
    def add(self, entity: SubscriptionLedger) -> SubscriptionLedger:
        ...

    @abstractmethod
    def remove(self, entity_id: str) -> bool:
        ...
