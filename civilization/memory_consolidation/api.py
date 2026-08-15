"""
API routes for memory consolidation and Knowledge Graph sync.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .engine import (
    MemoryConsolidationEngine,
    MemoryConsolidationError,
    MemoryConsolidationPolicy,
)
from .gateway import InMemoryKnowledgeGraphGateway
from .models import MemorySensitivity, MemorySourceType


router = APIRouter(
    prefix="/v1/civilization/memory",
    tags=["organizational-memory-consolidation"],
)


class IngestMemoryRecordPayload(BaseModel):
    source_type: MemorySourceType
    source_id: str

    title: str
    summary: str = ""

    content: dict = Field(default_factory=dict)

    organization_id: Optional[str] = None

    subject_type: Optional[str] = None
    subject_id: Optional[str] = None

    evidence_refs: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    sensitivity: Optional[MemorySensitivity] = None

    ttl_days: Optional[int] = None
    occurred_at: Optional[str] = None


class ConsolidateRequestPayload(BaseModel):
    record_id: Optional[str] = None


class SyncRequestPayload(BaseModel):
    record_id: Optional[str] = None
    force: bool = False


def enable_memory_consolidation(
    app: FastAPI,
    kg_gateway=None,
    policy: Optional[MemoryConsolidationPolicy] = None,
) -> MemoryConsolidationEngine:
    """Enable memory consolidation endpoints."""

    gateway = kg_gateway or InMemoryKnowledgeGraphGateway()

    engine = MemoryConsolidationEngine(
        kg_gateway=gateway,
        policy=policy,
    )

    app.state.memory_consolidation_engine = engine
    app.state.memory_consolidation_gateway = gateway

    app.include_router(router)

    return engine


def _engine(request: Request) -> MemoryConsolidationEngine:
    engine = getattr(request.app.state, "memory_consolidation_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Memory consolidation engine is not configured.",
        )

    return engine


@router.post("/records", status_code=201)
def ingest_record(payload: IngestMemoryRecordPayload, request: Request):
    engine = _engine(request)

    try:
        return engine.ingest_record(
            source_type=payload.source_type,
            source_id=payload.source_id,
            title=payload.title,
            summary=payload.summary,
            content=payload.content,
            organization_id=payload.organization_id,
            subject_type=payload.subject_type,
            subject_id=payload.subject_id,
            evidence_refs=payload.evidence_refs,
            tags=payload.tags,
            sensitivity=payload.sensitivity,
            ttl_days=payload.ttl_days,
            occurred_at=payload.occurred_at,
        )
    except MemoryConsolidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/records")
def list_records(
    request: Request,
    status: Optional[str] = Query(default=None),
    sensitivity: Optional[MemorySensitivity] = Query(default=None),
    organization_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
):
    engine = _engine(request)

    return engine.list_records(
        status=status,
        sensitivity=sensitivity,
        organization_id=organization_id,
        limit=limit,
    )


@router.post("/consolidate")
def consolidate(payload: ConsolidateRequestPayload, request: Request):
    engine = _engine(request)

    try:
        if payload.record_id:
            return engine.consolidate_record(payload.record_id)

        return engine.consolidate_all()
    except MemoryConsolidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sync")
def sync(payload: SyncRequestPayload, request: Request):
    engine = _engine(request)

    try:
        if payload.record_id:
            return engine.sync_record(payload.record_id, force=payload.force)

        return engine.sync_all(force=payload.force)
    except MemoryConsolidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/sync-results")
def sync_results(request: Request):
    engine = _engine(request)
    return list(engine.sync_results.values())


@router.post("/retention/apply")
def apply_retention(request: Request):
    engine = _engine(request)
    return engine.apply_retention()


@router.get("/report")
def report(request: Request):
    engine = _engine(request)
    return engine.report()
