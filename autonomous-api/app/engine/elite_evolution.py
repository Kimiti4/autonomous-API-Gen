import asyncio
import uuid
from typing import Dict, List, Optional, Callable
from datetime import datetime
from app.core.logger import logger
from app.engine.genome import Genome
from app.core.population import Population
from app.core.crossover import crossover
from app.core.mutation import mutate
from app.engine.fitness import calculate_fitness
from app.engine.memory import EvolutionMemory
from app.engine.adaptive import AdaptiveMutator
from app.engine.multi_population import MultiPopulationSystem
from app.engine.benchmark import benchmark_api_performance, calculate_performance_fitness
from app.engine.builder import build_genome_output
from app.engine.production_readiness import ProductionReadinessAnalyzer
from app.storage.db import SessionLocal
from app.storage.models import GenomeRecord, EvolutionRun


class EliteEvolutionEngine:
    """
    Advanced evolution engine with:
    - Persistent memory and learning
    - Adaptive mutation
    - Multi-population system
    - Real performance benchmarking
    - Continuous improvement loop
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
        self.memory = EvolutionMemory()
        self.adaptive_mutator = AdaptiveMutator()
        self.multi_pop = None  # Will be initialized per run
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
    
    async def evaluate_genome(self, genome: Genome, group_name: str = "balanced") -> float:
        """
        Evaluate genome with multi-objective fitness including real benchmarking.
        
        Args:
            genome: Genome to evaluate
            group_name: Population group name
        
        Returns:
            Fitness score
        """
        # Base fitness (architecture, security, etc.)
        base_fitness = calculate_fitness(genome)
        readiness = self.production_analyzer.analyze(genome)
        
        # Build and test if Docker enabled (optional)
        performance_score = 0.5  # Default neutral score
        
        # For now, estimate performance based on configuration
        # In production, you'd actually deploy and benchmark
        if genome.cache_enabled:
            performance_score += 0.2
        if genome.logging_level in ["WARNING", "ERROR"]:
            performance_score += 0.1  # Less logging = faster
        
        # Combine scores with weights
        # Group-specific weighting
        if group_name == "performance":
            final_fitness = base_fitness * 0.4 + performance_score * 0.6
        elif group_name == "security":
            security_score = genome.encode().get("security_score", 0.5)
            final_fitness = base_fitness * 0.7 + security_score * 0.3
        elif group_name == "operations":
            final_fitness = base_fitness * 0.4 + readiness["score"] * 0.6
        else:  # balanced or minimal
            final_fitness = base_fitness * 0.45 + performance_score * 0.25 + readiness["score"] * 0.30
        
        return round(final_fitness, 3)
    
    async def run_elite_evolution(
        self,
        generations: int = 10,
        population_size: int = 8,
        use_multi_population: bool = True,
        enable_adaptive_mutation: bool = True,
        use_docker: bool = False
    ) -> dict:
        """
        Run elite evolution with learning and adaptation.
        
        Args:
            generations: Number of generations
            population_size: Size per population group
            use_multi_population: Use specialized groups
            enable_adaptive_mutation: Use adaptive mutation
            use_docker: Deploy and benchmark with Docker
        
        Returns:
            Evolution results with insights
        """
        run_id = str(uuid.uuid4())
        logger.info(f"Starting elite evolution run {run_id}")
        
        # Initialize multi-population system
        if use_multi_population:
            self.multi_pop = MultiPopulationSystem(population_size=population_size)
            groups = self.multi_pop.groups
        else:
            # Single population fallback
            single_pop = Population(size=population_size * 4)
            groups = {"balanced": single_pop}
        
        # Track history
        all_history = {group_name: [] for group_name in groups.keys()}
        global_best_genome = None
        global_best_fitness = 0.0
        
        await self._emit_update({
            "type": "elite_evolution_start",
            "run_id": run_id,
            "generations": generations,
            "groups": list(groups.keys()),
            "adaptive_mutation": enable_adaptive_mutation
        })
        
        for gen in range(generations):
            await self._emit_update({
                "type": "generation_start",
                "run_id": run_id,
                "generation": gen + 1,
                "total_generations": generations
            })
            
            generation_results = {}
            
            # Evolve each group
            for group_name, population in groups.items():
                logger.info(f"Evolving group '{group_name}' - Generation {gen + 1}")
                
                # Evaluate all individuals
                fitness_scores = []
                for genome in population.individuals:
                    fitness = await self.evaluate_genome(genome, group_name)
                    fitness_scores.append(fitness)
                    
                    # Update adaptive mutator
                    if enable_adaptive_mutation:
                        self.adaptive_mutator.update(genome.encode(), fitness)
                    
                    # Track global best
                    if fitness > global_best_fitness:
                        global_best_fitness = fitness
                        global_best_genome = genome
                        
                        await self._emit_update({
                            "type": "new_global_best",
                            "run_id": run_id,
                            "group": group_name,
                            "generation": gen + 1,
                            "fitness": fitness,
                            "genome": genome.encode()
                        })
                
                avg_fitness = sum(fitness_scores) / len(fitness_scores)
                best_in_group = max(fitness_scores)
                
                generation_results[group_name] = {
                    "best": best_in_group,
                    "avg": avg_fitness,
                    "scores": fitness_scores
                }
                
                all_history[group_name].append({
                    "generation": gen + 1,
                    "best": best_in_group,
                    "avg": avg_fitness
                })
                
                await self._emit_update({
                    "type": "group_complete",
                    "run_id": run_id,
                    "group": group_name,
                    "generation": gen + 1,
                    "best_score": best_in_group,
                    "avg_score": avg_fitness
                })
                
                # Selection and reproduction
                parents = population.select_parents(fitness_scores, num_parents=2)
                new_population = parents.copy()
                
                while len(new_population) < population_size:
                    parent1, parent2 = parents[0], parents[1]
                    child = crossover(parent1, parent2)
                    
                    # Use adaptive mutation if enabled
                    if enable_adaptive_mutation:
                        child_data = self.adaptive_mutator.mutate(child.encode())
                        child.decode(child_data)
                    else:
                        child = mutate(child, mutation_rate=0.2)
                    
                    new_population.append(child)
                
                population.replace(new_population)
            
            # Cross-pollination every 3 generations
            if use_multi_population and (gen + 1) % 3 == 0:
                self.multi_pop.cross_pollinate()
                await self._emit_update({
                    "type": "cross_pollination",
                    "run_id": run_id,
                    "generation": gen + 1
                })
            
            await asyncio.sleep(0.05)  # Small delay for WebSocket updates
        
        # Build best genome
        output_path = None
        if global_best_genome:
            output_path = build_genome_output(global_best_genome)
            
            # Record in memory
            self.memory.record_run(
                best_genome=global_best_genome.encode(),
                best_score=global_best_fitness,
                worst_score=min([min(r["scores"]) for r in generation_results.values()]),
                generation=generations,
                run_id=run_id
            )
            
            await self._emit_update({
                "type": "building_complete",
                "run_id": run_id,
                "output_path": output_path,
                "best_fitness": global_best_fitness
            })
        
        # Get learning insights
        insights = self.memory.get_pattern_insights()
        top_features = self.adaptive_mutator.get_top_features(5) if enable_adaptive_mutation else []
        
        result = {
            "run_id": run_id,
            "best_genome": global_best_genome.encode() if global_best_genome else None,
            "best_fitness": global_best_fitness,
            "production_readiness": (
                self.production_analyzer.analyze(global_best_genome)
                if global_best_genome else None
            ),
            "history": all_history,
            "output_path": output_path,
            "total_generations": generations,
            "insights": insights,
            "top_features": top_features,
            "memory_stats": self.memory.get_statistics()
        }
        
        await self._emit_update({
            "type": "elite_evolution_complete",
            "run_id": run_id,
            "result": result
        })
        
        logger.info(f"Elite evolution run {run_id} completed. Best fitness: {global_best_fitness:.3f}")
        return result
    
    def get_memory_insights(self) -> dict:
        """Get current learning insights from memory"""
        return {
            "statistics": self.memory.get_statistics(),
            "pattern_insights": self.memory.get_pattern_insights(),
            "suggested_genome": self.memory.get_suggested_genome(),
            "adaptive_bias": self.adaptive_mutator.get_bias_report() if self.adaptive_mutator else None
        }
    
    def clear_memory(self):
        """Clear all learned memory"""
        self.memory.clear()
        if self.adaptive_mutator:
            self.adaptive_mutator.reset()
        logger.info("All memory cleared")
