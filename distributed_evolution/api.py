"""
API routes for the Distributed Evolution Cloud.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .engine import DistributedEvolutionCloudEngine
from .models import ResourceRequirements


router = APIRouter(
    prefix="/v1/distributed-evolution",
    tags=["distributed-evolution-cloud"],
)


def enable_distributed_evolution(
    app: FastAPI,
    cluster_policy_version: str = "constitution.v1",
) -> DistributedEvolutionCloudEngine:
    """Enable distributed evolution cloud endpoints."""

    engine = DistributedEvolutionCloudEngine(
        cluster_policy_version=cluster_policy_version,
    )

    app.state.distributed_evolution_engine = engine

    app.include_router(router)

    return engine


def _engine(request: Request) -> DistributedEvolutionCloudEngine:
    engine = getattr(request.app.state, "distributed_evolution_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Distributed evolution engine is not configured.",
        )

    return engine


class RegisterNodeRequest(BaseModel):
    node_id: str
    region: str
    capabilities: List[str] = Field(default_factory=list)
    cpu_capacity: int = Field(default=2, ge=1)
    memory_mb_capacity: int = Field(default=1024, ge=128)
    policy_version: str
    public_key_ref: str


class SubmitCampaignRequest(BaseModel):
    name: str
    objective: str
    candidate_count: int = Field(default=1, ge=1)
    target_backends: List[str] = Field(default_factory=list)
    policy_version: Optional[str] = None
    requirements: Optional[ResourceRequirements] = None
    max_job_attempts: int = Field(default=3, ge=1)


@router.post("/nodes", status_code=201)
def register_node(payload: RegisterNodeRequest, request: Request):
    engine = _engine(request)

    try:
        return engine.register_node(
            node_id=payload.node_id,
            region=payload.region,
            capabilities=payload.capabilities,
            cpu_capacity=payload.cpu_capacity,
            memory_mb_capacity=payload.memory_mb_capacity,
            policy_version=payload.policy_version,
            public_key_ref=payload.public_key_ref,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/nodes/{node_id}/heartbeat")
def heartbeat(node_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.heartbeat(node_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/campaigns", status_code=201)
def submit_campaign(payload: SubmitCampaignRequest, request: Request):
    engine = _engine(request)

    return engine.submit_campaign(
        name=payload.name,
        objective=payload.objective,
        candidate_count=payload.candidate_count,
        target_backends=payload.target_backends,
        policy_version=payload.policy_version,
        requirements=payload.requirements,
        max_job_attempts=payload.max_job_attempts,
    )


@router.post("/campaigns/{campaign_id}/run")
def run_campaign(campaign_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.run_campaign(campaign_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/campaigns/{campaign_id}/recover")
def recover_campaign(campaign_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.recover_campaign(campaign_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/nodes/{node_id}/fail")
def fail_node(node_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.fail_node(node_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/campaigns/{campaign_id}")
def get_campaign(campaign_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine._get_campaign(campaign_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/jobs/{job_id}")
def get_job(job_id: str, request: Request):
    engine = _engine(request)

    job = engine.jobs.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    return job


@router.get("/metrics")
def metrics(request: Request):
    engine = _engine(request)
    return engine.metrics()


@router.get("/audit")
def audit(request: Request):
    engine = _engine(request)
    return engine.audit_events


@router.post("/audit/verify")
def verify_audit(request: Request):
    engine = _engine(request)

    return {
        "valid": engine.verify_audit_chain(),
    }


@router.get("/artifacts/{content_hash}/verify")
def verify_artifact(content_hash: str, request: Request):
    engine = _engine(request)

    return {
        "valid": engine.verify_artifact(content_hash),
    }
