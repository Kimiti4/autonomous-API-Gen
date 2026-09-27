from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sse_starlette.sse import EventSourceResponse
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.logger import logger
from app.core.exceptions import ObservationDomainError
from app.engine.reasoning.orchestrator import ReasoningEngine
from app.engine.evolution import EvolutionEngine
from app.engine.elite_evolution import EliteEvolutionEngine
from app.engine.production_readiness import ProductionReadinessAnalyzer
from app.api.ws import manager
from app.storage.db import SessionLocal, get_db
from app.storage.models import EvolutionRun
from app.schemas.evolution import EvolutionRequest, EliteEvolutionRequest, EvolutionResponse, EliteEvolutionResponse, ProductionReadinessRequest, ProductionReadinessResponse, HealthCheckResponse
from app.middleware.security import require_auth
from pydantic import BaseModel, Field
from app.core.memory_clear import MemoryClearAuditStore, clear_elite_memory
from app.core.runtime_control import assert_evolution_enabled
from app.core.config import get_settings
import psutil
import os

router = APIRouter()
reasoning_engine = ReasoningEngine()
evolution_engine = EvolutionEngine()
elite_engine = EliteEvolutionEngine()
production_analyzer = ProductionReadinessAnalyzer()

@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    components = {}; overall_status = "healthy"
    try:
        db = SessionLocal(); db.execute(text("SELECT 1")); db.close(); components["database"] = "healthy"
    except Exception:
        logger.error("Database health check failed", exc_info=True); components["database"] = "unhealthy"; overall_status = "degraded"
    try:
        process = psutil.Process(os.getpid()); memory_percent = process.memory_percent(); memory_info = process.memory_info()
        memory_usage = {"rss_mb": round(memory_info.rss / 1024 / 1024, 2), "vms_mb": round(memory_info.vms / 1024 / 1024, 2), "percent": round(memory_percent, 2)}
        components["memory"] = "warning: high usage" if memory_percent > 80 else "healthy"
        if memory_percent > 80: overall_status = "degraded"
    except Exception:
        logger.error("Memory health check failed", exc_info=True); components["memory"] = "unknown"; memory_usage = None
    try:
        disk_percent = psutil.disk_usage('/').percent
        components["disk"] = f"critical: {disk_percent}% used" if disk_percent > 90 else (f"warning: {disk_percent}% used" if disk_percent > 75 else "healthy")
        if disk_percent > 75: overall_status = "degraded"
    except Exception:
        logger.error("Disk health check failed", exc_info=True); components["disk"] = "unknown"
    from app.core.config import get_settings
    settings = get_settings()
    return HealthCheckResponse(status=overall_status, version=settings.APP_VERSION, timestamp=datetime.utcnow().isoformat(), components=components, database=components.get("database", "unknown"), memory_usage=memory_usage)

@router.get("/stream")
async def stream_reasoning(task: str):
    async def event_generator():
        try:
            yield {"data": "[START] Thinking...\n"}; outputs = []
            async def run_agent(agent): return agent.name, await agent.generate(task)
            results = await asyncio.gather(*[run_agent(agent) for agent in reasoning_engine.agents])
            for name, text in results:
                yield {"data": f"[AGENT] {name}: {text}\n"}; outputs.append({"agent": name, "text": text, "score": len(text)})
            yield {"data": "\n[SCORING]\n"}
            for o in outputs: yield {"data": f"{o['agent']} score: {o['score']}\n"}
            best = max(outputs, key=lambda x: x["score"]); yield {"data": "\n[FINAL]\n"}; yield {"data": best["text"] + "\n"}
        except Exception:
            logger.error("Reasoning stream failed", exc_info=True); yield {"data": "[ERROR] Internal platform error\n"}
    return EventSourceResponse(event_generator())

@router.post("/production/readiness", response_model=ProductionReadinessResponse)
async def analyze_production_readiness(request: ProductionReadinessRequest):
    return production_analyzer.analyze(request.genome.model_dump(), deployment_target=request.deployment_target)

@router.post("/evolve/start", response_model=EvolutionResponse)
async def start_evolution(request: EvolutionRequest, background_tasks: BackgroundTasks):
    assert_evolution_enabled()
    logger.info(f"Starting evolution: {request.generations} generations, pop size {request.population_size}, runtime={request.use_docker}, seed={request.seed}")
    evolution_engine.set_websocket_callback(manager.broadcast)
    background_tasks.add_task(evolution_engine.run_async, generations=request.generations, population_size=request.population_size, use_docker=request.use_docker, seed=request.seed)
    return EvolutionResponse(message="Evolution started", note="Runtime Docker evaluation is the default. Set use_docker=false only for explicit static heuristic research.")

@router.get("/evolve/runs")
async def get_evolution_runs(db: Session = Depends(get_db)):
    try:
        runs = db.query(EvolutionRun).order_by(EvolutionRun.started_at.desc()).limit(100).all()
        return {"runs": [run.to_dict() for run in runs], "total": len(runs)}
    except Exception:
        logger.error("Error fetching evolution runs", exc_info=True); raise ObservationDomainError("Failed to fetch evolution runs", context={"operation": "evolve.runs"})

@router.get("/evolve/run/{run_id}")
async def get_evolution_run(run_id: str, db: Session = Depends(get_db)):
    try:
        run = db.query(EvolutionRun).filter(EvolutionRun.run_id == run_id).first()
        if not run: raise HTTPException(status_code=404, detail="Run not found")
        return run.to_dict()
    except HTTPException: raise
    except Exception:
        logger.error(f"Error fetching run {run_id}", exc_info=True); raise ObservationDomainError("Failed to fetch evolution run", context={"operation": "evolve.run", "parameters": {"runId": run_id}})

@router.post("/evolve/sync")
async def run_evolution_sync(generations: int = 5, population_size: int = 8):
    assert_evolution_enabled()
    logger.info("Running synchronous evolution in worker thread")
    return await asyncio.to_thread(evolution_engine.run_synchronous, generations=generations, population_size=population_size, use_docker=False)

@router.post("/evolve/elite/start", response_model=EliteEvolutionResponse)
async def start_elite_evolution(request: EliteEvolutionRequest, background_tasks: BackgroundTasks):
    assert_evolution_enabled()
    logger.info(f"Starting elite evolution: {request.generations} generations, runtime={request.use_docker}, seed={request.seed}")
    elite_engine.set_websocket_callback(manager.broadcast)
    background_tasks.add_task(elite_engine.run_elite_evolution, generations=request.generations, population_size=request.population_size, use_multi_population=request.use_multi_population, enable_adaptive_mutation=request.enable_adaptive_mutation, use_docker=request.use_docker, seed=request.seed)
    return EliteEvolutionResponse(message="Elite evolution started", features={"multi_population": request.use_multi_population, "adaptive_mutation": request.enable_adaptive_mutation, "persistent_memory": True}, note="Connect to WebSocket /ws/evolution for real-time updates")

@router.get("/evolve/elite/insights")
async def get_elite_insights(): return elite_engine.get_memory_insights()

class EliteMemoryClearRequest(BaseModel):
    confirmation: str = Field(min_length=1)
    operation_id: str | None = None


@router.post("/evolve/elite/clear-memory")
async def clear_elite_memory_route(
    request: EliteMemoryClearRequest,
    auth=Depends(require_auth),
):
    return clear_elite_memory(
        memory=elite_engine.memory,
        adaptive_mutator=elite_engine.adaptive_mutator,
        actor=auth.subject,
        confirmation=request.confirmation,
        operation_id=request.operation_id,
    )

@router.get("/evolve/elite/clear-memory/audit")
async def elite_memory_clear_audit(_auth=Depends(require_auth)):
    records = MemoryClearAuditStore(
        get_settings().GOVERNANCE_AUDIT_SIGNING_KEY
    ).verify()
    return {
        "target": "elite-memory",
        "verified": True,
        "records": [
            {
                "sequence": record.sequence,
                "eventType": record.event_type,
                "payload": record.payload,
                "previousHash": record.previous_hash,
                "recordHash": record.record_hash,
                "signature": record.signature,
            }
            for record in records
        ],
    }


class KillSwitchControlRequest(BaseModel):
    reason: str = ""
    actor_id: str = Field(min_length=1)


@router.get("/evolution/kill-switch")
async def get_evolution_kill_switch(_auth=Depends(require_auth)):
    from app.core.runtime_control import get_kill_switch
    state = get_kill_switch()
    return state.__dict__


@router.post("/evolution/kill-switch/activate")
async def activate_evolution_kill_switch(
    payload: KillSwitchControlRequest,
    auth=Depends(require_auth),
):
    from app.core.runtime_control import activate_kill_switch
    return activate_kill_switch(reason=payload.reason, actor=auth.subject).__dict__


@router.post("/evolution/kill-switch/deactivate")
async def deactivate_evolution_kill_switch(
    payload: KillSwitchControlRequest,
    auth=Depends(require_auth),
):
    from app.core.runtime_control import deactivate_kill_switch
    return deactivate_kill_switch(actor=auth.subject, reason=payload.reason).__dict__
