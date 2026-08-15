"""Multi-objective fitness construction for Phase 18.

Reuses the tree's FitnessVector (reconcile the import path). All metrics are
higher-is-better so ``FitnessVector.dominates()`` remains meaningful for Phase
20 Pareto selection.
"""

from __future__ import annotations

from tiannara.domain.models.fitness import FitnessVector


def build_fitness(outcomes: "list", max_repair_attempts: int) -> FitnessVector:
    n = len(outcomes)
    if n == 0:
        return FitnessVector(metrics={
            "build": 0.0, "scan": 0.0, "test": 0.0,
            "verification": 0.0, "repair_free": 0.0,
        })

    static_ok = sum(1 for o in outcomes if o.static_ok)
    executed = [o for o in outcomes if o.test_result is not None]
    test_ok = sum(1 for o in executed if getattr(o.test_result, "passed", False))
    test_denom = len(executed) if executed else n
    verified = sum(1 for o in outcomes if o.ok)

    total_attempts = sum(o.repair_attempts for o in outcomes)
    max_total = max_repair_attempts * n
    repair_free = 1.0 - (total_attempts / max_total) if max_total > 0 else 1.0
    repair_free = max(0.0, min(1.0, repair_free))

    return FitnessVector(metrics={
        "build": 1.0,
        "scan": static_ok / n,
        "test": (test_ok / test_denom) if test_denom else 1.0,
        "verification": verified / n,
        "repair_free": repair_free,
    })
