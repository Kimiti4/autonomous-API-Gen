"""
API routes for Marketplace Production Hardening and Financial Governance.

Provides the provider-neutral financial control-plane surface described in
Phase 24.9 section 7. Real provider integrations are not implemented here.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel

from .engine import FinancialHardeningEngine
from .models import (
    MarketplaceFinancialPolicy,
    MarketplaceFinancialReadinessEvidence,
    PaymentWebhookEnvelope,
    TaxCalculationRequest,
)


router = APIRouter(
    prefix="/v1/marketplace/financial",
    tags=["marketplace-financial-hardening"],
)


class PaymentEventRequest(BaseModel):
    provider: str
    provider_event_id: str
    idempotency_key: Optional[str] = None
    signature: Optional[str] = None
    timestamp: Optional[str] = None
    payload: dict = {}


class RefundRequestRequest(BaseModel):
    marketplace_id: str
    order_id: str
    listing_id: str
    tenant_id: str
    amount: float
    currency: str = "USD"
    requested_by: str
    original_payment_event_id: Optional[str] = None
    reason_code: str = ""
    reason: str = ""
    idempotency_key: Optional[str] = None


class ApproveRefundRequest(BaseModel):
    approver_id: str
    approval_ref: Optional[str] = None


class RejectRefundRequest(BaseModel):
    approver_id: str
    reason: str = ""


class FraudAssessRequest(BaseModel):
    listing_id: str
    tenant_id: str
    order_id: Optional[str] = None
    context: dict = {}


class CertifyFinancialRequest(BaseModel):
    certified_by: str = "system"
    evidence: Optional[MarketplaceFinancialReadinessEvidence] = None
    prerequisite_26_8_report_id: Optional[str] = None


class RevokeFinancialRequest(BaseModel):
    reason: str
    revoked_by: str = "system"


def enable_marketplace_financial_hardening(
    app: FastAPI,
    policy: Optional[MarketplaceFinancialPolicy] = None,
    governance=None,
    production_learning_certification_engine=None,
) -> FinancialHardeningEngine:
    """Enable marketplace financial hardening endpoints."""

    engine = FinancialHardeningEngine(
        policy=policy,
        governance=governance,
        production_learning_certification_engine=(
            production_learning_certification_engine
        ),
    )

    app.state.marketplace_financial_hardening_engine = engine

    app.include_router(router)

    return engine


def _engine(request: Request) -> FinancialHardeningEngine:
    engine = getattr(
        request.app.state,
        "marketplace_financial_hardening_engine",
        None,
    )

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Marketplace financial hardening engine is not configured.",
        )

    return engine


@router.post("/payments/events", status_code=201)
def process_payment_event(payload: PaymentEventRequest, request: Request):
    engine = _engine(request)

    from datetime import datetime

    timestamp = payload.timestamp

    envelope = PaymentWebhookEnvelope(
        provider=payload.provider,
        provider_event_id=payload.provider_event_id,
        idempotency_key=payload.idempotency_key,
        signature=payload.signature,
        timestamp=datetime.fromisoformat(timestamp) if timestamp else None,
        payload=payload.payload,
    )

    try:
        event = engine.process_payment_webhook(envelope)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return event


@router.post("/refunds/request", status_code=201)
def request_refund(payload: RefundRequestRequest, request: Request):
    engine = _engine(request)

    try:
        refund = engine.request_refund(
            marketplace_id=payload.marketplace_id,
            order_id=payload.order_id,
            listing_id=payload.listing_id,
            tenant_id=payload.tenant_id,
            amount=payload.amount,
            currency=payload.currency,
            requested_by=payload.requested_by,
            original_payment_event_id=payload.original_payment_event_id,
            reason_code=payload.reason_code,
            reason=payload.reason,
            idempotency_key=payload.idempotency_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return refund


@router.post("/refunds/{refund_id}/approve")
def approve_refund(refund_id: str, payload: ApproveRefundRequest, request: Request):
    engine = _engine(request)

    try:
        return engine.approve_refund(
            refund_id=refund_id,
            approver_id=payload.approver_id,
            approval_ref=payload.approval_ref,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/refunds/{refund_id}/reject")
def reject_refund(refund_id: str, payload: RejectRefundRequest, request: Request):
    engine = _engine(request)

    try:
        return engine.reject_refund(
            refund_id=refund_id,
            approver_id=payload.approver_id,
            reason=payload.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/ledger/report")
def ledger_report(request: Request, marketplace_id: Optional[str] = None):
    engine = _engine(request)

    return engine.ledger.report(marketplace_id)


@router.post("/reconciliation/run", status_code=201)
def run_reconciliation(request: Request, marketplace_id: Optional[str] = None):
    engine = _engine(request)

    return engine.run_reconciliation(marketplace_id)


@router.get("/reconciliation/latest")
def latest_reconciliation(request: Request):
    engine = _engine(request)

    report = engine.latest_reconciliation_report()

    if not report:
        raise HTTPException(
            status_code=404,
            detail="No reconciliation report found.",
        )

    return report


@router.post("/tax/calculate")
def calculate_tax(payload: TaxCalculationRequest, request: Request):
    engine = _engine(request)

    return engine.calculate_tax(payload)


@router.post("/fraud/assess")
def assess_fraud(payload: FraudAssessRequest, request: Request):
    engine = _engine(request)

    return engine.assess_fraud(
        listing_id=payload.listing_id,
        tenant_id=payload.tenant_id,
        order_id=payload.order_id,
        context=payload.context,
    )


@router.get("/sla/report")
def sla_report(request: Request):
    engine = _engine(request)

    return engine.sla_report()


@router.post("/compliance/certify", status_code=201)
def certify_financial(payload: CertifyFinancialRequest, request: Request):
    engine = _engine(request)

    try:
        return engine.certify(
            certified_by=payload.certified_by,
            evidence=payload.evidence,
            prerequisite_26_8_report_id=payload.prerequisite_26_8_report_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/compliance/latest")
def latest_certification(request: Request):
    engine = _engine(request)

    report = engine.latest_certification_report()

    if not report:
        raise HTTPException(
            status_code=404,
            detail="No financial compliance certification report found.",
        )

    return report


@router.post("/compliance/report/{report_id}/revoke")
def revoke_certification(
    report_id: str,
    payload: RevokeFinancialRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.revoke_certification(
            report_id=report_id,
            reason=payload.reason,
            revoked_by=payload.revoked_by,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
