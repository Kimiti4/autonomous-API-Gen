import asyncio
import uuid
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime
from app.core.logger import logger
from app.engine.genome import Genome
from app.core.population import Population
from app.core.crossover import crossover
from app.core.mutation import mutate
from app.engine.fitness import calculate_fitness
from app.engine.builder import build_genome_output
from app.engine.production_readiness import ProductionReadinessAnalyzer
from app.storage.db import SessionLocal
from app.storage.models import GenomeRecord, EvolutionRun


class EvolutionEngine:
    """
    Main evolution engine that runs genetic algorithm to evolve API architectures.
    Supports both synchronous and asynchronous execution with real-time updates.
    """
    
    # Legacy bare-dict type → contract EventType mapping (GAP-01).
    _EVENT_TYPE_MAP = {
        "evolution_start": "evolution.stage_changed",
        "generation_start": "evolution.stage_changed",
        "new_best": "candidate.promoted",
        "generation_complete": "fitness.evaluated",
        "building_best": "evolution.stage_changed",
        "docker_test": "evolution.stage_changed",
        "evolution_complete": "evolution.stage_changed",
    }

    def __init__(self):
        self.docker_runner = None  # Will be initialized if Docker is available
        self.websocket_callback: Optional[Callable] = None
        self.dispatcher = None  # EventDispatcher (envelope emission)
        self.production_analyzer = ProductionReadinessAnalyzer()
    
    def set_websocket_callback(self, callback: Callable):
        """Set callback for real-time WebSocket updates"""
        self.websocket_callback = callback

    def set_dispatcher(self, dispatcher):
        """Inject the observation EventDispatcher (envelope emission)."""
        self.dispatcher = dispatcher
    
    async def _emit_update(self, data: dict, *, run_id: str = "global",
                           generation: int = 0):
        """Emit update via WebSocket callback AND as an enveloped event."""
        if self.websocket_callback:
            try:
                await self.websocket_callback(data)
            except Exception as e:
                logger.error(f"WebSocket emit error: {str(e)}")

        if self.dispatcher is not None:
            event_type = self._EVENT_TYPE_MAP.get(
                data.get("type", ""), "evolution.stage_changed"
            )
            try:
                await self.dispatcher.emit(
                    stream_id=run_id,
                    event_type=event_type,
                    payload=data,
                    correlation_id=run_id,
                    generation=generation,
                )
            except Exception:
                logger.error("Envelope emission failed", exc_info=True)
    
    def run_synchronous(self, generations: int = 10, population_size: int = 10, 
                       use_docker: bool = False) -> dict:
        """
        Run evolution synchronously (for testing/simple use).
        
        Args:
            generations: Number of generations to evolve
            population_size: Size of population
            use_docker: Whether to build and test with Docker
        
        Returns:
            Dictionary with best genome, history, and output path
        """
        logger.info(f"Starting synchronous evolution: {generations} generations, pop size {population_size}")
        
        # Initialize population
        population = Population(size=population_size)
        history = []
        best_genome = None
        best_fitness = 0.0
        output_path = None
        
        for gen in range(generations):
            logger.info(f"Generation {gen + 1}/{generations}")
            
            # Calculate fitness for all individuals
            fitness_scores = []
            for genome in population.individuals:
                fitness = calculate_fitness(genome)
                fitness_scores.append(fitness)
                
                # Track best
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_genome = genome
            
            history.append({
                "generation": gen + 1,
                "scores": fitness_scores,
                "best_score": max(fitness_scores),
                "avg_score": sum(fitness_scores) / len(fitness_scores)
            })
            
            logger.info(f"  Best fitness: {max(fitness_scores):.3f}, Avg: {sum(fitness_scores)/len(fitness_scores):.3f}")
            
            # Selection
            parents = population.select_parents(fitness_scores, num_parents=2)
            
            # Create new population
            new_population = parents.copy()
            
            while len(new_population) < population_size:
                # Crossover
                parent1, parent2 = parents[0], parents[1]
                child = crossover(parent1, parent2)
                
                # Mutation
                child = mutate(child, mutation_rate=0.2)
                
                new_population.append(child)
            
            population.replace(new_population)
        
        # Build best genome
        if best_genome:
            output_path = build_genome_output(best_genome)
            logger.info(f"Best genome built at: {output_path}")
            
            # Optionally test with Docker
            if use_docker and self.docker_runner:
                success, port, error = self.docker_runner.build_and_run(output_path)
                if success:
                    api_working = self.docker_runner.test_api(port)
                    logger.info(f"Docker test: {'PASSED' if api_working else 'FAILED'}")
        
        return {
            "best_genome": best_genome.encode() if best_genome else None,
            "best_fitness": best_fitness,
            "production_readiness": (
                self.production_analyzer.analyze(best_genome)
                if best_genome else None
            ),
            "history": history,
            "output_path": output_path,
            "total_generations": generations
        }
    
    async def run_async(self, generations: int = 10, population_size: int = 10,
                       use_docker: bool = False) -> dict:
        """
        Run evolution asynchronously with real-time WebSocket updates.
        
        Args:
            generations: Number of generations to evolve
            population_size: Size of population
            use_docker: Whether to build and test with Docker
        
        Returns:
            Dictionary with evolution results
        """
        run_id = str(uuid.uuid4())
        logger.info(f"Starting async evolution run {run_id}")
        
        # Create database record
        db = SessionLocal()
        try:
            evolution_record = EvolutionRun(
                run_id=run_id,
                status="running",
                total_generations=generations
            )
            db.add(evolution_record)
            db.commit()
        finally:
            db.close()
        
        # Emit start event
        await self._emit_update({
            "type": "evolution_start",
            "run_id": run_id,
            "generations": generations,
            "population_size": population_size
        }, run_id=run_id)
        
        # Initialize population
        population = Population(size=population_size)
        history = []
        best_genome = None
        best_fitness = 0.0
        output_path = None
        
        for gen in range(generations):
            await self._emit_update({
                "type": "generation_start",
                "run_id": run_id,
                "generation": gen + 1,
                "total_generations": generations
            }, run_id=run_id, generation=gen + 1)
            
            # Calculate fitness
            fitness_scores = []
            genomes_to_save = []  # Batch save for performance
            
            for idx, genome in enumerate(population.individuals):
                fitness = calculate_fitness(genome)
                fitness_scores.append(fitness)
                
                # Collect genomes for batch insert
                genomes_to_save.append({
                    "genome_data": genome.encode(),
                    "fitness_score": fitness,
                    "generation": gen + 1
                })
                
                # Track best
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_genome = genome
                    
                    await self._emit_update({
                        "type": "new_best",
                        "run_id": run_id,
                        "generation": gen + 1,
                        "fitness": fitness,
                        "genome": genome.encode()
                    }, run_id=run_id, generation=gen + 1)
            
            # Batch save genomes to database (much faster than individual saves)
            db = SessionLocal()
            try:
                for genome_data in genomes_to_save:
                    genome_record = GenomeRecord(**genome_data)
                    db.add(genome_record)
                db.commit()
            except Exception as e:
                logger.error(f"Error saving genomes: {str(e)}")
                db.rollback()
            finally:
                db.close()

            avg_fitness = sum(fitness_scores) / len(fitness_scores)
            history.append({
                "generation": gen + 1,
                "scores": fitness_scores,
                "best_score": max(fitness_scores),
                "avg_score": avg_fitness
            })
            
            await self._emit_update({
                "type": "generation_complete",
                "run_id": run_id,
                "generation": gen + 1,
                "best_score": max(fitness_scores),
                "avg_score": avg_fitness,
                "fitness_scores": fitness_scores
            }, run_id=run_id, generation=gen + 1)
            
            # Small delay to allow WebSocket updates
            await asyncio.sleep(0.1)
            
            # Selection
            parents = population.select_parents(fitness_scores, num_parents=2)
            
            # Create new population
            new_population = parents.copy()
            
            while len(new_population) < population_size:
                parent1, parent2 = parents[0], parents[1]
                child = crossover(parent1, parent2)
                child = mutate(child, mutation_rate=0.2)
                new_population.append(child)
            
            population.replace(new_population)
        
        # Build best genome
        if best_genome:
            output_path = build_genome_output(best_genome)
            
            await self._emit_update({
                "type": "building_best",
                "run_id": run_id,
                "output_path": output_path
            }, run_id=run_id)
            
            # Test with Docker if enabled
            docker_result = None
            if use_docker and self.docker_runner:
                success, port, error = self.docker_runner.build_and_run(output_path)
                if success:
                    api_working = self.docker_runner.test_api(port)
                    docker_result = {
                        "success": success,
                        "port": port,
                        "api_working": api_working
                    }
                    
                    await self._emit_update({
                        "type": "docker_test",
                        "run_id": run_id,
                        "result": docker_result
                    }, run_id=run_id)
        
        # Update database record
        db = SessionLocal()
        try:
            evolution_record.status = "completed"
            evolution_record.best_fitness = best_fitness
            evolution_record.best_genome = best_genome.encode() if best_genome else None
            evolution_record.history = history
            evolution_record.completed_at = datetime.utcnow()
            db.commit()
        finally:
            db.close()
        
        result = {
            "run_id": run_id,
            "best_genome": best_genome.encode() if best_genome else None,
            "best_fitness": best_fitness,
            "production_readiness": (
                self.production_analyzer.analyze(best_genome)
                if best_genome else None
            ),
            "history": history,
            "output_path": output_path,
            "total_generations": generations,
            "docker_result": docker_result if use_docker else None
        }
        
        await self._emit_update({
            "type": "evolution_complete",
            "run_id": run_id,
            "result": result
        }, run_id=run_id)
        
        logger.info(f"Evolution run {run_id} completed")
        return result
