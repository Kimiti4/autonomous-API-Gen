"""R2.9.5 -- Adaptive operator scheduling.

Allocates variation search budget across operators based on historical
evidence, with a guaranteed exploration floor to prevent operator-level
monoculture.

Constitutional constraints honored:
* The scheduler answers 'which operators get budget', NEVER 'which candidate
  is correct'. Correctness remains with the R2.8 boundary and R2.6 selection.
* ``BudgetAllocation`` is physically incapable of carrying a candidate, fitness
  score, or verdict -- no authority escalation is representable.
* Each stage independently replaceable: ``OperatorScheduler`` is a protocol.
* Search-process state stays outside the ISR (statistics live in the
  coordinator, never in the ISR).
* Deterministic: sorted iteration + largest-remainder apportionment + a
  fixed seed-passing contract, inheriting the R2.8.12 ``PYTHONHASHSEED``
  discipline.
* Credit assignment is immediate-outcome only: an operator is credited with
  the outcome of the candidate it produced in the generation that produced
  it (feasible? resolved the target?). Lineage-based credit (operator A set
  up the foundation operator B later completed) is a real refinement and is
  deliberately out of scope -- recorded here as future work.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol


@dataclass(frozen=True)
class OperatorStatistics:
    """Historical evidence for one operator (immediate-outcome attribution).

    ``operator_id`` is the canonical operator identity (the same key the
    diversity observer and mutation operators use).
    """
    operator_id: str
    attempts: int
    feasible_count: int
    target_resolved_count: int

    @property
    def success_rate(self) -> float:
        if self.attempts == 0:
            return 0.0
        return self.target_resolved_count / self.attempts

    def record(self, feasible: bool, resolved: bool) -> "OperatorStatistics":
        return OperatorStatistics(
            self.operator_id,
            self.attempts + 1,
            self.feasible_count + (1 if feasible else 0),
            self.target_resolved_count + (1 if resolved else 0),
        )


@dataclass(frozen=True)
class BudgetAllocation:
    """The scheduler's sole output: operator -> candidate count.

    Deliberately carries NO candidates, NO fitness, NO verdicts. The scheduler
    cannot escalate authority because this type cannot represent it.
    """
    allocations: Mapping[str, int]   # operator_id -> evidence-based count
    exploration_reserved: int        # floor reserved to prevent monopoly
    rationale: str

    @property
    def total(self) -> int:
        return sum(self.allocations.values())


class OperatorScheduler(Protocol):
    """Pluggable scheduling policy (independently replaceable)."""

    def schedule(
        self,
        statistics: Mapping[str, OperatorStatistics],
        population_size: int,
        seed: int,
    ) -> BudgetAllocation: ...


class EvidenceBasedScheduler:
    """Allocates budget proportional to smoothed operator success, with a
    guaranteed exploration floor distributed across all operators.

    * Cold start (no history): defer entirely to exploration.
    * Exploration floor: every operator receives a minimum share, so no
      operator can permanently monopolize the population.
    * Deterministic: sorted iteration + largest-remainder apportionment.
    * Zero-attempt operators are treated by their Laplace-smoothed rate
      (attractive), which is how never-tried operators keep receiving budget.
    """

    def __init__(self, exploration_floor: float = 0.2, smoothing: float = 1.0) -> None:
        self._exploration_floor = exploration_floor
        self._smoothing = smoothing

    def schedule(self, statistics, population_size, seed) -> BudgetAllocation:
        # Cold start: no operator has been attempted yet (the map may still
        # carry zero-attempt entries pre-seeded from the variation's known
        # operator set -- absence of history, not absence of operators).
        if not statistics or all(s.attempts == 0 for s in statistics.values()):
            return BudgetAllocation(
                allocations={},
                exploration_reserved=population_size,
                rationale="cold_start:no_history;defer_to_exploration",
            )

        names = sorted(statistics.keys())
        exploration_count = max(len(names), int(population_size * self._exploration_floor))
        exploration_count = min(exploration_count, population_size)
        exploitable = population_size - exploration_count

        # Laplace-smoothed success rates (handles zero-attempt operators).
        rates = {
            n: (statistics[n].target_resolved_count + self._smoothing)
               / (statistics[n].attempts + 2 * self._smoothing)
            for n in names
        }
        total_rate = sum(rates.values())

        allocations = {n: 0 for n in names}

        # Evidence-based allocation of the exploitable budget (largest remainder).
        if exploitable > 0 and total_rate > 0:
            raw = {n: exploitable * rates[n] / total_rate for n in names}
            floors = {n: int(raw[n]) for n in names}
            for n in names:
                allocations[n] += floors[n]
            remainder = exploitable - sum(floors.values())
            by_frac = sorted(names, key=lambda n: (-(raw[n] - floors[n]), n))
            for i in range(remainder):
                allocations[by_frac[i % len(by_frac)]] += 1

        # Exploration floor distributed uniformly (anti-monopoly guarantee).
        per_op = exploration_count // len(names)
        extra = exploration_count - per_op * len(names)
        for i, n in enumerate(names):
            allocations[n] += per_op + (1 if i < extra else 0)

        rationale = self._rationale(rates, statistics)
        return BudgetAllocation(allocations, exploration_count, rationale)

    def _rationale(self, rates, statistics) -> str:
        parts = [
            f"{n}:resolved={statistics[n].target_resolved_count}/{statistics[n].attempts}"
            f"@{rates[n]:.3f}"
            for n in sorted(rates)
        ]
        return "evidence:" + ";".join(parts)
