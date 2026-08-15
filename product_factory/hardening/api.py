"""
API routes for Phase 24 hardening.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel

from .compilation import CompilationExecutor, CompilationTarget
from .governance import ProductGovernanceEngine, ProductGovernancePolicy
from .learning import CustomerLearningEngine
from .market_evidence import MarketEvidenceEngine
from .models import (
    BillingEvent,
    CustomerSignal,
    MarketEvidence,
    MarketEvidenceSource,
    ProductAction,
    ProductEvidenceContext,
)
from .monetization import MonetizationOpsEngine


router = APIRouter(
    prefix="/v1/product-factory/hardening",
    tags=["product-factory-hardening"],
)


class EvaluateGovernanceRequest(BaseModel):
    product_id: str
    action: ProductAction
    context: ProductEvidenceContext


class SubmitApprovalRequest(BaseModel):
    product_id: str
    action: ProductAction
    requested_by: str
    evidence_refs: List[str] = []


class DecideApprovalRequest(BaseModel):
    decided_by: str
    approved: bool
    comments: str = ""


class ExecuteCompilationRequest(BaseModel):
    product_id: str
    isr: Dict[str, Any]
    targets: Optional[List[CompilationTarget]] = None
    environment: str = "development"


class IngestSignalsRequest(BaseModel):
    signals: List[CustomerSignal] = []


class ValidatePlanRequest(BaseModel):
    plan: Dict[str, Any]


class ValidatePriceChangeRequest(BaseModel):
    old_plan: Dict[str, Any]
    new_plan: Dict[str, Any]


class IngestBillingEventsRequest(BaseModel):
    events: List[BillingEvent] = []


def enable_product_hardening(app: FastAPI) -> None:
    app.state.product_governance_engine = ProductGovernanceEngine(
        ProductGovernancePolicy()
    )
    app.state.market_evidence_engine = MarketEvidenceEngine()
    app.state.compilation_executor = CompilationExecutor()
    app.state.customer_learning_engine = CustomerLearningEngine()
    app.state.monetization_engine = MonetizationOpsEngine()

    app.include_router(router)


def _governance(request: Request) -> ProductGovernanceEngine:
    return request.app.state.product_governance_engine


def _market(request: Request) -> MarketEvidenceEngine:
    return request.app.state.market_evidence_engine


def _compilation(request: Request) -> CompilationExecutor:
    return request.app.state.compilation_executor


def _learning(request: Request) -> CustomerLearningEngine:
    return request.app.state.customer_learning_engine


def _monetization(request: Request) -> MonetizationOpsEngine:
    return request.app.state.monetization_engine


@router.post("/governance/evaluate")
def evaluate_governance(
    payload: EvaluateGovernanceRequest,
    request: Request,
):
    engine = _governance(request)

    return engine.evaluate_action(
        product_id=payload.product_id,
        action=payload.action,
        context=payload.context,
    )


@router.post("/governance/approvals", status_code=201)
def submit_approval(payload: SubmitApprovalRequest, request: Request):
    engine = _governance(request)

    return engine.submit_approval(
        product_id=payload.product_id,
        action=payload.action,
        requested_by=payload.requested_by,
        evidence_refs=payload.evidence_refs,
    )


@router.post("/governance/approvals/{approval_id}/decide")
def decide_approval(
    approval_id: str,
    payload: DecideApprovalRequest,
    request: Request,
):
    engine = _governance(request)

    try:
        return engine.decide_approval(
            approval_id=approval_id,
            decided_by=payload.decided_by,
            approved=payload.approved,
            comments=payload.comments,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/market-evidence/sources", status_code=201)
def register_market_source(
    payload: MarketEvidenceSource,
    request: Request,
):
    engine = _market(request)
    return engine.register_source(payload)


@router.post("/market-evidence", status_code=201)
def ingest_market_evidence(payload: MarketEvidence, request: Request):
    engine = _market(request)
    return engine.ingest_evidence(payload)


@router.get("/market-evidence/{product_id}/report")
def market_evidence_report(product_id: str, request: Request):
    engine = _market(request)
    return engine.report(product_id)


@router.post("/compilation/execute")
def execute_compilation(payload: ExecuteCompilationRequest, request: Request):
    engine = _compilation(request)

    return engine.execute(
        product_id=payload.product_id,
        isr=payload.isr,
        targets=payload.targets,
        environment=payload.environment,
    )


@router.post("/learning/signals", status_code=201)
def ingest_learning_signals(payload: IngestSignalsRequest, request: Request):
    engine = _learning(request)

    count = engine.ingest(payload.signals)

    return {
        "ingested_signals": count,
    }


@router.get("/learning/{product_id}/fitness")
def product_fitness(product_id: str, request: Request):
    engine = _learning(request)
    return engine.product_fitness(product_id)


@router.get("/learning/{product_id}/evolution-feedback")
def evolution_feedback(product_id: str, request: Request):
    engine = _learning(request)
    return engine.evolution_feedback(product_id)


@router.post("/monetization/validate-plan")
def validate_pricing_plan(payload: ValidatePlanRequest, request: Request):
    engine = _monetization(request)
    return engine.validate_pricing_plan(payload.plan)


@router.post("/monetization/validate-price-change")
def validate_price_change(
    payload: ValidatePriceChangeRequest,
    request: Request,
):
    engine = _monetization(request)

    return engine.validate_price_change(
        old_plan=payload.old_plan,
        new_plan=payload.new_plan,
    )


@router.post("/monetization/billing-events", status_code=201)
def ingest_billing_events(
    payload: IngestBillingEventsRequest,
    request: Request,
):
    engine = _monetization(request)

    count = engine.ingest_billing_events(payload.events)

    return {
        "ingested_events": count,
    }


@router.get("/monetization/{product_id}/report")
def revenue_ops_report(product_id: str, request: Request):
    engine = _monetization(request)
    return engine.revenue_ops_report(product_id)
