"""
Platform Genome.

Encodes all tunable platform parameters as an immutable, versioned genome.
The Platform Genome is the meta-evolutionary equivalent of the ISR.

Constitutional constraint: The Platform Genome NEVER encodes constitutional
parameters. Constitutional layers are immutable and cannot be evolved.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, unique
from typing import Any, Optional


@unique
class ParameterCategory(str, Enum):
    EVOLUTION = "evolution"
    COMPILER = "compiler"
    VERIFICATION = "verification"
    DEPLOYMENT = "deployment"
    SCHEDULING = "scheduling"
    KNOWLEDGE = "knowledge"
    AGENT = "agent"
    PERFORMANCE = "performance"


@unique
class ParameterType(str, Enum):
    FLOAT = "float"
    INT = "int"
    BOOL = "bool"
    STRING = "string"
    LIST = "list"
    DICT = "dict"


@dataclass(frozen=True)
class GenomeParameter:
    id: str
    name: str
    category: ParameterCategory
    param_type: ParameterType
    value: Any
    description: str = ""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: tuple[Any, ...] = ()
    sensitivity: float = 0.5
    mutation_rate: float = 0.1
    locked: bool = False

    def is_within_bounds(self, new_value: Any) -> bool:
        if self.param_type in (ParameterType.FLOAT, ParameterType.INT):
            if self.min_value is not None and new_value < self.min_value:
                return False
            if self.max_value is not None and new_value > self.max_value:
                return False
        if self.allowed_values and new_value not in self.allowed_values:
            return False
        return True

    def with_value(self, new_value: Any) -> "GenomeParameter":
        if not self.is_within_bounds(new_value):
            raise ValueError(
                f"Value {new_value} out of bounds for parameter '{self.name}' "
                f"[{self.min_value}, {self.max_value}]"
            )
        return GenomeParameter(
            id=self.id, name=self.name, category=self.category,
            param_type=self.param_type, value=new_value,
            description=self.description,
            min_value=self.min_value, max_value=self.max_value,
            allowed_values=self.allowed_values,
            sensitivity=self.sensitivity, mutation_rate=self.mutation_rate,
            locked=self.locked,
        )


@dataclass(frozen=True)
class PlatformGenome:
    genome_id: str = ""
    version: int = 1
    parent_hash: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    mutation_description: str = ""
    parameters: dict[str, GenomeParameter] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        canonical = json.dumps(
            {pid: p.value for pid, p in sorted(self.parameters.items())},
            sort_keys=True, separators=(",", ":"), default=str,
        )
        return hashlib.sha256(canonical.encode()).hexdigest()

    def get_parameter(self, param_id: str) -> Optional[GenomeParameter]:
        return self.parameters.get(param_id)

    def get_by_category(self, category: ParameterCategory) -> list[GenomeParameter]:
        return [p for p in self.parameters.values() if p.category == category]

    def get_mutable_parameters(self) -> list[GenomeParameter]:
        return [p for p in self.parameters.values() if not p.locked]

    def get_locked_parameters(self) -> list[GenomeParameter]:
        return [p for p in self.parameters.values() if p.locked]

    def with_parameter(self, param_id: str, new_value: Any) -> "PlatformGenome":
        param = self.parameters.get(param_id)
        if param is None:
            raise ValueError(f"Parameter '{param_id}' not found")
        if param.locked:
            raise ValueError(f"Parameter '{param_id}' is locked (constitutional boundary)")
        new_param = param.with_value(new_value)
        new_parameters = dict(self.parameters)
        new_parameters[param_id] = new_param
        return PlatformGenome(
            genome_id=self.genome_id, version=self.version + 1,
            parent_hash=self.content_hash,
            mutation_description=f"Changed {param.name} from {param.value} to {new_value}",
            parameters=new_parameters, metadata=self.metadata,
        )

    def with_parameters(self, changes: dict[str, Any]) -> "PlatformGenome":
        new_parameters = dict(self.parameters)
        descriptions: list[str] = []
        for param_id, new_value in changes.items():
            param = self.parameters.get(param_id)
            if param is None:
                raise ValueError(f"Parameter '{param_id}' not found")
            if param.locked:
                raise ValueError(f"Parameter '{param_id}' is locked (constitutional boundary)")
            new_parameters[param_id] = param.with_value(new_value)
            descriptions.append(f"{param.name}: {param.value} \u2192 {new_value}")
        return PlatformGenome(
            genome_id=self.genome_id, version=self.version + 1,
            parent_hash=self.content_hash,
            mutation_description="; ".join(descriptions),
            parameters=new_parameters, metadata=self.metadata,
        )

    @property
    def parameter_count(self) -> int:
        return len(self.parameters)

    @property
    def mutable_count(self) -> int:
        return len(self.get_mutable_parameters())

    @property
    def locked_count(self) -> int:
        return len(self.get_locked_parameters())


def create_default_genome() -> PlatformGenome:
    parameters: dict[str, GenomeParameter] = {}

    # Evolution Parameters
    parameters["evo.mutation_rate"] = GenomeParameter(
        id="evo.mutation_rate", name="Mutation Rate",
        category=ParameterCategory.EVOLUTION, param_type=ParameterType.FLOAT,
        value=0.3,
        description="Probability of mutation per individual per generation",
        min_value=0.01, max_value=0.9, sensitivity=0.7, mutation_rate=0.1,
    )
    parameters["evo.crossover_rate"] = GenomeParameter(
        id="evo.crossover_rate", name="Crossover Rate",
        category=ParameterCategory.EVOLUTION, param_type=ParameterType.FLOAT,
        value=0.2,
        description="Probability of crossover per pair",
        min_value=0.0, max_value=0.8, sensitivity=0.5, mutation_rate=0.1,
    )
    parameters["evo.population_size"] = GenomeParameter(
        id="evo.population_size", name="Population Size",
        category=ParameterCategory.EVOLUTION, param_type=ParameterType.INT,
        value=50,
        description="Number of individuals in the population",
        min_value=10, max_value=500, sensitivity=0.6, mutation_rate=0.05,
    )
    parameters["evo.elite_count"] = GenomeParameter(
        id="evo.elite_count", name="Elite Count",
        category=ParameterCategory.EVOLUTION, param_type=ParameterType.INT,
        value=5,
        description="Number of elite individuals preserved",
        min_value=1, max_value=20, sensitivity=0.4, mutation_rate=0.05,
    )
    parameters["evo.tournament_size"] = GenomeParameter(
        id="evo.tournament_size", name="Tournament Size",
        category=ParameterCategory.EVOLUTION, param_type=ParameterType.INT,
        value=5,
        description="Tournament selection size",
        min_value=2, max_value=20, sensitivity=0.3, mutation_rate=0.05,
    )
    parameters["evo.diversity_threshold"] = GenomeParameter(
        id="evo.diversity_threshold", name="Diversity Threshold",
        category=ParameterCategory.EVOLUTION, param_type=ParameterType.FLOAT,
        value=0.15,
        description="Minimum population diversity before diversification",
        min_value=0.05, max_value=0.5, sensitivity=0.5, mutation_rate=0.1,
    )
    parameters["evo.novelty_weight"] = GenomeParameter(
        id="evo.novelty_weight", name="Novelty Weight",
        category=ParameterCategory.EVOLUTION, param_type=ParameterType.FLOAT,
        value=0.1,
        description="Weight of novelty in fitness calculation",
        min_value=0.0, max_value=0.5, sensitivity=0.4, mutation_rate=0.1,
    )
    parameters["evo.adaptive_learning_rate"] = GenomeParameter(
        id="evo.adaptive_learning_rate", name="Adaptive Learning Rate",
        category=ParameterCategory.EVOLUTION, param_type=ParameterType.FLOAT,
        value=0.05,
        description="Learning rate for adaptive mutation weights",
        min_value=0.001, max_value=0.2, sensitivity=0.5, mutation_rate=0.1,
    )

    # Compiler Parameters
    parameters["comp.optimization_level"] = GenomeParameter(
        id="comp.optimization_level", name="Optimization Level",
        category=ParameterCategory.COMPILER, param_type=ParameterType.INT,
        value=1,
        description="Compiler optimization level (0=none, 1=standard, 2=aggressive)",
        min_value=0, max_value=2, sensitivity=0.3, mutation_rate=0.05,
    )
    parameters["comp.normalization_enabled"] = GenomeParameter(
        id="comp.normalization_enabled", name="Normalization Enabled",
        category=ParameterCategory.COMPILER, param_type=ParameterType.BOOL,
        value=True,
        description="Whether to normalize ISR before compilation",
        sensitivity=0.2, mutation_rate=0.02,
    )

    # Verification Parameters
    parameters["verif.max_level"] = GenomeParameter(
        id="verif.max_level", name="Max Verification Level",
        category=ParameterCategory.VERIFICATION, param_type=ParameterType.INT,
        value=3,
        description="Maximum verification level (0-6)",
        min_value=0, max_value=6, sensitivity=0.6, mutation_rate=0.05,
    )
    parameters["verif.stop_on_blocker"] = GenomeParameter(
        id="verif.stop_on_blocker", name="Stop on Blocker",
        category=ParameterCategory.VERIFICATION, param_type=ParameterType.BOOL,
        value=True,
        description="Whether to stop verification on blocker",
        sensitivity=0.4, mutation_rate=0.02,
        locked=True,
    )

    # Deployment Parameters
    parameters["deploy.rollout_strategy"] = GenomeParameter(
        id="deploy.rollout_strategy", name="Rollout Strategy",
        category=ParameterCategory.DEPLOYMENT, param_type=ParameterType.STRING,
        value="rolling",
        description="Deployment rollout strategy",
        allowed_values=("immediate", "rolling", "blue_green", "canary"),
        sensitivity=0.4, mutation_rate=0.05,
    )
    parameters["deploy.canary_percentage"] = GenomeParameter(
        id="deploy.canary_percentage", name="Canary Percentage",
        category=ParameterCategory.DEPLOYMENT, param_type=ParameterType.FLOAT,
        value=10.0,
        description="Percentage of traffic for canary deployment",
        min_value=1.0, max_value=50.0, sensitivity=0.3, mutation_rate=0.1,
    )
    parameters["deploy.rollback_required"] = GenomeParameter(
        id="deploy.rollback_required", name="Rollback Required",
        category=ParameterCategory.DEPLOYMENT, param_type=ParameterType.BOOL,
        value=True,
        description="Whether rollback plan is required",
        sensitivity=0.5, mutation_rate=0.0,
        locked=True,
    )

    # Scheduling Parameters
    parameters["sched.max_concurrent_evolutions"] = GenomeParameter(
        id="sched.max_concurrent_evolutions", name="Max Concurrent Evolutions",
        category=ParameterCategory.SCHEDULING, param_type=ParameterType.INT,
        value=4,
        description="Maximum concurrent evolution runs",
        min_value=1, max_value=32, sensitivity=0.4, mutation_rate=0.05,
    )
    parameters["sched.evolution_timeout_seconds"] = GenomeParameter(
        id="sched.evolution_timeout_seconds", name="Evolution Timeout",
        category=ParameterCategory.SCHEDULING, param_type=ParameterType.FLOAT,
        value=300.0,
        description="Maximum time for a single evolution run (seconds)",
        min_value=30.0, max_value=3600.0, sensitivity=0.3, mutation_rate=0.05,
    )

    # Knowledge Parameters
    parameters["know.query_limit"] = GenomeParameter(
        id="know.query_limit", name="Knowledge Query Limit",
        category=ParameterCategory.KNOWLEDGE, param_type=ParameterType.INT,
        value=10,
        description="Maximum results per knowledge query",
        min_value=1, max_value=100, sensitivity=0.2, mutation_rate=0.05,
    )
    parameters["know.pattern_min_confidence"] = GenomeParameter(
        id="know.pattern_min_confidence", name="Pattern Min Confidence",
        category=ParameterCategory.KNOWLEDGE, param_type=ParameterType.FLOAT,
        value=0.5,
        description="Minimum confidence for pattern recommendations",
        min_value=0.1, max_value=0.95, sensitivity=0.4, mutation_rate=0.1,
    )

    # Agent Parameters
    parameters["agent.consensus_max_rounds"] = GenomeParameter(
        id="agent.consensus_max_rounds", name="Consensus Max Rounds",
        category=ParameterCategory.AGENT, param_type=ParameterType.INT,
        value=3,
        description="Maximum rounds for agent consensus",
        min_value=1, max_value=10, sensitivity=0.4, mutation_rate=0.05,
    )
    parameters["agent.approval_threshold"] = GenomeParameter(
        id="agent.approval_threshold", name="Approval Threshold",
        category=ParameterCategory.AGENT, param_type=ParameterType.FLOAT,
        value=0.6,
        description="Vote approval threshold for consensus",
        min_value=0.3, max_value=0.9, sensitivity=0.5, mutation_rate=0.1,
    )

    # Performance Parameters
    parameters["perf.fitness_eval_timeout_ms"] = GenomeParameter(
        id="perf.fitness_eval_timeout_ms", name="Fitness Eval Timeout",
        category=ParameterCategory.PERFORMANCE, param_type=ParameterType.FLOAT,
        value=1000.0,
        description="Timeout for fitness evaluation (milliseconds)",
        min_value=100.0, max_value=10000.0, sensitivity=0.3, mutation_rate=0.05,
    )
    parameters["perf.cache_enabled"] = GenomeParameter(
        id="perf.cache_enabled", name="Cache Enabled",
        category=ParameterCategory.PERFORMANCE, param_type=ParameterType.BOOL,
        value=True,
        description="Whether compilation caching is enabled",
        sensitivity=0.3, mutation_rate=0.02,
    )

    # Constitutional (Locked) Parameters
    parameters["const.isr_immutable"] = GenomeParameter(
        id="const.isr_immutable", name="ISR Immutability",
        category=ParameterCategory.EVOLUTION, param_type=ParameterType.BOOL,
        value=True,
        description="ISR must be immutable (CONSTITUTIONAL)",
        locked=True, sensitivity=1.0, mutation_rate=0.0,
    )
    parameters["const.verification_gate"] = GenomeParameter(
        id="const.verification_gate", name="Verification Gate",
        category=ParameterCategory.VERIFICATION, param_type=ParameterType.BOOL,
        value=True,
        description="Deployment requires verification approval (CONSTITUTIONAL)",
        locked=True, sensitivity=1.0, mutation_rate=0.0,
    )
    parameters["const.deterministic_compilation"] = GenomeParameter(
        id="const.deterministic_compilation", name="Deterministic Compilation",
        category=ParameterCategory.COMPILER, param_type=ParameterType.BOOL,
        value=True,
        description="Compilation must be deterministic (CONSTITUTIONAL)",
        locked=True, sensitivity=1.0, mutation_rate=0.0,
    )
    parameters["const.source_mapping"] = GenomeParameter(
        id="const.source_mapping", name="Source Mapping",
        category=ParameterCategory.COMPILER, param_type=ParameterType.BOOL,
        value=True,
        description="All artifacts must have source mappings (CONSTITUTIONAL)",
        locked=True, sensitivity=1.0, mutation_rate=0.0,
    )

    return PlatformGenome(
        genome_id="platform-genome-default", version=1,
        parameters=parameters,
    )
