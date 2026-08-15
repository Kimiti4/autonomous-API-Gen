from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response

from payment_system.api.schemas import PaymentCreate, PaymentLedgerCreate
from payment_system.application.services import PaymentService, PaymentLedgerService
from payment_system.domain.models import Payment, PaymentLedger


def build_payment_router(service: PaymentService, auth_dependency) -> APIRouter:
    router = APIRouter(
        prefix="/payments",
        tags=["payments"],
        dependencies=[Depends(auth_dependency)],
    )

    @router.get("", response_model=List[Payment])
    def list_payment() -> List[Payment]:
        return service.list()

    @router.post("", response_model=Payment, status_code=201)
    def create_payment(payload: PaymentCreate) -> Payment:
        return service.create(**payload.model_dump())

    @router.get("/{payment_id}", response_model=Payment)
    def get_payment(payment_id: str) -> Payment:
        entity = service.get(payment_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Payment not found")
        return entity

    @router.delete("/{payment_id}", status_code=204)
    def delete_payment(payment_id: str) -> Response:
        deleted = service.delete(payment_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Payment not found")
        return Response(status_code=204)

    return router

def build_payment_ledger_router(service: PaymentLedgerService, auth_dependency) -> APIRouter:
    router = APIRouter(
        prefix="/payment_ledgers",
        tags=["payment_ledgers"],
        dependencies=[Depends(auth_dependency)],
    )

    @router.get("", response_model=List[PaymentLedger])
    def list_payment_ledger() -> List[PaymentLedger]:
        return service.list()

    @router.post("", response_model=PaymentLedger, status_code=201)
    def create_payment_ledger(payload: PaymentLedgerCreate) -> PaymentLedger:
        return service.create(**payload.model_dump())

    @router.get("/{payment_ledger_id}", response_model=PaymentLedger)
    def get_payment_ledger(payment_ledger_id: str) -> PaymentLedger:
        entity = service.get(payment_ledger_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="PaymentLedger not found")
        return entity

    @router.delete("/{payment_ledger_id}", status_code=204)
    def delete_payment_ledger(payment_ledger_id: str) -> Response:
        deleted = service.delete(payment_ledger_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="PaymentLedger not found")
        return Response(status_code=204)

    return router
