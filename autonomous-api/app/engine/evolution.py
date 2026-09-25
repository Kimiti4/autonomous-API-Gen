import asyncio
import uuid
import random
from typing import Callable, Optional
from datetime import datetime
from app.core.logger import logger
from app.core.config import get_settings
from app.governance.runtime import get_governance
from app.engine.genome import Genome
from app.core.population import Population
from app.core.crossover import crossover
from app.core.mutation import mutate
from app.engine.fitness import calculate_fitness
from app.engine.backend_contract import BackendTarget, PYTHON_FASTAPI
from app.engine.candidate_evaluator import evaluate_candidate_async
from app.engine.backends import get_backend, promote_verified_artifact
from app.engine.production_readiness import ProductionReadinessAnalyzer
from app.storage.db import SessionLocal
from app.storage.models import GenomeRecord, EvolutionRun
from app.storage.lease import (
    ControlPlaneBusy,
    acquire_control_plane_lease,
    heartbeat_control_plane_lease,
    release_control_plane_lease,
)

class EvolutionEngine:
    """Main genetic evolution engine with durable lifecycle and provenance."""
    _EVENT_TYPE_MAP = {"evolution_start":"evolution.stage_changed","generation_start":"evolution.stage_changed","new_best":"candidate.promoted","generation_complete":"fitness.evaluated","building_best":"evolution.stage_changed","docker_test":"evolution.stage_changed","evolution_complete":"evolution.stage_changed","evolution_failed":"evolution.stage_changed"}

    def __init__(self, target: BackendTarget = PYTHON_FASTAPI):
        self.target = target
        self.docker_runner = None; self.websocket_callback: Optional[Callable] = None; self.dispatcher = None; self.production_analyzer = ProductionReadinessAnalyzer()

    def set_websocket_callback(self, callback: Callable): self.websocket_callback = callback
    def set_dispatcher(self, dispatcher): self.dispatcher = dispatcher

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
        if not evidence.get("build_ok") or not evidence.get("artifact_compile_ok"):
            return 0.0
        status = evidence.get("verification_status")
        if status not in ("verified", "static_verified"):
            return 0.0
        if not evidence.get("artifact_digest"):
            return 0.0
        mode = evidence.get("evaluation_mode")
        if mode == "runtime":
            score = evidence.get("runtime_score")
        elif mode == "static":
            score = evidence.get("static_score")
        else:
            return 0.0
        return float(score) if score is not None else 0.0

    async def _governance_allows_promotion(self, genome: Genome) -> bool:
        """Production promotion requires a durable governance decision.

        Evaluation evidence proves the artifact; governance proves that the
        candidate is authorized to cross the promotion boundary. Development
        and test environments may exercise the engine without a configured
        council, but production cannot bypass this check.
        """
        if not get_settings().GOVERNANCE_ENFORCEMENT_REQUIRED:
            return True
        governance = get_governance()
        state = await governance.materialize_candidate(genome.genome_id)
        if state.current_state not in {
            "certified", "selected", "deployed", "operating"
        }:
            return False
        decision = state.latest_decision()
        return bool(
            decision
            and decision.verdict == "approve"
            and decision.authorizesTransition
        )

    async def run_async(self, generations: int = 10, population_size: int = 10, use_docker: bool = True, seed: Optional[int] = None) -> dict:
        if generations < 1 or population_size < 2: raise ValueError("generations must be >= 1 and population_size must be >= 2")
        run_id = str(uuid.uuid4())
        lease_token = acquire_control_plane_lease(owner_run_id=run_id)
        previous_state = random.getstate()
        evaluation_mode = "runtime" if use_docker and get_backend(self.target.backend_id).runtime_supported else "static"
        if seed is not None: random.seed(seed)
        db = SessionLocal()
        try:
            db.add(EvolutionRun(
                run_id=run_id, status="running", total_generations=generations,
                history=self._run_metadata(
                    phase="starting", evaluation_mode=evaluation_mode,
                    backend_id=self.target.backend_id, seed=seed,
                ),
            ))
            db.commit()
        finally: db.close()
        try:
            await self._emit_update({"type":"evolution_start","run_id":run_id,"generations":generations,"population_size":population_size,"evaluation_mode":evaluation_mode,"backend_id":self.target.backend_id,"seed":seed}, run_id=run_id)
            population = Population(size=population_size); history = []; best_genome = None; best_evidence = None; best_fitness = float("-inf"); output_path = None
            for gen in range(generations):
                await self._emit_update({"type":"generation_start","run_id":run_id,"generation":gen+1,"total_generations":generations,"backend_id":self.target.backend_id}, run_id=run_id, generation=gen+1)
                fitness_scores = []; genomes_to_save = []
                for genome in population.individuals:
                    evidence = await evaluate_candidate_async(genome, use_docker=use_docker, target=self.target)
                    heartbeat_control_plane_lease(lease_token)
                    fitness = self._fitness_from_evidence(evidence)
                    fitness_scores.append(fitness)
                    payload = genome.encode(); payload["lineage"] = self._lineage_payload(genome); payload["evaluation"] = evidence; payload["provenance"] = {"run_id": run_id, "generation": gen + 1, "seed": seed, "evaluation_mode": evidence["evaluation_mode"], "backend_id": self.target.backend_id, "artifact_digest": evidence.get("artifact_digest")}
                    stored_payload = dict(payload)
                    stored_evaluation = dict(evidence)
                    stored_evaluation.pop("artifact_path", None)
                    stored_payload["evaluation"] = stored_evaluation
                    genomes_to_save.append({"genome_data":stored_payload,"fitness_score":fitness,"generation":gen+1})
                    if evidence.get("verification_status") in ("verified", "static_verified") and fitness > 0.0 and fitness > best_fitness:
                        best_fitness, best_genome, best_evidence = fitness, genome, evidence
                        await self._emit_update({"type":"new_best","run_id":run_id,"generation":gen+1,"fitness":fitness,"genome":payload}, run_id=run_id, generation=gen+1)
                db = SessionLocal()
                try: db.add_all([GenomeRecord(**item) for item in genomes_to_save]); db.commit()
                except Exception: db.rollback(); logger.error("Error saving genomes", exc_info=True); raise
                finally: db.close()
                avg_fitness = sum(fitness_scores) / len(fitness_scores)
                history.append({"generation":gen+1,"scores":fitness_scores,"best_score":max(fitness_scores),"avg_score":avg_fitness})
                db = SessionLocal()
                try:
                    record = db.query(EvolutionRun).filter(EvolutionRun.run_id == run_id).first()
                    if record:
                        record.history = self._run_metadata(
                            phase="evaluating", evaluation_mode=evaluation_mode,
                            backend_id=self.target.backend_id, seed=seed,
                            generation=gen + 1,
                            best_fitness=0.0 if best_fitness == float("-inf") else best_fitness,
                            best_artifact_digest=best_evidence.get("artifact_digest") if best_evidence else None,
                        ) | {"generations": history}
                        db.commit()
                finally:
                    db.close()
                await self._emit_update({"type":"generation_complete","run_id":run_id,"generation":gen+1,"best_score":max(fitness_scores),"avg_score":avg_fitness,"fitness_scores":fitness_scores}, run_id=run_id, generation=gen+1)
                await asyncio.sleep(0)
                parents = population.select_parents(fitness_scores, num_parents=2); new_population = parents.copy()
                while len(new_population) < population_size: new_population.append(mutate(crossover(parents[0], parents[1]), mutation_rate=0.2))
                population.replace(new_population)
            build_error = None
            promotion_status = "not_attempted"
            if best_genome and best_evidence:
                try:
                    if best_evidence.get("verification_status") not in ("verified", "static_verified"):
                        raise ValueError("best candidate is not verified")
                    if not await self._governance_allows_promotion(best_genome):
                        raise ValueError(
                            "governance promotion gate denied: candidate lacks an approving "
                            "decision at certified/selected lifecycle state"
                        )
                    output_path = promote_verified_artifact(best_evidence["artifact_path"], "output/generated_api", expected_digest=best_evidence["artifact_digest"])
                    promotion_status = "published"
                except (KeyError, ValueError) as exc:
                    output_path = None
                    build_error = f"verified artifact promotion failed: {exc}"
                    promotion_status = "failed"
                    logger.error("Verified artifact promotion failed: %s", exc)
                await self._emit_update(
                    {"type": "building_best", "run_id": run_id,
                     "output_path": output_path,
                     "artifact_digest": best_evidence.get("artifact_digest")},
                    run_id=run_id,
                )
            elif best_genome is None:
                build_error = "no candidate could be lowered by the selected backend"
                promotion_status = "failed"
            result = {"run_id":run_id,"best_genome":best_genome.encode() if best_genome and not build_error else None,"best_fitness":best_fitness if best_genome and not build_error else 0.0,"production_readiness":self.production_analyzer.analyze(best_genome) if best_genome and not build_error else None,"history":history,"output_path":output_path,"build_error":build_error,"total_generations":generations,"evaluation_mode":evaluation_mode,"backend_id":self.target.backend_id,"seed":seed}
            db = SessionLocal()
            try:
                record = db.query(EvolutionRun).filter(EvolutionRun.run_id == run_id).first()
                if record:
                    record.status="failed" if build_error else "completed"
                    record.best_fitness=result["best_fitness"]
                    record.best_genome=result["best_genome"]
                    record.history = self._run_metadata(
                        phase="failed" if build_error else "completed",
                        evaluation_mode=evaluation_mode, backend_id=self.target.backend_id,
                        seed=seed, generation=generations, best_fitness=result["best_fitness"],
                        best_artifact_digest=best_evidence.get("artifact_digest") if best_evidence else None,
                        promotion_status=promotion_status, error=build_error,
                    ) | {"generations": history}
                    record.completed_at=datetime.utcnow()
                    db.commit()
                    if record.status == "completed" and not self._is_authoritative(record):
                        raise RuntimeError("completed evolution run failed durable authority invariant")
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
                if record:
                    record.status="failed"; record.completed_at=datetime.utcnow()
                    prior = record.history if isinstance(record.history, dict) else {}
                    record.history={**prior, "schema_version":1, "phase":"failed", "error":str(exc)}
                    db.commit()
            except Exception: db.rollback(); logger.error("Failed to persist evolution failure state", exc_info=True)
            finally: db.close()
            await self._emit_update({"type":"evolution_failed","run_id":run_id,"error":"Evolution run failed"}, run_id=run_id); raise
        finally:
            release_control_plane_lease(lease_token)
            if seed is not None: random.setstate(previous_state)

    @staticmethod
    def _run_metadata(*, phase: str, evaluation_mode: str, backend_id: str,
                      seed: Optional[int], generation: int = 0,
                      best_fitness: float = 0.0, best_artifact_digest: Optional[str] = None,
                      promotion_status: str = "not_attempted", error: Optional[str] = None) -> dict:
        return {
            "schema_version": 1, "phase": phase, "evaluation_mode": evaluation_mode,
            "backend_id": backend_id, "seed": seed, "generation": generation,
            "best_fitness": best_fitness, "best_artifact_digest": best_artifact_digest,
            "promotion_status": promotion_status, "error": error,
        }

    @staticmethod
    def _is_authoritative(record: EvolutionRun) -> bool:
        if record.status != "completed" or record.completed_at is None:
            return False
        metadata = record.history if isinstance(record.history, dict) else {}
        return (
            metadata.get("schema_version") == 1
            and metadata.get("phase") == "completed"
            and metadata.get("promotion_status") == "published"
            and bool(metadata.get("best_artifact_digest"))
            and bool(record.best_genome)
        )

    @staticmethod
    def recover_interrupted_runs() -> int:
        recovery_id = f"recovery:{uuid.uuid4()}"
        try:
            lease_token = acquire_control_plane_lease(
                owner_run_id=recovery_id,
                allow_stale_takeover=True,
            )
        except ControlPlaneBusy:
            return 0

        db = SessionLocal()
        recovered = 0
        try:
            runs = db.query(EvolutionRun).filter(EvolutionRun.status == "running").all()
            for record in runs:
                metadata = record.history if isinstance(record.history, dict) else {}
                record.status = "abandoned"
                record.completed_at = datetime.utcnow()
                record.history = {
                    **metadata,
                    "schema_version": 1,
                    "phase": "abandoned",
                    "promotion_status": metadata.get("promotion_status", "not_attempted"),
                    "recovery_reason": "stale control-plane lease; process restart or interrupted execution",
                }
                recovered += 1
            db.commit()
            return recovered
        except Exception:
            db.rollback()
            logger.exception("Failed to recover interrupted evolution runs")
            raise
        finally:
            db.close()
            release_control_plane_lease(lease_token)

    def run_synchronous(self, generations: int = 10, population_size: int = 10, use_docker: bool = False) -> dict:
        """Synchronous compatibility wrapper for the verified async evolution path."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self.run_async(
                    generations=generations,
                    population_size=population_size,
                    use_docker=use_docker,
                )
            )
        raise RuntimeError("run_synchronous cannot be called from an active event loop; use run_async")
