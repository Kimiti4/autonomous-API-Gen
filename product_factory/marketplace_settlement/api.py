"""
API routes for marketplace financial reconciliation and settlement.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel

from .engine import MarketplaceSettlementEngine
from .gateway import GovernanceGateway, SettlementAdapter
from .models import FinancialEvent, SettlementPolicy


router = APIRouter(
    prefix="/v1/marketplace/settlement",
    tags=["marketplace-settlement"],
)


class RunReconciliationRequest(BaseModel):
    marketplace_id: str
    period_start: datetime
    period_end: datetime


class ResolveMismatchRequest(BaseModel):
    actor_id: str
    notes: str = ""


class CreateSettlementBatchRequest(BaseModel):
    marketplace_id: str
    tenant_id: str
    currency: str
    period_start: datetime
    period_end: datetime
    actor_id: str


class ApproveSettlementRequest(BaseModel):
    actor_id: str
    approval_ref: Optional[str] = None


class ExecuteSettlementRequest(BaseModel):
    actor_id: str


def enable_marketplace_settlement(
    app: FastAPI,
    governance_gateway: GovernanceGateway | None = None,
    settlement_adapter: SettlementAdapter | None = None,
    policy: SettlementPolicy | None = None,
) -> MarketplaceSettlementEngine:
    """Enable marketplace settlement endpoints."""

    engine = MarketplaceSettlementEngine(
        governance_gateway=governance_gateway,
        settlement_adapter=settlement_adapter,
        policy=policy,
    )

    app.state.marketplace_settlement_engine = engine

    app.include_router(router)

    return engine


def _engine(request: Request) -> MarketplaceSettlementEngine:
    engine = getattr(request.app.state, "marketplace_settlement_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Marketplace settlement engine is not configured.",
        )

    return engine


@router.post("/events", status_code=201)
def ingest_event(payload: FinancialEvent, request: Request):
    engine = _engine(request)

    entry = engine.ledger.ingest_event(payload)

    if entry is None:
        return {
            "status": "duplicate_event",
            "idempotency_key": payload.idempotency_key,
        }

    return entry


@router.post("/reconciliation/run")
def run_reconciliation(payload: RunReconciliationRequest, request: Request):
    engine = _engine(request)

    return engine.reconciliation.run(
        marketplace_id=payload.marketplace_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
    )


@router.post("/reconciliation/mismatches/{mismatch_id}/resolve")
def resolve_mismatch(
    mismatch_id: str,
    payload: ResolveMismatchRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.reconciliation.resolve_mismatch(
            mismatch_id=mismatch_id,
            actor_id=payload.actor_id,
            notes=payload.notes,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/batches", status_code=201)
def create_settlement_batch(payload: CreateSettlementBatchRequest, request: Request):
    engine = _engine(request)

    try:
        return engine.settlement.create_batch(
            marketplace_id=payload.marketplace_id,
            tenant_id=payload.tenant_id,
            currency=payload.currency,
            period_start=payload.period_start,
            period_end=payload.period_end,
            actor_id=payload.actor_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/batches/{batch_id}/approve")
def approve_settlement(
    batch_id: str,
    payload: ApproveSettlementRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.settlement.approve_settlement(
            batch_id=batch_id,
            actor_id=payload.actor_id,
            approval_ref=payload.approval_ref,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/batches/{batch_id}/execute")
def execute_settlement(
    batch_id: str,
    payload: ExecuteSettlementRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.settlement.execute_settlement(
            batch_id=batch_id,
            actor_id=payload.actor_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/balances/{marketplace_id}/{tenant_id}/{currency}")
def get_balance(
    marketplace_id: str,
    tenant_id: str,
    currency: str,
    request: Request,
):
    engine = _engine(request)

    return {
        "marketplace_id": marketplace_id,
        "tenant_id": tenant_id,
        "currency": currency,
        "balance": engine.ledger.balance(
            marketplace_id=marketplace_id,
            tenant_id=tenant_id,
            currency=currency,
        ),
    }


@router.get("/report")
def settlement_report(request: Request):
    engine = _engine(request)

    return engine.report()
