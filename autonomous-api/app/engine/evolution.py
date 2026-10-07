from app.core.runtime_control import assert_evolution_enabled

import asyncio
import uuid
import random
from typing import Callable, Optional
from datetime import datetime
from app.core.logger import logger
from app.engine.genome import Genome
from app.core.population import Population
from app.core.crossover import crossover
from app.core.mutation import mutate
from app.engine.fitness import calculate_fitness
from app.engine.builder import build_genome_output
from app.engine.backend_contract import BackendTarget, PYTHON_FASTAPI
from app.engine.candidate_evaluator import evaluate_candidate_async
from app.engine.backends import get_backend, promote_verified_artifact
from app.governance.runtime import get_governance
from app.core.config import get_settings
from app.engine.production_readiness import ProductionReadinessAnalyzer
from app.storage.db import SessionLocal
from app.storage.models import GenomeRecord, EvolutionRun
from app.storage.lease import acquire_control_plane_lease, heartbeat_control_plane_lease, release_control_plane_lease

class EvolutionEngine:
    """Main genetic evolution engine with durable lifecycle and provenance."""
    _EVENT_TYPE_MAP = {"evolution_start":"evolution.stage_changed","generation_start":"evolution.stage_changed","new_best":"evolution.stage_changed","candidate_promoted":"candidate.promoted","generation_complete":"fitness.evaluated","building_best":"evolution.stage_changed","docker_test":"evolution.stage_changed","evolution_complete":"evolution.stage_changed","evolution_failed":"evolution.stage_changed"}

    def __init__(self, target: BackendTarget = PYTHON_FASTAPI):
        self.target = target
        self.docker_runner = None; self.websocket_callback: Optional[Callable] = None; self.dispatcher = None; self.production_analyzer = ProductionReadinessAnalyzer()

    def set_websocket_callback(self, callback: Callable): self.websocket_callback = callback
    def set_dispatcher(self, dispatcher): self.dispatcher = dispatcher

    @staticmethod
    def _is_authoritative(record) -> bool:
        history = getattr(record, "history", {}) or {}
        return (
            getattr(record, "status", None) == "completed"
            and history.get("phase") == "completed"
            and history.get("promotion_status") == "published"
            and bool(history.get("best_artifact_digest"))
        )

    @staticmethod
    def recover_interrupted_runs() -> int:
        from datetime import datetime, timezone
        from app.storage.lease import lease_is_live
        db = SessionLocal()
        recovered = 0
        try:
            for record in db.query(EvolutionRun).filter(EvolutionRun.status == "running").all():
                if lease_is_live():
                    continue
                record.status = "abandoned"
                record.completed_at = datetime.now(timezone.utc)
                history = dict(getattr(record, "history", {}) or {})
                history["phase"] = "abandoned"
                record.history = history
                recovered += 1
            if recovered:
                db.commit()
            return recovered
        finally:
            db.close()

    async def run_async(self, generations=10, population_size=10, use_docker=True, seed=None):
        owner = "evolution:" + str(uuid.uuid4())
        token = acquire_control_plane_lease(owner_run_id=owner)
        try:
            self._active_lease_token = token
            return await self._run_async_unleased(generations, population_size, use_docker, seed)
        finally:
            self._active_lease_token = None
            release_control_plane_lease(token)

    def run_synchronous(self, generations=10, population_size=10, use_docker=False):
        owner = "evolution:" + str(uuid.uuid4())
        token = acquire_control_plane_lease(owner_run_id=owner)
        try:
            self._active_lease_token = token
            return self._run_synchronous_unleased(generations, population_size, use_docker)
        finally:
            self._active_lease_token = None
            release_control_plane_lease(token)

    async def _emit_update(self, data: dict, *, run_id: str = "global", generation: int = 0):
        if self.websocket_callback:
            try: await self.websocket_callback(data)
            except Exception: logger.error("WebSocket emit error", exc_info=True)
        if self.dispatcher is not None:
            event_type = self._EVENT_TYPE_MAP.get(data.get("type", ""), "evolution.stage_changed")
            try: await self.dispatcher.emit(stream_id=run_id, event_type=event_type, payload=data, correlation_id=run_id, generation=generation)
            except Exception: logger.error("Envelope emission failed", exc_info=True)

    @staticmethod
    def _lineage_payload(genome: Genome) -> dict:
        return {"genome_id": genome.genome_id, "lineage": getattr(genome, "lineage", {})}

    @staticmethod
    def _fitness_from_evidence(evidence: dict) -> float:
        """Convert candidate evidence into a safe evolutionary fitness value.

        Only completed runtime or static evaluations may contribute fitness.
        Build failures and runtime failures are deliberately zero-fitness so a
        partially verified candidate can never be promoted as the best result.
        """
        if not evidence.get("build_ok"):
            return 0.0
        mode = evidence.get("evaluation_mode")
        if mode == "runtime":
            score = evidence.get("runtime_score")
        elif mode == "static":
            score = evidence.get("static_score")
        else:
            return 0.0
        return float(score) if score is not None else 0.0

    async def _governance_allows_promotion(self, genome) -> bool:
        if not getattr(get_settings(), "GOVERNANCE_ENFORCEMENT_REQUIRED", False):
            return True
        state = await get_governance().materialize_candidate(genome.genome_id)
        decision = state.latest_decision()
        if decision is None:
            return False
        return (
            getattr(decision, "verdict", None) == "approve"
            and bool(getattr(decision, "authorizesTransition", False))
        )

    async def _publish_governed_candidate(self, genome, evidence: dict):
        if not await self._governance_allows_promotion(genome):
            raise ValueError("governance promotion gate denied")
        source = evidence.get("artifact_path") or evidence.get("output_path")
        destination = evidence.get("output_path") or evidence.get("artifact_path")
        digest = str(evidence.get("artifact_digest") or "")
        if digest.startswith("sha256:"):
            digest = digest[len("sha256:"):]
        return promote_verified_artifact(source, destination, expected_digest=digest)

    async def _run_async_unleased(self, generations: int = 10, population_size: int = 10, use_docker: bool = True, seed: Optional[int] = None) -> dict:
        if generations < 1 or population_size < 2: raise ValueError("generations must be >= 1 and population_size must be >= 2")
        run_id = str(uuid.uuid4())
        previous_state = random.getstate()
        if seed is not None: random.seed(seed)
        db = SessionLocal()
        try: db.add(EvolutionRun(run_id=run_id, status="running", total_generations=generations)); db.commit()
        finally: db.close()
        try:
            await self._emit_update({"type":"evolution_start","run_id":run_id,"generations":generations,"population_size":population_size,"evaluation_mode":"runtime" if use_docker and get_backend(self.target.backend_id).runtime_supported else "static","backend_id":self.target.backend_id,"seed":seed}, run_id=run_id)
            population = Population(size=population_size); history = []; best_genome = None; best_fitness = float("-inf"); output_path = None; best_evidence = None
            for gen in range(generations):
                assert_evolution_enabled()
                await self._emit_update({"type":"generation_start","run_id":run_id,"generation":gen+1,"total_generations":generations,"backend_id":self.target.backend_id}, run_id=run_id, generation=gen+1)
                fitness_scores = []; genomes_to_save = []
                for genome in population.individuals:
                    evidence = await evaluate_candidate_async(genome, use_docker=use_docker, target=self.target)
                    heartbeat_control_plane_lease(self._active_lease_token) if hasattr(self, "_active_lease_token") else None
                    fitness = self._fitness_from_evidence(evidence)
                    fitness_scores.append(fitness)
                    payload = genome.encode(); payload["lineage"] = self._lineage_payload(genome); payload["evaluation"] = evidence; payload["provenance"] = {"run_id": run_id, "generation": gen + 1, "seed": seed, "evaluation_mode": evidence["evaluation_mode"], "backend_id": self.target.backend_id}
                    genomes_to_save.append({"genome_data":payload,"fitness_score":fitness,"generation":gen+1})
                    if evidence["build_ok"] and fitness > 0.0 and fitness > best_fitness:
                        best_fitness, best_genome = fitness, genome
                        best_evidence = dict(evidence)
                        await self._emit_update({"type":"new_best","run_id":run_id,"generation":gen+1,"fitness":fitness,"genome":payload}, run_id=run_id, generation=gen+1)
                db = SessionLocal()
                try: db.add_all([GenomeRecord(**item) for item in genomes_to_save]); db.commit()
                except Exception: db.rollback(); logger.error("Error saving genomes", exc_info=True); raise
                finally: db.close()
                avg_fitness = sum(fitness_scores) / len(fitness_scores)
                history.append({"generation":gen+1,"scores":fitness_scores,"best_score":max(fitness_scores),"avg_score":avg_fitness})
                await self._emit_update({"type":"generation_complete","run_id":run_id,"generation":gen+1,"best_score":max(fitness_scores),"avg_score":avg_fitness,"fitness_scores":fitness_scores}, run_id=run_id, generation=gen+1)
                await asyncio.sleep(0)
                parents = population.select_parents(fitness_scores, num_parents=2); new_population = parents.copy()
                while len(new_population) < population_size: new_population.append(mutate(crossover(parents[0], parents[1]), mutation_rate=0.2))
                population.replace(new_population)
            build_error = None
            if best_genome:
                try:
                    output_path = build_genome_output(best_genome, target=self.target)
                except ValueError as exc:
                    output_path = None
                    build_error = f"best genome not lowerable: {exc}"
                    logger.error("Best genome build failed: %s", exc)
                await self._emit_update({"type":"building_best","run_id":run_id,"output_path":output_path}, run_id=run_id)
                if output_path and not build_error and getattr(get_settings(), "GOVERNANCE_ENFORCEMENT_REQUIRED", False):
                    publish_evidence = dict(best_evidence or {})
                    publish_evidence["output_path"] = output_path
                    publish_evidence.setdefault("artifact_path", output_path)
                    try:
                        output_path = await self._publish_governed_candidate(best_genome, publish_evidence)
                        await self._emit_update({"type":"candidate_promoted","run_id":run_id,"output_path":output_path}, run_id=run_id)
                    except ValueError as exc:
                        output_path = None
                        build_error = str(exc)
                        logger.error("Governed promotion denied: %s", exc)
            elif best_genome is None:
                build_error = "no candidate could be lowered by the selected backend"
            result = {"run_id":run_id,"best_genome":best_genome.encode() if best_genome and not build_error else None,"best_fitness":best_fitness if best_genome and not build_error else 0.0,"production_readiness":self.production_analyzer.analyze(best_genome) if best_genome and not build_error else None,"history":history,"output_path":output_path,"build_error":build_error,"total_generations":generations,"evaluation_mode":"runtime" if use_docker and get_backend(self.target.backend_id).runtime_supported else "static","backend_id":self.target.backend_id,"seed":seed}
            db = SessionLocal()
            try:
                record = db.query(EvolutionRun).filter(EvolutionRun.run_id == run_id).first()
                if record:
                    record.status="failed" if build_error else "completed"; record.best_fitness=result["best_fitness"]; record.best_genome=result["best_genome"]; record.completed_at=datetime.utcnow()
                    if build_error:
                        record.history={"schema_version":1,"phase":"failed","promotion_status":"failed","generations":history,"build_error":build_error,"error":build_error}
                    else:
                        record.history={"schema_version":1,"phase":"completed","promotion_status":"published","generations":history,"build_error":None}
                        if best_evidence and best_evidence.get("artifact_digest"):
                            record.history["best_artifact_digest"]=best_evidence["artifact_digest"]
                    db.commit()
            finally: db.close()
            if build_error:
                await self._emit_update({"type":"evolution_failed","run_id":run_id,"error":build_error}, run_id=run_id)
            else:
                await self._emit_update({"type":"evolution_complete","run_id":run_id,"result":result}, run_id=run_id)
            return result
        except Exception as exc:
            logger.error("Evolution run failed", exc_info=True)
            db = SessionLocal()
            try:
                record = db.query(EvolutionRun).filter(EvolutionRun.run_id == run_id).first()
                if record: record.status="failed"; record.completed_at=datetime.utcnow(); record.history={"schema_version":1,"phase":"failed","promotion_status":"failed","error":str(exc)}; db.commit()
            except Exception: db.rollback(); logger.error("Failed to persist evolution failure state", exc_info=True)
            finally: db.close()
            await self._emit_update({"type":"evolution_failed","run_id":run_id,"error":"Evolution run failed"}, run_id=run_id); raise
        finally:
            if seed is not None: random.setstate(previous_state)

    def _run_synchronous_unleased(self, generations: int = 10, population_size: int = 10, use_docker: bool = False) -> dict:
        if generations < 1 or population_size < 2: raise ValueError("generations must be >= 1 and population_size must be >= 2")
        population = Population(size=population_size); history = []; best_genome = None; best_fitness = float("-inf"); output_path = None
        for gen in range(generations):
            fitness_scores = []
            for g in population.individuals:
                fitness_scores.append(calculate_fitness(g))
                heartbeat_control_plane_lease(self._active_lease_token) if hasattr(self, "_active_lease_token") else None
            for fitness, genome in zip(fitness_scores, population.individuals):
                if fitness > best_fitness: best_fitness, best_genome = fitness, genome
            history.append({"generation": gen + 1, "scores": fitness_scores, "best_score": max(fitness_scores), "avg_score": sum(fitness_scores) / len(fitness_scores)})
            parents = population.select_parents(fitness_scores, num_parents=2); new_population = parents.copy()
            while len(new_population) < population_size: new_population.append(mutate(crossover(parents[0], parents[1]), mutation_rate=0.2))
            population.replace(new_population)
        build_error = None
        if best_genome:
            try:
                output_path = build_genome_output(best_genome, target=self.target)
            except ValueError as exc:
                output_path = None
                build_error = f"best genome not lowerable: {exc}"
                logger.error("Best genome build failed: %s", exc)
        return {"best_genome": best_genome.encode() if best_genome and not build_error else None, "best_fitness": best_fitness if best_genome and not build_error else 0.0, "production_readiness": self.production_analyzer.analyze(best_genome) if best_genome and not build_error else None, "history": history, "output_path": output_path, "build_error": build_error, "total_generations": generations, "backend_id": self.target.backend_id}