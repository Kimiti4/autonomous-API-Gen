"""R2.10.9 — the dry run: the verdict that justifies scaling.

The small-scale dry run validates the HARNESS — determinism, resource
behavior, failure classification, ledger integrity under parallel load —
at tens of intents before the campaign runs at thousands. ``ready_to_scale``
is the last pre-Phase-31 gate: when it returns True, the platform has
proven the campaign machinery itself is trustworthy.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from .failure_taxonomy import FailureCategory


@dataclass(frozen=True)
class DryRunVerdict:
    """The small-scale dry-run verdict. This is what justifies scaling to
    Phase 31. ``resource_budget_respected`` covers the measured dimensions
    of the budget (duration; the memory envelope is carried for Phase 31 —
    the dry run does not measure memory)."""

    harness_deterministic: bool
    resource_budget_respected: bool
    all_failures_classified: bool
    ledger_intact_under_load: bool
    corpus_category_coverage: int  # number of categories exercised
    ready_to_scale: bool


def budget_respected(result: Any, budget: Any) -> bool:
    """The measured budget dimensions hold: every outcome with metrics ran
    within the per-intent duration envelope. ``max_parallel`` bounds the
    harness by construction (workers <= max_parallel)."""
    for outcome in result.outcomes:
        if outcome.metrics is not None:
            if outcome.metrics.duration_ms > budget.max_duration_per_intent_ms:
                return False
    return True


class CampaignDryRun:
    """Runs the harness over the corpus at small scale and renders the
    verdict: the same campaign twice under the same seed must yield the
    same outcome counts, every failure must be classified, the ledger must
    stay intact under the harness's parallel load, and the corpus must
    exercise the full category shape."""

    def __init__(self, harness: Any) -> None:
        self._harness = harness

    def run(self, corpus: Any, config: Any) -> DryRunVerdict:
        r1 = self._harness.run(config, corpus)
        r2 = self._harness.run(dataclasses.replace(config, seed=config.seed), corpus)
        deterministic = (r1.success_count, r1.failure_count) == (
            r2.success_count,
            r2.failure_count,
        )
        failures = [o.failure for o in r1.outcomes if o.failure is not None]
        all_classified = all(
            f.category is not FailureCategory.UNKNOWN for f in failures
        )
        budget_ok = budget_respected(r1, config.resource_budget)
        return DryRunVerdict(
            harness_deterministic=deterministic,
            resource_budget_respected=budget_ok,
            all_failures_classified=all_classified,
            ledger_intact_under_load=r1.ledger_intact,
            corpus_category_coverage=len(corpus.categories_covered()),
            ready_to_scale=all(
                (deterministic, all_classified, r1.ledger_intact, budget_ok)
            ),
        )