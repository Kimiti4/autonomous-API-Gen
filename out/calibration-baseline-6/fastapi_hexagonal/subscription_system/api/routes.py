from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response

from subscription_system.api.schemas import SubscriptionCreate, SubscriptionLedgerCreate
from subscription_system.application.services import SubscriptionService, SubscriptionLedgerService
from subscription_system.domain.models import Subscription, SubscriptionLedger


def build_subscription_router(service: SubscriptionService, auth_dependency) -> APIRouter:
    router = APIRouter(
        prefix="/subscriptions",
        tags=["subscriptions"],
        dependencies=[Depends(auth_dependency)],
    )

    @router.get("", response_model=List[Subscription])
    def list_subscription() -> List[Subscription]:
        return service.list()

    @router.post("", response_model=Subscription, status_code=201)
    def create_subscription(payload: SubscriptionCreate) -> Subscription:
        return service.create(**payload.model_dump())

    @router.get("/{subscription_id}", response_model=Subscription)
    def get_subscription(subscription_id: str) -> Subscription:
        entity = service.get(subscription_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return entity

    @router.delete("/{subscription_id}", status_code=204)
    def delete_subscription(subscription_id: str) -> Response:
        deleted = service.delete(subscription_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return Response(status_code=204)

    return router

def build_subscription_ledger_router(service: SubscriptionLedgerService, auth_dependency) -> APIRouter:
    router = APIRouter(
        prefix="/subscription_ledgers",
        tags=["subscription_ledgers"],
        dependencies=[Depends(auth_dependency)],
    )

    @router.get("", response_model=List[SubscriptionLedger])
    def list_subscription_ledger() -> List[SubscriptionLedger]:
        return service.list()

    @router.post("", response_model=SubscriptionLedger, status_code=201)
    def create_subscription_ledger(payload: SubscriptionLedgerCreate) -> SubscriptionLedger:
        return service.create(**payload.model_dump())

    @router.get("/{subscription_ledger_id}", response_model=SubscriptionLedger)
    def get_subscription_ledger(subscription_ledger_id: str) -> SubscriptionLedger:
        entity = service.get(subscription_ledger_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="SubscriptionLedger not found")
        return entity

    @router.delete("/{subscription_ledger_id}", status_code=204)
    def delete_subscription_ledger(subscription_ledger_id: str) -> Response:
        deleted = service.delete(subscription_ledger_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="SubscriptionLedger not found")
        return Response(status_code=204)

    return router
