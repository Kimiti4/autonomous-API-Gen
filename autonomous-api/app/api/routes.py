from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sse_starlette.sse import EventSourceResponse
import asyncio
from typing import List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.logger import logger
from app.core.exceptions import ObservationDomainError
from app.engine.reasoning.scorer import score_output
from app.engine.reasoning.orchestrator import ReasoningEngine
from app.engine.evolution import EvolutionEngine
from app.engine.elite_evolution import EliteEvolutionEngine
from app.engine.production_readiness import ProductionReadinessAnalyzer
from app.api.ws import manager
from app.storage.db import SessionLocal, engine, get_db
from app.storage.models import EvolutionRun
from app.schemas.evolution import (
    EvolutionRequest,
    EliteEvolutionRequest,
    EvolutionResponse,
    EliteEvolutionResponse,
    EvolutionResult,
    InsightsResponse,
    RunListResponse,
    RunInfo,
    HealthCheckResponse,
    ProductionReadinessRequest,
    ProductionReadinessResponse
)
import psutil
import os

router = APIRouter()
reasoning_engine = ReasoningEngine()
evolution_engine = EvolutionEngine()
elite_engine = EliteEvolutionEngine()
production_analyzer = ProductionReadinessAnalyzer()


# ==================== REASONING ENDPOINTS ====================

@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Comprehensive health check endpoint.
    Validates all system dependencies and returns status.
    Optimized for faster response time.
    """
    components = {}
    overall_status = "healthy"
    
    # Check database - optimized with context manager
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        components["database"] = "healthy"
    except Exception:
        logger.error("Database health check failed", exc_info=True)
        components["database"] = "unhealthy"
        overall_status = "degraded"
    
    # Check memory usage - only if needed
    try:
        process = psutil.Process(os.getpid())
        memory_percent = process.memory_percent()
        memory_info = process.memory_info()
        memory_usage = {
            "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
            "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
            "percent": round(memory_percent, 2)
        }
        
        if memory_percent > 80:
            components["memory"] = "warning: high usage"
            if overall_status == "healthy":
                overall_status = "degraded"
        else:
            components["memory"] = "healthy"
    except Exception:
        logger.error("Memory health check failed", exc_info=True)
        components["memory"] = "unknown"
        memory_usage = None
    
    # Check disk space - simplified
    try:
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        if disk_percent > 90:
            components["disk"] = f"critical: {disk_percent}% used"
            overall_status = "degraded"
        elif disk_percent > 75:
            components["disk"] = f"warning: {disk_percent}% used"
            if overall_status == "healthy":
                overall_status = "degraded"
        else:
            components["disk"] = "healthy"
    except Exception:
        logger.error("Disk health check failed", exc_info=True)
        components["disk"] = "unknown"
    
    from app.core.config import get_settings
    settings = get_settings()
    
    return HealthCheckResponse(
        status=overall_status,
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow().isoformat(),
        components=components,
        database=components.get("database", "unknown"),
        memory_usage=memory_usage
    )


@router.get("/stream")
async def stream_reasoning(task: str):
    async def event_generator():
        try:
            yield {"data": "[START] Thinking...\n"}

            outputs = []

            async def run_agent(agent):
                result = await agent.generate(task)
                return agent.name, result

            results = await asyncio.gather(
                *[run_agent(agent) for agent in reasoning_engine.agents]
            )

            for name, text in results:
                yield {"data": f"[AGENT] {name}: {text}\n"}

                outputs.append({
                    "agent": name,
                    "text": text,
                    "score": len(text)
                })

            yield {"data": "\n[SCORING]\n"}

            for o in outputs:
                yield {"data": f"{o['agent']} score: {o['score']}\n"}

            best = max(outputs, key=lambda x: x["score"])

            yield {"data": "\n[FINAL]\n"}
            yield {"data": best["text"] + "\n"}

        except Exception:
            logger.error("Reasoning stream failed", exc_info=True)
            yield {"data": "[ERROR] Internal platform error\n"}

    return EventSourceResponse(event_generator())


# ==================== PRODUCTION READINESS ====================

@router.post("/production/readiness", response_model=ProductionReadinessResponse)
async def analyze_production_readiness(request: ProductionReadinessRequest):
    """
    Score a candidate genome against production deployment requirements.
    This is designed to be used as a promotion gate for evolved architectures.
    """
    return production_analyzer.analyze(
        request.genome.model_dump(),
        deployment_target=request.deployment_target
    )


# ==================== EVOLUTION ENDPOINTS ====================

@router.post("/evolve/start", response_model=EvolutionResponse)
async def start_evolution(
    request: EvolutionRequest,
    background_tasks: BackgroundTasks
):
    """
    Start evolution process in background with WebSocket updates.
    Returns run_id to track progress.
    
    Validates:
    - generations: 1-100
    - population_size: 4-50
    """
    logger.info(f"Starting evolution: {request.generations} generations, pop size {request.population_size}")
    
    # Set WebSocket callback
    evolution_engine.set_websocket_callback(manager.broadcast)
    
    # Run evolution in background
    background_tasks.add_task(
        evolution_engine.run_async,
        generations=request.generations,
        population_size=request.population_size,
        use_docker=request.use_docker
    )
    
    return EvolutionResponse(
        message="Evolution started",
        note="Connect to WebSocket /ws/evolution to receive real-time updates"
    )


@router.get("/evolve/runs")
async def get_evolution_runs(db: Session = Depends(get_db)):
    """Get list of all evolution runs - optimized with dependency injection"""
    try:
        runs = db.query(EvolutionRun).order_by(EvolutionRun.started_at.desc()).limit(100).all()
        return {
            "runs": [run.to_dict() for run in runs],
            "total": len(runs)
        }
    except Exception:
        logger.error("Error fetching evolution runs", exc_info=True)
        raise ObservationDomainError(
            "Failed to fetch evolution runs",
            context={"operation": "evolve.runs"},
        )


@router.get("/evolve/run/{run_id}")
async def get_evolution_run(run_id: str, db: Session = Depends(get_db)):
    """Get details of specific evolution run - optimized with dependency injection"""
    try:
        run = db.query(EvolutionRun).filter(EvolutionRun.run_id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        return run.to_dict()
    except HTTPException:
        raise
    except Exception:
        logger.error(f"Error fetching run {run_id}", exc_info=True)
        raise ObservationDomainError(
            "Failed to fetch evolution run",
            context={"operation": "evolve.run", "parameters": {"runId": run_id}},
        )


@router.post("/evolve/sync")
async def run_evolution_sync(generations: int = 5, population_size: int = 8):
    """
    Run evolution synchronously (for testing).
    WARNING: This blocks until completion.
    """
    logger.info(f"Running synchronous evolution")
    result = evolution_engine.run_synchronous(
        generations=generations,
        population_size=population_size,
        use_docker=False
    )
    return result


# ==================== ELITE EVOLUTION ENDPOINTS ====================

@router.post("/evolve/elite/start", response_model=EliteEvolutionResponse)
async def start_elite_evolution(
    request: EliteEvolutionRequest,
    background_tasks: BackgroundTasks
):
    """
    Start elite evolution with learning and adaptation.
    Features:
    - Multi-population system
    - Adaptive mutation
    - Persistent memory
    - Real-time insights
    
    Validates all input parameters with Pydantic.
    """
    logger.info(f"Starting elite evolution: {request.generations} generations")
    
    # Set WebSocket callback
    elite_engine.set_websocket_callback(manager.broadcast)
    
    # Run elite evolution in background
    background_tasks.add_task(
        elite_engine.run_elite_evolution,
        generations=request.generations,
        population_size=request.population_size,
        use_multi_population=request.use_multi_population,
        enable_adaptive_mutation=request.enable_adaptive_mutation,
        use_docker=request.use_docker
    )
    
    return EliteEvolutionResponse(
        message="Elite evolution started",
        features={
            "multi_population": request.use_multi_population,
            "adaptive_mutation": request.enable_adaptive_mutation,
            "persistent_memory": True
        },
        note="Connect to WebSocket /ws/evolution for real-time updates"
    )


@router.get("/evolve/elite/insights")
async def get_elite_insights():
    """Get current learning insights from elite evolution"""
    insights = elite_engine.get_memory_insights()
    return insights


@router.post("/evolve/elite/clear-memory")
async def clear_elite_memory():
    """Clear all learned memory and reset adaptive systems"""
    elite_engine.clear_memory()
    return {"message": "Memory cleared successfully"}
