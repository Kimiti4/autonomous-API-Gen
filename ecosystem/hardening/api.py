"""
API routes for ecosystem hardening.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from ecosystem.models import RoutingRequest

from .engine import EcosystemHardeningEngine, EcosystemHardeningPolicy
from .models import EcosystemComplianceEvidence


router = APIRouter(
    prefix="/v1/ecosystem/hardening",
    tags=["ecosystem-hardening"],
)


class IngestSLAMetricRequest(BaseModel):
    metric: str
    value: float


class CertifyEcosystemRequest(BaseModel):
    scope: str = "ecosystem"
    certified_by: str = "system"
    evidence: EcosystemComplianceEvidence = Field(
        default_factory=EcosystemComplianceEvidence
    )


class RevokeComplianceRequest(BaseModel):
    reason: str
    revoked_by: str = "system"


class RecordDependencyFailureRequest(BaseModel):
    dependency: str


class RecordDependencySuccessRequest(BaseModel):
    dependency: str


def enable_ecosystem_hardening(
    app: FastAPI,
    ecosystem_engine=None,
    governance_gateway=None,
    policy: EcosystemHardeningPolicy | None = None,
) -> EcosystemHardeningEngine:
    """Enable ecosystem hardening endpoints."""

    ecosystem_engine = ecosystem_engine or getattr(
        app.state,
        "ecosystem_engine",
        None,
    )

    if not ecosystem_engine:
        raise RuntimeError("Ecosystem engine is required for hardening.")

    engine = EcosystemHardeningEngine(
        ecosystem_engine=ecosystem_engine,
        governance_gateway=governance_gateway,
        policy=policy,
    )

    app.state.ecosystem_hardening_engine = engine

    app.include_router(router)

    return engine


def _engine(request: Request) -> EcosystemHardeningEngine:
    engine = getattr(request.app.state, "ecosystem_hardening_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Ecosystem hardening engine is not configured.",
        )

    return engine


@router.get("/treaties/{treaty_id}/risk")
def treaty_risk(treaty_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.assess_treaty(treaty_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/partners/{partner_id}/trust")
def partner_trust(partner_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.assess_partner(partner_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/routing/evaluate")
def guarded_routing(payload: RoutingRequest, request: Request):
    engine = _engine(request)

    return engine.guarded_routing(payload)


@router.post("/contracts/{contract_id}/sla/ingest")
def ingest_sla_metric(
    contract_id: str,
    payload: IngestSLAMetricRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.enforce_sla(
            contract_id=contract_id,
            metric=payload.metric,
            value=payload.value,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/compliance/certify", status_code=201)
def certify_ecosystem(payload: CertifyEcosystemRequest, request: Request):
    engine = _engine(request)

    return engine.certify_ecosystem(
        evidence=payload.evidence,
        certified_by=payload.certified_by,
        scope=payload.scope,
    )


@router.post("/compliance/{report_id}/revoke")
def revoke_compliance_report(
    report_id: str,
    payload: RevokeComplianceRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.revoke_compliance_report(
            report_id=report_id,
            reason=payload.reason,
            revoked_by=payload.revoked_by,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/audit/bundle")
def audit_bundle(request: Request):
    engine = _engine(request)

    return engine.build_audit_bundle()


@router.get("/observability/report")
def observability_report(request: Request):
    engine = _engine(request)

    return engine.observability_report()


@router.post("/resilience/failures", status_code=201)
def record_dependency_failure(
    payload: RecordDependencyFailureRequest,
    request: Request,
):
    engine = _engine(request)

    return engine.record_dependency_failure(payload.dependency)


@router.post("/resilience/success", status_code=201)
def record_dependency_success(
    payload: RecordDependencySuccessRequest,
    request: Request,
):
    engine = _engine(request)

    return engine.record_dependency_success(payload.dependency)


@router.get("/resilience/report")
def resilience_report(request: Request):
    engine = _engine(request)

    return engine.resilience_report()
