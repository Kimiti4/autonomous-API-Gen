from __future__ import annotations

from typing import Dict, List, Optional

from subscription_system.domain.models import Subscription, SubscriptionLedger
from subscription_system.domain.repositories import SubscriptionRepository, SubscriptionLedgerRepository


class InMemorySubscriptionRepository(SubscriptionRepository):
    def __init__(self) -> None:
        self._store: Dict[str, Subscription] = {}

    def get(self, entity_id: str) -> Optional[Subscription]:
        return self._store.get(entity_id)

    def list(self) -> List[Subscription]:
        return list(self._store.values())

    def add(self, entity: Subscription) -> Subscription:
        self._store[entity.id] = entity
        return entity

    def remove(self, entity_id: str) -> bool:
        return self._store.pop(entity_id, None) is not None

class InMemorySubscriptionLedgerRepository(SubscriptionLedgerRepository):
    def __init__(self) -> None:
        self._store: Dict[str, SubscriptionLedger] = {}

    def get(self, entity_id: str) -> Optional[SubscriptionLedger]:
        return self._store.get(entity_id)

    def list(self) -> List[SubscriptionLedger]:
        return list(self._store.values())

    def add(self, entity: SubscriptionLedger) -> SubscriptionLedger:
        self._store[entity.id] = entity
        return entity

    def remove(self, entity_id: str) -> bool:
        return self._store.pop(entity_id, None) is not None
