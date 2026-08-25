"""34.2 Fitness -- independently observable, no composite."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class ArchitectureFitness:
    throughput: float; latency: float; availability: float; failure_recovery: float; resource_usage: float; cost: float; deployment_complexity: float; data_consistency: float; operational_complexity: float
    def has_composite(self) -> bool: return False
    def dimensions(self): return ("throughput","latency","availability","failure_recovery","resource_usage","cost","deployment_complexity","data_consistency","operational_complexity")

def measure_fitness(observation: dict) -> ArchitectureFitness:
    # Each dimension independently measured from observation, no averaging
    return ArchitectureFitness(
        throughput=observation.get("throughput", 0),
        latency=observation.get("latency", 0),
        availability=observation.get("availability", 0),
        failure_recovery=observation.get("failure_recovery", 0),
        resource_usage=observation.get("resource_usage", 0),
        cost=observation.get("cost", 0),
        deployment_complexity=observation.get("deployment_complexity", 0),
        data_consistency=observation.get("data_consistency", 0),
        operational_complexity=observation.get("operational_complexity", 0),
    )
