"""Observatory HTTP boundary: read views, event ingest, commands, SSE stream.

Transport only: no policy, epistemic, or governance logic lives here.
All decisions come from the gateway.
"""
from __future__ import annotations

from typing import Optional

import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse

from ..config import get_settings
from ..domain import (Actor, BatchEventInput, BatchIngestionResponse,
                      CommandRequest, EventInput, event_from_input)
from ..gateway import ObservatoryGateway
from .deps import get_actor, get_gateway, require_operator, require_writer

router = APIRouter(prefix="/observatory", tags=["observatory"])


@router.get("/dashboard")
async def dashboard(gateway: ObservatoryGateway = Depends(get_gateway)):
    return await gateway.dashboard()


@router.get("/overview")
async def overview(gateway: ObservatoryGateway = Depends(get_gateway)):
    return await gateway.overview()


@router.get("/runtime")
async def runtime(gateway: ObservatoryGateway = Depends(get_gateway)):
    return await gateway.runtime()


@router.get("/governance")
async def governance(gateway: ObservatoryGateway = Depends(get_gateway)):
    return await gateway.governance()


@router.get("/health")
async def health(gateway: ObservatoryGateway = Depends(get_gateway)):
    return await gateway.health()


@router.get("/timeline")
async def timeline(
    subject: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=1000),
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.timeline(subject=subject, limit=limit)


@router.get("/evolution/{evolution_id}")
async def evolution(
    evolution_id: str,
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.evolution(evolution_id)


@router.get("/evidence/{evidence_id}")
async def evidence(
    evidence_id: str,
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.evidence(evidence_id)


@router.get("/requirement/{requirement_id}")
async def requirement(
    requirement_id: str,
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.requirement(requirement_id)


@router.get("/capability/{capability_id}")
async def capability(
    capability_id: str,
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.capability(capability_id)


@router.get("/experiments")
async def experiments_overview(
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.experiments_overview()


@router.get("/experiments/{experiment_id}")
async def experiment_detail(
    experiment_id: str,
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.experiment_detail(experiment_id)


@router.get("/fitness")
async def fitness_overview(
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.fitness_overview()


@router.get("/fitness/{fitness_id}")
async def fitness_detail(
    fitness_id: str,
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.fitness_detail(fitness_id)


@router.get("/genomes")
async def genomes_overview(
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.genomes_overview()


@router.get("/genomes/{genome_id}")
async def genome_detail(
    genome_id: str,
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.genome_detail(genome_id)


def split_csv(value: Optional[str]) -> Optional[list]:
    if not value:
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or None


@router.get("/search")
async def search_events(
    q: Optional[str] = Query(default=None),
    categories: Optional[str] = Query(default=None),
    severities: Optional[str] = Query(default=None),
    epistemic_statuses: Optional[str] = Query(default=None),
    since: Optional[str] = Query(default=None),
    until: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    try:
        return await gateway.search_events(
            query=q, categories=split_csv(categories),
            severities=split_csv(severities),
            epistemic_statuses=split_csv(epistemic_statuses),
            since=since, until=until, limit=limit)
    except ValueError as exc:
        # GAP-003 (D36 T2): an unparseable search bound is a client error,
        # never a server crash. Only _normalize_timestamp can raise here.
        raise HTTPException(
            status_code=400, detail=f"invalid search bound: {exc}")


@router.get("/export/events")
async def export_events(
    q: Optional[str] = Query(default=None),
    categories: Optional[str] = Query(default=None),
    severities: Optional[str] = Query(default=None),
    epistemic_statuses: Optional[str] = Query(default=None),
    since: Optional[str] = Query(default=None),
    until: Optional[str] = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
    format: str = Query(default="json"),
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    if format not in {"json", "csv"}:
        raise HTTPException(status_code=400,
                            detail="format must be json or csv")
    try:
        results = await gateway.search_events(
            query=q, categories=split_csv(categories),
            severities=split_csv(severities),
            epistemic_statuses=split_csv(epistemic_statuses),
            since=since, until=until, limit=limit)
    except ValueError as exc:
        # GAP-003 (D36 T2): same bound contract as /search.
        raise HTTPException(
            status_code=400, detail=f"invalid search bound: {exc}")
    if format == "json":
        return results
    fieldnames = ["event_id", "timestamp", "category", "type", "subject_id",
                  "source", "epistemic_status", "severity", "entity_type",
                  "summary"]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames,
                            extrasaction="ignore")
    writer.writeheader()
    for row in results:
        writer.writerow(row)
    return Response(
        content=output.getvalue(), media_type="text/csv",
        headers={"Content-Disposition":
                 "attachment; filename=observatory-events.csv"})


@router.get("/audit-bundle/{subject_id}")
async def audit_bundle(
    subject_id: str,
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.audit_bundle(subject_id)


@router.get("/provenance")
async def provenance_overview(
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.provenance_overview()


@router.get("/provenance/{subject_id}")
async def provenance_audit(
    subject_id: str,
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.provenance_audit(subject_id)


@router.get("/knowledge/overview")
async def knowledge_overview(
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.knowledge_overview()


@router.get("/knowledge/{subject_id}/memory")
async def knowledge_memory(
    subject_id: str,
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.knowledge_memory(subject_id)


@router.get("/knowledge")
async def knowledge_all(gateway: ObservatoryGateway = Depends(get_gateway)):
    return await gateway.knowledge(None)


@router.get("/knowledge/{subject_id}")
async def knowledge_subject(
    subject_id: str,
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.knowledge(subject_id)


@router.get("/trace/{subject_id}")
async def trace(
    subject_id: str,
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.trace(subject_id)


@router.get("/explain/{subject_id}")
async def explain(
    subject_id: str,
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.explain(subject_id)


@router.post("/events")
async def ingest_event(
    event_input: EventInput,
    gateway: ObservatoryGateway = Depends(get_gateway),
    actor: Actor = Depends(get_actor),
    _writer: Actor = Depends(require_writer),
):
    event = event_from_input(event_input)
    event_id = await gateway.observe(event)
    return {"status": "accepted", "event_id": event_id,
            "actor_id": actor.id}


@router.post("/events/batch", response_model=BatchIngestionResponse)
async def ingest_event_batch(
    batch: BatchEventInput,
    gateway: ObservatoryGateway = Depends(get_gateway),
    actor: Actor = Depends(get_actor),
    _writer: Actor = Depends(require_writer),
):
    settings = get_settings()
    if not batch.events:
        raise HTTPException(status_code=400, detail="event batch is empty")
    if len(batch.events) > settings.max_batch_size:
        raise HTTPException(
            status_code=413,
            detail=f"event batch exceeds maximum size of {settings.max_batch_size}")
    events = []
    for index, event_input in enumerate(batch.events):
        try:
            events.append(event_from_input(event_input))
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail={"error": "invalid_event", "index": index,
                        "reason": str(exc)}) from exc
    return await gateway.observe_batch(events)


@router.post("/commands")
async def request_command(
    command: CommandRequest,
    gateway: ObservatoryGateway = Depends(get_gateway),
    actor: Actor = Depends(get_actor),
    _operator: Actor = Depends(require_operator),
):
    return await gateway.request_command(command, actor)


@router.get("/stream")
async def stream(gateway: ObservatoryGateway = Depends(get_gateway)):
    queue = gateway.bus.subscribe()

    async def event_stream():
        try:
            while True:
                event = await queue.get()
                yield f"data: {event.model_dump_json()}\n\n"
        finally:
            gateway.bus.unsubscribe(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive",
                 "X-Accel-Buffering": "no"},
    )
