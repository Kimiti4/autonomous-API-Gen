"""R2.9.3 -- Evolutionary process state.

Constitutional constraint: this is SEARCH-PROCESS state, kept strictly outside
the ISR. The ISR is the sole architectural source of truth; generation
counters, populations, frontiers, termination, and diversity metrics are about
the search, not the software. ``EvolutionState`` references ISR hashes
(``stable_isr_hash``) but never contains or mutates an ISR.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Optional


class TerminationReason(str, Enum):
    """Why a multi-generation run stopped. The ISR never carries this -- it is
    search-process state recorded only in ``EvolutionState``."""

    SUCCESS = "SUCCESS"                              # defect resolved
    GENERATION_LIMIT = "GENERATION_LIMIT"            # max generations reached
    POPULATION_EXHAUSTION = "POPULATION_EXHAUSTION"  # no novel candidates remain
    NO_FEASIBLE_CANDIDATES = "NO_FEASIBLE_CANDIDATES"  # no candidate improves on the parent
    STAGNATION = "STAGNATION"                        # selected ISR unchanged for N gens
    LINEAGE_BREAK = "LINEAGE_BREAK"                  # integrity violation


@dataclass(frozen=True)
class DiversityMetrics:
    """Observed-only diversity for one generation (R2.9.4's empirical basis).

    Recorded in ``EvolutionState``; NEVER used as a selection objective in
    R2.9.3. ``genotype_entropy`` is Shannon entropy over the mutation-operator
    distribution -- 0.0 is the monoculture diagnostic.
    """

    population_size: int
    unique_isr_count: int
    unique_delta_count: int
    mutation_operator_distribution: Mapping[str, int]
    genotype_entropy: float
    phenotype_diversity: float
    duplicate_rate: float


@dataclass(frozen=True)
class PopulationSnapshot:
    """Immutable snapshot of a generation's candidate identities."""

    candidate_ids: tuple[str, ...]


@dataclass(frozen=True)
class GenerationState:
    """One generation of the search. References ISR hashes only.

    ``selected_candidate_id`` is the deterministic advancement choice: the
    Pareto-selected feasible candidate, or (when none was feasible) the elite
    candidate advanced under the documented no-feasible rule
    (``elite_advanced=True``). ``selected_isr_hash`` is always the parent hash
    of the next generation.
    """

    generation_id: str
    generation_index: int
    parent_generation_id: Optional[str]
    parent_isr_hash: str
    population_snapshot: PopulationSnapshot
    evaluated_count: int
    feasible_count: int
    frontier_size: int
    selected_candidate_id: Optional[str]
    selected_isr_hash: Optional[str]
    elite_advanced: bool
    diversity: DiversityMetrics


@dataclass(frozen=True)
class EvolutionState:
    """The full multi-generation run. References ISR hashes; never holds the ISR."""

    evolution_id: str
    initial_isr_hash: str
    generations: tuple[GenerationState, ...]
    termination_reason: TerminationReason
    final_isr_hash: Optional[str]

    @property
    def generation_count(self) -> int:
        return len(self.generations)

    @property
    def succeeded(self) -> bool:
        return self.termination_reason is TerminationReason.SUCCESS


def derive_evolution_id(initial_isr_hash: str, observation_hash: str, seed: int) -> str:
    """Deterministic run identity: replaying the same (ISR, observation, seed)
    reproduces the same evolution_id and therefore the same event lineage."""
    basis = f"{initial_isr_hash}|{observation_hash}|{seed}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:24]


def derive_generation_id(evolution_id: str, index: int, parent_isr_hash: str) -> str:
    """Deterministic generation identity within a run."""
    basis = f"{evolution_id}|{index}|{parent_isr_hash}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:24]