import asyncio
import uuid
import random
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
    """Advanced evolution engine with persistent memory, adaptation and multi-population search."""
    _EVENT_TYPE_MAP = {"evolution_start":"evolution.stage_changed","generation_start":"evolution.stage_changed","new_best":"candidate.promoted","generation_complete":"fitness.evaluated","building_best":"evolution.stage_changed","docker_test":"evolution.stage_changed","evolution_complete":"evolution.stage_changed"}
    def __init__(self):
        self.memory=EvolutionMemory(); self.adaptive_mutator=AdaptiveMutator(); self.multi_pop=None; self.websocket_callback:Optional[Callable]=None; self.dispatcher=None; self.production_analyzer=ProductionReadinessAnalyzer()
    def set_websocket_callback(self, callback: Callable): self.websocket_callback=callback
    def set_dispatcher(self, dispatcher): self.dispatcher=dispatcher
    async def _emit_update(self, data:dict, *, run_id:str="global", generation:int=0):
        if self.websocket_callback:
            try: await self.websocket_callback(data)
            except Exception: logger.error("WebSocket emit error", exc_info=True)
        if self.dispatcher is not None:
            event_type=self._EVENT_TYPE_MAP.get(data.get("type",""),"evolution.stage_changed")
            try: await self.dispatcher.emit(stream_id=run_id,event_type=event_type,payload=data,correlation_id=run_id,generation=generation)
            except Exception: logger.error("Envelope emission failed",exc_info=True)
    async def evaluate_genome(self, genome:Genome, group_name:str="balanced") -> float:
        base_fitness=calculate_fitness(genome); readiness=self.production_analyzer.analyze(genome); performance_score=0.5
        if genome.cache_enabled: performance_score+=0.2
        if genome.logging_level in ["WARNING","ERROR"]: performance_score+=0.1
        if group_name=="performance": final_fitness=base_fitness*.4+performance_score*.6
        elif group_name=="security": final_fitness=base_fitness*.7+genome.encode().get("security_score",.5)*.3
        elif group_name=="operations": final_fitness=base_fitness*.4+readiness["score"]*.6
        else: final_fitness=base_fitness*.45+performance_score*.25+readiness["score"]*.30
        return round(final_fitness,3)
    async def run_elite_evolution(self,generations:int=10,population_size:int=8,use_multi_population:bool=True,enable_adaptive_mutation:bool=True,use_docker:bool=False,seed:Optional[int]=None)->dict:
        run_id=str(uuid.uuid4()); logger.info(f"Starting elite evolution run {run_id}"); previous_state=random.getstate()
        if seed is not None: random.seed(seed)
        try:
            if use_multi_population: self.multi_pop=MultiPopulationSystem(population_size=population_size); groups=self.multi_pop.groups
            else: groups={"balanced":Population(size=population_size*4)}
            all_history={g:[] for g in groups}; global_best_genome=None; global_best_fitness=float("-inf")
            await self._emit_update({"type":"elite_evolution_start","run_id":run_id,"generations":generations,"groups":list(groups.keys()),"adaptive_mutation":enable_adaptive_mutation,"seed":seed,"evaluation_mode":"static"},run_id=run_id)
            for gen in range(generations):
                for group_name,population in groups.items():
                    fitness_scores=[]
                    for genome in population.individuals:
                        fitness=await self.evaluate_genome(genome,group_name); fitness_scores.append(fitness)
                        if enable_adaptive_mutation: self.adaptive_mutator.update(genome.encode(),fitness)
                        if fitness>global_best_fitness: global_best_fitness=fitness; global_best_genome=genome
                    best_in_group=max(fitness_scores); avg_fitness=sum(fitness_scores)/len(fitness_scores); all_history[group_name].append({"generation":gen+1,"best":best_in_group,"avg":avg_fitness})
                    parents=population.select_parents(fitness_scores,num_parents=2); new_population=parents.copy()
                    while len(new_population)<population_size:
                        child=crossover(parents[0],parents[1])
                        if enable_adaptive_mutation: child.decode(self.adaptive_mutator.mutate(child.encode()))
                        else: child=mutate(child,mutation_rate=.2)
                        new_population.append(child)
                    population.replace(new_population)
                if use_multi_population and (gen+1)%3==0: self.multi_pop.cross_pollinate()
                await asyncio.sleep(.05)
            output_path=build_genome_output(global_best_genome) if global_best_genome else None
            return {"run_id":run_id,"best_genome":global_best_genome.encode() if global_best_genome else None,"best_fitness":global_best_fitness if global_best_genome else 0.0,"production_readiness":self.production_analyzer.analyze(global_best_genome) if global_best_genome else None,"history":all_history,"output_path":output_path,"total_generations":generations,"insights":self.memory.get_pattern_insights(),"top_features":self.adaptive_mutator.get_top_features(5) if enable_adaptive_mutation else [],"memory_stats":self.memory.get_statistics(),"seed":seed,"evaluation_mode":"static"}
        finally:
            if seed is not None: random.setstate(previous_state)
    def get_memory_insights(self)->dict: return {"statistics":self.memory.get_statistics(),"pattern_insights":self.memory.get_pattern_insights(),"suggested_genome":self.memory.get_suggested_genome(),"adaptive_bias":self.adaptive_mutator.get_bias_report() if self.adaptive_mutator else None}
    def clear_memory(self): self.memory.clear(); self.adaptive_mutator.reset(); logger.info("All memory cleared")
