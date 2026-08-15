"""
API routes for Production Learning Certification.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .engine import ProductionLearningCertificationEngine
from .models import (
    OperationalReadinessEvidence,
    ProductionLearningCertificationPolicy,
)


router = APIRouter(
    prefix="/v1/learning/production-certification",
    tags=["production-learning-certification"],
)


class CertifyRequest(BaseModel):
    scope: str = "production_learning"
    certified_by: str = "system"
    prerequisite_26_7_report_id: Optional[str] = None
    evidence: Optional[OperationalReadinessEvidence] = None


class RevokeRequest(BaseModel):
    reason: str
    revoked_by: str = "system"


def enable_production_learning_certification(
    app: FastAPI,
    policy: ProductionLearningCertificationPolicy | None = None,
) -> ProductionLearningCertificationEngine:
    """Enable production learning certification endpoints."""

    learning_pipeline_certification_engine = (
        getattr(app.state, "learning_pipeline_certification_engine", None)
        or getattr(app.state, "learning_certification_engine", None)
    )

    telemetry_engine = getattr(app.state, "telemetry_engine", None)

    anomaly_engine = (
        getattr(app.state, "anomaly_engine", None)
        or getattr(app.state, "anomaly_detection_engine", None)
    )

    knowledge_sync_engine = getattr(app.state, "knowledge_sync_engine", None)

    evolution_feedback_engine = (
        getattr(app.state, "evolution_feedback_engine", None)
        or getattr(app.state, "evolution_integration_engine", None)
    )

    learning_governance_engine = getattr(
        app.state,
        "learning_governance_engine",
        None,
    )

    observability_engine = (
        getattr(app.state, "learning_observability_engine", None)
        or getattr(app.state, "learning_observability", None)
    )

    marketplace_autonomy_engine = getattr(
        app.state,
        "marketplace_autonomy_engine",
        None,
    )

    engine = ProductionLearningCertificationEngine(
        learning_pipeline_certification_engine=(
            learning_pipeline_certification_engine
        ),
        telemetry_engine=telemetry_engine,
        anomaly_engine=anomaly_engine,
        knowledge_sync_engine=knowledge_sync_engine,
        evolution_feedback_engine=evolution_feedback_engine,
        learning_governance_engine=learning_governance_engine,
        observability_engine=observability_engine,
        marketplace_autonomy_engine=marketplace_autonomy_engine,
        policy=policy,
    )

    app.state.production_learning_certification_engine = engine

    app.include_router(router)

    return engine


def _engine(request: Request) -> ProductionLearningCertificationEngine:
    engine = getattr(
        request.app.state,
        "production_learning_certification_engine",
        None,
    )

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Production learning certification engine is not configured.",
        )

    return engine


@router.post("/certify", status_code=201)
def certify(payload: CertifyRequest, request: Request):
    engine = _engine(request)

    return engine.certify(
        scope=payload.scope,
        certified_by=payload.certified_by,
        evidence=payload.evidence,
        prerequisite_26_7_report_id=payload.prerequisite_26_7_report_id,
    )


@router.get("/latest")
def latest_report(request: Request):
    engine = _engine(request)

    report = engine.latest_report()

    if not report:
        raise HTTPException(
            status_code=404,
            detail="No production learning certification report found.",
        )

    return report


@router.get("/report/{report_id}")
def get_report(report_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.report(report_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/report/{report_id}/revoke")
def revoke_report(report_id: str, payload: RevokeRequest, request: Request):
    engine = _engine(request)

    try:
        return engine.revoke(
            report_id=report_id,
            reason=payload.reason,
            revoked_by=payload.revoked_by,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
