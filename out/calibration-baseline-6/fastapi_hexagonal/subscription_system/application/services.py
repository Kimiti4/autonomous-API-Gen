from __future__ import annotations

import uuid
from typing import List, Optional

from subscription_system.domain.models import Subscription, SubscriptionLedger
from subscription_system.domain.repositories import SubscriptionRepository, SubscriptionLedgerRepository


class SubscriptionService:
    def __init__(self, repository: SubscriptionRepository) -> None:
        self._repository = repository

    def create(self, name: Optional[str] = None) -> Subscription:
        entity = Subscription(id=str(uuid.uuid4()), name=name)
        return self._repository.add(entity)

    def get(self, entity_id: str) -> Optional[Subscription]:
        return self._repository.get(entity_id)

    def list(self) -> List[Subscription]:
        return self._repository.list()

    def delete(self, entity_id: str) -> bool:
        return self._repository.remove(entity_id)

class SubscriptionLedgerService:
    def __init__(self, repository: SubscriptionLedgerRepository) -> None:
        self._repository = repository

    def create(self, reference_id: str) -> SubscriptionLedger:
        entity = SubscriptionLedger(id=str(uuid.uuid4()), reference_id=reference_id)
        return self._repository.add(entity)

    def get(self, entity_id: str) -> Optional[SubscriptionLedger]:
        return self._repository.get(entity_id)

    def list(self) -> List[SubscriptionLedger]:
        return self._repository.list()

    def delete(self, entity_id: str) -> bool:
        return self._repository.remove(entity_id)
