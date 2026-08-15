from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response

from notification_system.api.schemas import NotificationCreate, NotificationLedgerCreate
from notification_system.application.services import NotificationService, NotificationLedgerService
from notification_system.domain.models import Notification, NotificationLedger


def build_notification_router(service: NotificationService, auth_dependency) -> APIRouter:
    router = APIRouter(
        prefix="/notifications",
        tags=["notifications"],
        dependencies=[Depends(auth_dependency)],
    )

    @router.get("", response_model=List[Notification])
    def list_notification() -> List[Notification]:
        return service.list()

    @router.post("", response_model=Notification, status_code=201)
    def create_notification(payload: NotificationCreate) -> Notification:
        return service.create(**payload.model_dump())

    @router.get("/{notification_id}", response_model=Notification)
    def get_notification(notification_id: str) -> Notification:
        entity = service.get(notification_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Notification not found")
        return entity

    @router.delete("/{notification_id}", status_code=204)
    def delete_notification(notification_id: str) -> Response:
        deleted = service.delete(notification_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Notification not found")
        return Response(status_code=204)

    return router

def build_notification_ledger_router(service: NotificationLedgerService, auth_dependency) -> APIRouter:
    router = APIRouter(
        prefix="/notification_ledgers",
        tags=["notification_ledgers"],
        dependencies=[Depends(auth_dependency)],
    )

    @router.get("", response_model=List[NotificationLedger])
    def list_notification_ledger() -> List[NotificationLedger]:
        return service.list()

    @router.post("", response_model=NotificationLedger, status_code=201)
    def create_notification_ledger(payload: NotificationLedgerCreate) -> NotificationLedger:
        return service.create(**payload.model_dump())

    @router.get("/{notification_ledger_id}", response_model=NotificationLedger)
    def get_notification_ledger(notification_ledger_id: str) -> NotificationLedger:
        entity = service.get(notification_ledger_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="NotificationLedger not found")
        return entity

    @router.delete("/{notification_ledger_id}", status_code=204)
    def delete_notification_ledger(notification_ledger_id: str) -> Response:
        deleted = service.delete(notification_ledger_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="NotificationLedger not found")
        return Response(status_code=204)

    return router
