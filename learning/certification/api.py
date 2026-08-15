"""
API routes for learning pipeline certification.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .engine import LearningPipelineCertificationEngine
from .models import LearningPipelineCertificationPolicy

router = APIRouter(
    prefix="/v1/learning/certification",
    tags=["learning-pipeline-certification"],
)


class CertifyRequest(BaseModel):
    scope: str = "learning_pipeline"
    certified_by: str = "system"
    evidence_refs: List[str] = Field(default_factory=list)


class RevokeRequest(BaseModel):
    reason: str
    revoked_by: str = "system"


def enable_learning_pipeline_certification(
    app: FastAPI,
    learning_engine=None,
    analytics_engine=None,
    governance_engine=None,
    observability_engine=None,
    knowledge_sync_engine=None,
    policy: LearningPipelineCertificationPolicy | None = None,
) -> LearningPipelineCertificationEngine:
    """Enable learning pipeline certification endpoints."""

    learning_engine = learning_engine or getattr(
        app.state,
        "learning_engine",
        None,
    )

    analytics_engine = analytics_engine or getattr(
        app.state,
        "anomaly_engine",
        None,
    )

    governance_engine = governance_engine or getattr(
        app.state,
        "learning_governance_engine",
        None,
    )

    observability_engine = observability_engine or getattr(
        app.state,
        "learning_observability_engine",
        None,
    )

    knowledge_sync_engine = knowledge_sync_engine or getattr(
        app.state,
        "knowledge_sync_engine",
        None,
    )

    engine = LearningPipelineCertificationEngine(
        learning_engine=learning_engine,
        analytics_engine=analytics_engine,
        governance_engine=governance_engine,
        observability_engine=observability_engine,
        knowledge_sync_engine=knowledge_sync_engine,
        policy=policy,
    )

    app.state.learning_certification_engine = engine

    app.include_router(router)

    return engine


def _engine(request: Request) -> LearningPipelineCertificationEngine:
    engine = getattr(request.app.state, "learning_certification_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Learning pipeline certification engine is not configured.",
        )

    return engine


@router.post("/certify", status_code=201)
def certify(payload: CertifyRequest, request: Request):
    engine = _engine(request)

    return engine.certify(
        scope=payload.scope,
        certified_by=payload.certified_by,
        evidence_refs=payload.evidence_refs,
    )


@router.get("/latest")
def latest_report(request: Request):
    engine = _engine(request)

    report = engine.latest_report()

    if not report:
        raise HTTPException(
            status_code=404,
            detail="No certification report found.",
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
