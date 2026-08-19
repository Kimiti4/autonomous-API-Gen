"""R2.10.31.1 — Calibration.

The baseline everything else in Phase 31 is measured against. Calibration
is a MEASUREMENT phase, not a certification: it runs the corpus through
the campaign pipeline TWICE with the same seed, establishes the baseline
success/failure distribution, and proves the pipeline is deterministic and
fully provenanced at the 26-intent scale. It makes no claim about compiler
correctness at scale — that claim belongs to 31.5, and the epistemic chain
stays clean:

    R2.10.9 ready_to_scale   (infrastructure structurally ready)
    -> 31.1 calibration      (baseline established and reproducible)
    -> 31.5 certification    (compiler correctness proven)

The harness invokes the frozen CampaignHarness (R2.10.9) as a black box
and never modifies the ISR, the compilation foundation, or the evolution
engine. It measures. The declared-stub limitation (the intent -> ISR
pipeline behind the R2.10.9 dry run is a DECLARED stub, not the LLM-driven
IntentCompiler) is recorded on every calibration report — a calibration
over stubbed derivations is a calibration of the stub, and the report says
so explicitly.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from .corpus import ProjectCategory
from .failure_taxonomy import FailureCategory
from .harness import CampaignConfig, CampaignResult


class CalibrationVerdict(str, Enum):
    READY_FOR_31_2 = "READY_FOR_31_2"
    NOT_READY = "NOT_READY"
    # Deliberately no CERTIFIED — calibration measures; 31.5 certifies.


@dataclass(frozen=True)
class CategoryOutcome:
    """The calibration outcome for one project category."""

    category: ProjectCategory
    intent_count: int
    success_count: int
    failure_count: int
    failure_classes: Mapping[FailureCategory, int]


@dataclass(frozen=True)
class BaselineDistribution:
    """The baseline success/failure distribution across the corpus — the
    reference 31.2's backend matrix and 31.4's scale ramp are measured
    against. A shift in this distribution at higher scale is a signal to
    understand, not noise."""

    per_category: Mapping[ProjectCategory, CategoryOutcome]
    per_failure_class: Mapping[FailureCategory, int]
    total_intents: int
    total_success: int
    total_failure: int


@dataclass(frozen=True)
class CalibrationReport:
    """The durable artifact of 31.1. A measurement, not a certification."""

    calibration_id: str
    corpus_id: str
    seed: int
    baseline: BaselineDistribution
    deterministic_replay_verified: bool
    provenance_complete: bool
    failures_fully_classified: bool
    calibration_verdict: CalibrationVerdict
    calibration_event_ref: str
    declared_assumptions: tuple[str, ...] = ()


def baseline_to_payload(baseline: BaselineDistribution) -> dict[str, Any]:
    """JSON-safe ledger payload for a baseline distribution (the ledger
    never imports the campaign package)."""
    return {
        "per_category": {
            category.value: {
                "intent_count": outcome.intent_count,
                "success_count": outcome.success_count,
                "failure_count": outcome.failure_count,
                "failure_classes": {
                    failure_class.value: count
                    for failure_class, count in outcome.failure_classes.items()
                },
            }
            for category, outcome in sorted(
                baseline.per_category.items(), key=lambda item: item[0].value
            )
        },
        "per_failure_class": {
            failure_class.value: count
            for failure_class, count in sorted(
                baseline.per_failure_class.items(),
                key=lambda item: item[0].value,
            )
        },
        "total_intents": baseline.total_intents,
        "total_success": baseline.total_success,
        "total_failure": baseline.total_failure,
    }


class CalibrationHarness:
    """31.1 — Calibration.

    Runs the corpus through the campaign pipeline TWICE with the same seed
    and establishes the baseline. A measurement phase: it invokes the
    frozen CampaignHarness (R2.10.9) as a black box and never modifies the
    ISR, the compilation foundation, or the evolution engine. It measures.
    """

    def __init__(
        self, campaign_harness: Any, corpus: Any, ledger: Any
    ) -> None:
        self._campaign_harness = campaign_harness
        self._corpus = corpus
        self._ledger = ledger

    def run(self, config: CampaignConfig) -> CalibrationReport:
        # Run the campaign twice with the same seed — determinism is the
        # property that makes the baseline trustworthy.
        result1 = self._campaign_harness.run(config, self._corpus)
        result2 = self._campaign_harness.run(config, self._corpus)

        baseline = self._establish_baseline(result1)
        deterministic = self._verify_determinism(result1, result2)
        provenance_complete = self._verify_provenance(result1)
        failures_classified = self._verify_classification(result1)

        verdict = (
            CalibrationVerdict.READY_FOR_31_2
            if deterministic and provenance_complete and failures_classified
            else CalibrationVerdict.NOT_READY
        )

        calibration_ref = self._ledger.record_calibration(
            calibration_id=config.campaign_id,
            seed=config.seed,
            baseline=baseline_to_payload(baseline),
            deterministic=deterministic,
            provenance_complete=provenance_complete,
            failures_classified=failures_classified,
            verdict=verdict.value,
            declared_assumptions=result1.declared_assumptions,
        )

        return CalibrationReport(
            calibration_id=config.campaign_id,
            corpus_id=self._corpus.corpus_id,
            seed=config.seed,
            baseline=baseline,
            deterministic_replay_verified=deterministic,
            provenance_complete=provenance_complete,
            failures_fully_classified=failures_classified,
            calibration_verdict=verdict,
            calibration_event_ref=calibration_ref,
            declared_assumptions=result1.declared_assumptions,
        )

    def _establish_baseline(
        self, result: CampaignResult
    ) -> BaselineDistribution:
        per_category: dict[ProjectCategory, dict[str, Any]] = {}
        per_failure_class: dict[FailureCategory, int] = {}
        for outcome in result.outcomes:
            entry = per_category.setdefault(
                outcome.category,
                {"count": 0, "success": 0, "failure": 0, "classes": {}},
            )
            entry["count"] += 1
            if outcome.succeeded:
                entry["success"] += 1
            else:
                entry["failure"] += 1
                failure_class = (
                    outcome.failure.category
                    if outcome.failure
                    else FailureCategory.UNKNOWN
                )
                entry["classes"][failure_class] = (
                    entry["classes"].get(failure_class, 0) + 1
                )
                per_failure_class[failure_class] = (
                    per_failure_class.get(failure_class, 0) + 1
                )
        category_outcomes = {
            category: CategoryOutcome(
                category,
                entry["count"],
                entry["success"],
                entry["failure"],
                entry["classes"],
            )
            for category, entry in per_category.items()
        }
        return BaselineDistribution(
            per_category=category_outcomes,
            per_failure_class=per_failure_class,
            total_intents=len(result.outcomes),
            total_success=result.success_count,
            total_failure=result.failure_count,
        )

    def _verify_determinism(
        self, r1: CampaignResult, r2: CampaignResult
    ) -> bool:
        """Per-intent determinism: same intent -> same outcome, same
        artifact hash."""
        for o1, o2 in zip(r1.outcomes, r2.outcomes):
            if o1.intent_id != o2.intent_id or o1.succeeded != o2.succeeded:
                return False
            if o1.succeeded and o2.succeeded:
                if o1.metrics.artifact_hash != o2.metrics.artifact_hash:
                    return False
        return True

    def _verify_provenance(self, result: CampaignResult) -> bool:
        """Every successful outcome carries a complete provenance chain."""
        for outcome in result.outcomes:
            if outcome.succeeded:
                ref = outcome.metrics.provenance_chain_ref
                if ref is None or not self._ledger.chain_complete(ref):
                    return False
        return True

    def _verify_classification(self, result: CampaignResult) -> bool:
        """Every failure has a taxonomy class; silent UNKNOWN is not
        tolerated."""
        for outcome in result.outcomes:
            if not outcome.succeeded:
                if (
                    outcome.failure is None
                    or outcome.failure.category is FailureCategory.UNKNOWN
                ):
                    return False
        return True