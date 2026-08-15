"""
API routes for autonomous ecosystem and federation.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .engine import EcosystemEngine
from .gateway import GovernanceGateway
from .models import (
    PartnerType,
    RoutingRequest,
    SLADefinition,
    SLAOperator,
)


router = APIRouter(
    prefix="/v1/ecosystem",
    tags=["autonomous-ecosystem"],
)


class CreateTreatyRequest(BaseModel):
    name: str
    source_marketplace_id: str
    target_marketplace_id: str
    revenue_share_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    routing_policy: dict = Field(default_factory=dict)


class ActivateTreatyRequest(BaseModel):
    actor_id: str
    approval_ref: Optional[str] = None


class CreatePartnerRequest(BaseModel):
    name: str
    partner_type: PartnerType = PartnerType.VENDOR
    capabilities: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)


class ActivatePartnerRequest(BaseModel):
    actor_id: str


class AdjustTrustRequest(BaseModel):
    delta: float
    reason: str


class CreateContractRequest(BaseModel):
    partner_id: str
    marketplace_id: str
    contract_type: str
    terms: dict = Field(default_factory=dict)


class AddSLARequest(BaseModel):
    metric: str
    threshold: float
    operator: SLAOperator
    window_minutes: int = Field(default=60, ge=1)


class IngestMetricRequest(BaseModel):
    metric: str
    value: float


class SuspendTreatyRequest(BaseModel):
    reason: str
    actor_id: str
    evidence_refs: Optional[List[str]] = None


class UpdateRoutingPolicyRequest(BaseModel):
    routing_policy: dict
    actor_id: str
    evidence_refs: Optional[List[str]] = None


class EnforcePenaltyRequest(BaseModel):
    breach_id: str
    penalty_amount: float = 0.0
    actor_id: str
    evidence_refs: Optional[List[str]] = None


class SubmitApprovalRequest(BaseModel):
    actor: str = "ecosystem"
    comments: Optional[str] = None


def enable_ecosystem(
    app: FastAPI,
    governance_gateway: GovernanceGateway | None = None,
) -> EcosystemEngine:
    """Enable ecosystem endpoints."""

    engine = EcosystemEngine(governance_gateway=governance_gateway)

    app.state.ecosystem_engine = engine

    app.include_router(router)

    return engine


def _engine(request: Request) -> EcosystemEngine:
    engine = getattr(request.app.state, "ecosystem_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Ecosystem engine is not configured.",
        )

    return engine


@router.post("/federations/treaties", status_code=201)
def create_treaty(payload: CreateTreatyRequest, request: Request):
    engine = _engine(request)

    return engine.federation.create_treaty(
        name=payload.name,
        source_marketplace_id=payload.source_marketplace_id,
        target_marketplace_id=payload.target_marketplace_id,
        revenue_share_pct=payload.revenue_share_pct,
        routing_policy=payload.routing_policy,
    )


@router.post("/federations/treaties/{treaty_id}/activate")
def activate_treaty(
    treaty_id: str,
    payload: ActivateTreatyRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.federation.activate_treaty(
            treaty_id=treaty_id,
            actor_id=payload.actor_id,
            approval_ref=payload.approval_ref,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/partners", status_code=201)
def create_partner(payload: CreatePartnerRequest, request: Request):
    engine = _engine(request)

    return engine.partners.register_partner(
        name=payload.name,
        partner_type=payload.partner_type,
        capabilities=payload.capabilities,
        evidence_refs=payload.evidence_refs,
    )


@router.post("/partners/{partner_id}/activate")
def activate_partner(
    partner_id: str,
    payload: ActivatePartnerRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.partners.activate_partner(
            partner_id=partner_id,
            actor_id=payload.actor_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/partners/{partner_id}/trust")
def adjust_trust(
    partner_id: str,
    payload: AdjustTrustRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.partners.adjust_trust(
            partner_id=partner_id,
            delta=payload.delta,
            reason=payload.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/routing/evaluate")
def evaluate_routing(payload: RoutingRequest, request: Request):
    engine = _engine(request)

    try:
        return engine.routing.evaluate(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/contracts", status_code=201)
def create_contract(payload: CreateContractRequest, request: Request):
    engine = _engine(request)

    return engine.contracts.create_contract(
        partner_id=payload.partner_id,
        marketplace_id=payload.marketplace_id,
        contract_type=payload.contract_type,
        terms=payload.terms,
    )


@router.post("/contracts/{contract_id}/sla", status_code=201)
def add_sla(contract_id: str, payload: AddSLARequest, request: Request):
    engine = _engine(request)

    try:
        return engine.contracts.add_sla(
            contract_id=contract_id,
            sla=SLADefinition(
                metric=payload.metric,
                threshold=payload.threshold,
                operator=payload.operator,
                window_minutes=payload.window_minutes,
            ),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/contracts/{contract_id}/metrics")
def ingest_metric(
    contract_id: str,
    payload: IngestMetricRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        breach = engine.contracts.ingest_metric(
            contract_id=contract_id,
            metric=payload.metric,
            value=payload.value,
        )

        return {
            "breach": breach,
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sync")
def sync_ecosystem(request: Request):
    engine = _engine(request)

    return {
        "synced_records": engine.sync_all(),
    }


@router.get("/report")
def ecosystem_report(request: Request):
    engine = _engine(request)

    return engine.report()


@router.post("/federations/treaties/{treaty_id}/suspend")
def suspend_treaty(
    treaty_id: str,
    payload: SuspendTreatyRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.suspend_treaty(
            treaty_id=treaty_id,
            reason=payload.reason,
            actor_id=payload.actor_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/federations/treaties/{treaty_id}/routing-policy")
def update_routing_policy(
    treaty_id: str,
    payload: UpdateRoutingPolicyRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.update_routing_policy(
            treaty_id=treaty_id,
            routing_policy=payload.routing_policy,
            actor_id=payload.actor_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/contracts/{contract_id}/enforce-penalty")
def enforce_penalty(
    contract_id: str,
    payload: EnforcePenaltyRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.enforce_penalty(
            contract_id=contract_id,
            breach_id=payload.breach_id,
            penalty_amount=payload.penalty_amount,
            actor_id=payload.actor_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/approvals/{approval_id}/submit")
def submit_approval(
    approval_id: str,
    payload: SubmitApprovalRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        status = engine.submit_approval(
            approval_id=approval_id,
            actor=payload.actor,
            comments=payload.comments,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return {"status": status}


@router.get("/approvals/{action}/pending")
def list_pending_approvals(action: str, request: Request):
    engine = _engine(request)

    return {"approval_ids": engine.list_pending_approvals(action)}
