import asyncio
import uuid
from typing import Callable, Optional
from datetime import datetime

from app.core.logger import logger
from app.engine.genome import Genome
from app.core.population import Population
from app.core.crossover import crossover
from app.core.mutation import mutate
from app.engine.fitness import calculate_fitness
from app.engine.builder import build_genome_output
from app.engine.candidate_evaluator import evaluate_candidate_async
from app.engine.production_readiness import ProductionReadinessAnalyzer
from app.storage.db import SessionLocal
from app.storage.models import GenomeRecord, EvolutionRun


class EvolutionEngine:
    """Main genetic evolution engine with durable lifecycle state."""

    _EVENT_TYPE_MAP = {
        "evolution_start": "evolution.stage_changed",
        "generation_start": "evolution.stage_changed",
        "new_best": "candidate.promoted",
        "generation_complete": "fitness.evaluated",
        "building_best": "evolution.stage_changed",
        "docker_test": "evolution.stage_changed",
        "evolution_complete": "evolution.stage_changed",
        "evolution_failed": "evolution.stage_changed",
    }

    def __init__(self):
        self.docker_runner = None
        self.websocket_callback: Optional[Callable] = None
        self.dispatcher = None
        self.production_analyzer = ProductionReadinessAnalyzer()

    def set_websocket_callback(self, callback: Callable):
        self.websocket_callback = callback

    def set_dispatcher(self, dispatcher):
        self.dispatcher = dispatcher

    async def _emit_update(self, data: dict, *, run_id: str = "global", generation: int = 0):
        if self.websocket_callback:
            try: await self.websocket_callback(data)
            except Exception: logger.error("WebSocket emit error", exc_info=True)
        if self.dispatcher is not None:
            event_type = self._EVENT_TYPE_MAP.get(data.get("type", ""), "evolution.stage_changed")
            try:
                await self.dispatcher.emit(stream_id=run_id, event_type=event_type, payload=data, correlation_id=run_id, generation=generation)
            except Exception: logger.error("Envelope emission failed", exc_info=True)

    @staticmethod
    def _lineage_payload(genome: Genome) -> dict:
        return {"genome_id": genome.genome_id, "lineage": getattr(genome, "lineage", {})}

    def run_synchronous(self, generations: int = 10, population_size: int = 10, use_docker: bool = False) -> dict:
        if generations < 1 or population_size < 2: raise ValueError("generations must be >= 1 and population_size must be >= 2")
        population = Population(size=population_size); history = []; best_genome = None; best_fitness = float("-inf"); output_path = None
        for gen in range(generations):
            fitness_scores = [calculate_fitness(g) for g in population.individuals]
            for fitness, genome in zip(fitness_scores, population.individuals):
                if fitness > best_fitness: best_fitness, best_genome = fitness, genome
            history.append({"generation": gen + 1, "scores": fitness_scores, "best_score": max(fitness_scores), "avg_score": sum(fitness_scores) / len(fitness_scores)})
            parents = population.select_parents(fitness_scores, num_parents=2); new_population = parents.copy()
            while len(new_population) < population_size: new_population.append(mutate(crossover(parents[0], parents[1]), mutation_rate=0.2))
            population.replace(new_population)
        if best_genome: output_path = build_genome_output(best_genome)
        return {"best_genome": best_genome.encode() if best_genome else None, "best_fitness": best_fitness if best_genome else 0.0, "production_readiness": self.production_analyzer.analyze(best_genome) if best_genome else None, "history": history, "output_path": output_path, "total_generations": generations}

    async def run_async(self, generations: int = 10, population_size: int = 10, use_docker: bool = False) -> dict:
        if generations < 1 or population_size < 2: raise ValueError("generations must be >= 1 and population_size must be >= 2")
        run_id = str(uuid.uuid4())
        db = SessionLocal()
        try:
            db.add(EvolutionRun(run_id=run_id, status="running", total_generations=generations)); db.commit()
        finally: db.close()
        try:
            await self._emit_update({"type": "evolution_start", "run_id": run_id, "generations": generations, "population_size": population_size}, run_id=run_id)
            population = Population(size=population_size); history = []; best_genome = None; best_fitness = float("-inf"); output_path = None; docker_result = None
            for gen in range(generations):
                await self._emit_update({"type": "generation_start", "run_id": run_id, "generation": gen + 1, "total_generations": generations}, run_id=run_id, generation=gen + 1)
                fitness_scores = []; genomes_to_save = []
                for genome in population.individuals:
                    evidence = await evaluate_candidate_async(genome, use_docker=use_docker)
                    fitness = evidence["runtime_score"] if evidence["evaluation_mode"] == "runtime" else evidence["static_score"]
                    fitness_scores.append(fitness)
                    payload = genome.encode(); payload["lineage"] = self._lineage_payload(genome); payload["evaluation"] = evidence
                    genomes_to_save.append({"genome_data": payload, "fitness_score": fitness, "generation": gen + 1})
                    if fitness > best_fitness:
                        best_fitness, best_genome = fitness, genome
                        await self._emit_update({"type": "new_best", "run_id": run_id, "generation": gen + 1, "fitness": fitness, "genome": payload}, run_id=run_id, generation=gen + 1)
                db = SessionLocal()
                try: db.add_all([GenomeRecord(**item) for item in genomes_to_save]); db.commit()
                except Exception: db.rollback(); logger.error("Error saving genomes", exc_info=True); raise
                finally: db.close()
                avg_fitness = sum(fitness_scores) / len(fitness_scores)
                history.append({"generation": gen + 1, "scores": fitness_scores, "best_score": max(fitness_scores), "avg_score": avg_fitness})
                await self._emit_update({"type": "generation_complete", "run_id": run_id, "generation": gen + 1, "best_score": max(fitness_scores), "avg_score": avg_fitness, "fitness_scores": fitness_scores}, run_id=run_id, generation=gen + 1)
                await asyncio.sleep(0)
                parents = population.select_parents(fitness_scores, num_parents=2); new_population = parents.copy()
                while len(new_population) < population_size: new_population.append(mutate(crossover(parents[0], parents[1]), mutation_rate=0.2))
                population.replace(new_population)
            if best_genome:
                output_path = build_genome_output(best_genome)
                await self._emit_update({"type": "building_best", "run_id": run_id, "output_path": output_path}, run_id=run_id)
            result = {"run_id": run_id, "best_genome": best_genome.encode() if best_genome else None, "best_fitness": best_fitness if best_genome else 0.0, "production_readiness": self.production_analyzer.analyze(best_genome) if best_genome else None, "history": history, "output_path": output_path, "total_generations": generations, "docker_result": docker_result}
            db = SessionLocal()
            try:
                record = db.query(EvolutionRun).filter(EvolutionRun.run_id == run_id).first()
                if record: record.status = "completed"; record.best_fitness = result["best_fitness"]; record.best_genome = result["best_genome"]; record.history = history; record.completed_at = datetime.utcnow(); db.commit()
            finally: db.close()
            await self._emit_update({"type": "evolution_complete", "run_id": run_id, "result": result}, run_id=run_id)
            return result
        except Exception as exc:
            logger.error("Evolution run failed", exc_info=True)
            db = SessionLocal()
            try:
                record = db.query(EvolutionRun).filter(EvolutionRun.run_id == run_id).first()
                if record: record.status = "failed"; record.completed_at = datetime.utcnow(); record.history = {"error": str(exc)}; db.commit()
            except Exception: db.rollback(); logger.error("Failed to persist evolution failure state", exc_info=True)
            finally: db.close()
            await self._emit_update({"type": "evolution_failed", "run_id": run_id, "error": "Evolution run failed"}, run_id=run_id)
            raise
