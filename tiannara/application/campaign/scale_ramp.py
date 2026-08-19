"""R2.10.31.4 — the scale ramp: does the envelope hold as workload grows?

31.1 calibrated the baseline; 31.2 multiplied it across seven backends;
31.3 made every deviation explainable. 31.4 stops asking "can the system
do this?" and asks "do the properties established at small scale remain
true as workload increases?" It is OBSERVATIONAL, never architectural:
it never changes the semantic contract to fit scale — it climbs the
declared scale levels, runs the REAL campaign pipeline at every level
(real derivation, real evolution, real compilation, real verification,
real ledger records), and measures where a property stops holding.

The invariant: scale must not become a source of epistemic ambiguity.
Every property proven in 31.1-31.3 must either still hold at larger
scale or fail visibly and be classified. A property that quietly
degrades is exactly what this ramp exists to catch.

Declared methodology (never implicit):

  * corpus growth is DERIVED_FROM_SEEDS — every scale corpus is the 26
    calibrated seeds plus deterministic derived variants (a pure function
    of seed intent and tier index); the ramp measures volume-of-similar,
    never diversity-at-scale. NEW_INTENTS / MIXED are declared
    unreachable on this platform and cannot be silently approximated.
  * the deterministic rerun subset (the canary) is chosen BEFORE the
    ramp runs — post-hoc selection would invite picking the cases that
    still pass. It is replayed at every level through the full
    seven-backend matrix with real verification and real provenance.
  * the reachable top is DECLARED, never silently capped: levels
    1000/5000 are scheduled but not run — full real per-intent
    compilation bounds the runnable top within the declared per-level
    budget. The measured cost at the reached top is recorded; the
    unreached levels are named.
  * the per-level budget is a real resource measured by the real clock;
    a breach is envelope evidence, never a campaign defect.
  * the verdict is READY_FOR_31_5, never CERTIFIED — 31.4 earns the
    certification statement; 31.5 makes it.
"""
from __future__ import annotations

import dataclasses
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from tiannara.application.evolution.ledger import EventType

from .backend_matrix import MatrixDisposition, MatrixHarness
from .corpus import GenerationCorpus
from .failure_taxonomy import FailureCategory
from .failure_taxonomy_validation import (
    ContractEvidence,
    FailureObservation,
    ResourceEvidence,
    TaxonomyClassifier,
    VerificationEvidence,
    failure_category_map,
)
from .harness import CampaignConfig, GenerationOutcome, backend_for

SCALE_LEVELS: tuple[int, ...] = (26, 100, 500, 1000, 5000)

DEFAULT_LEVEL_BUDGET_SECONDS = 300
DEFAULT_REACHABLE_TOP = 500


class ScaleRampVerdict(str, Enum):
    READY_FOR_31_5 = "READY_FOR_31_5"
    NOT_READY = "NOT_READY"
    # Deliberately no CERTIFIED — 31.4 earns the certification statement; it does not make it.


class ScaleRampGate(str, Enum):
    """The ten gates that keep scale honest. Each is evaluated at every
    level."""

    SCALE_MONOTONICITY = "SCALE_MONOTONICITY"
    FAILURE_RATE_ACCOUNTING = "FAILURE_RATE_ACCOUNTING"
    TAXONOMY_STABILITY = "TAXONOMY_STABILITY"
    NO_SILENT_OMISSION = "NO_SILENT_OMISSION"
    LEDGER_COMPLETENESS = "LEDGER_COMPLETENESS"
    PROVENANCE_PRESERVATION = "PROVENANCE_PRESERVATION"
    RESOURCE_BOUND_HONESTY = "RESOURCE_BOUND_HONESTY"
    DETERMINISTIC_RERUN_SUBSET = "DETERMINISTIC_RERUN_SUBSET"
    NO_CROSS_INTENT_CONTAMINATION = "NO_CROSS_INTENT_CONTAMINATION"
    NO_CERTIFICATION_INFLATION = "NO_CERTIFICATION_INFLATION"


class CorpusGrowthStrategy(str, Enum):
    """How the corpus grows at each scale level. A DECLARED ASSUMPTION —
    it determines what the ramp measures: volume-of-similar,
    diversity-at-scale, or a stated mix. Never left implicit."""

    DERIVED_FROM_SEEDS = "DERIVED_FROM_SEEDS"
    NEW_INTENTS = "NEW_INTENTS"
    MIXED = "MIXED"


class UnreachableCorpusStrategy(Exception):
    """A growth strategy the platform cannot yet honor — declared, never
    silently approximated."""


@dataclass(frozen=True)
class DeterministicRerunSubset:
    """A fixed sample replayed at every scale level — the reproducibility
    canary.

    If the subset's outcomes drift as scale grows, determinism is
    degrading even when the aggregate looks fine. Chosen BEFORE the ramp
    runs; choosing it after would tempt picking the cases that still
    pass, which is exactly the rationalization 31.3 made structurally
    impossible.
    """

    subset_id: str
    intent_ids: tuple[str, ...]


class CorpusBuilder:
    """Builds the corpus for a given scale per the declared growth
    strategy.

    DERIVED_FROM_SEEDS: the 26 calibrated seeds first, then deterministic
    derived variants — a pure function of (seed intent, tier index), so
    the variant corpus is fully reproducible with no RNG. Every scale
    corpus CONTAINS the 26 seeds byte-identically: the seeds are the
    monotonicity anchor at every level.
    """

    def __init__(self, seeds: GenerationCorpus) -> None:
        self._seeds = seeds

    def seed_intent_ids(self) -> tuple[str, ...]:
        """The calibrated seed intents — the monotonicity anchor present
        at every scale level."""
        return tuple(intent.intent_id for intent in self._seeds.intents)

    def build(
        self,
        scale: int,
        strategy: CorpusGrowthStrategy = CorpusGrowthStrategy.DERIVED_FROM_SEEDS,
    ) -> GenerationCorpus:
        if strategy is not CorpusGrowthStrategy.DERIVED_FROM_SEEDS:
            raise UnreachableCorpusStrategy(
                f"{strategy.value}: new intents cannot yet be authored at "
                "scale on this platform; DERIVED_FROM_SEEDS is the declared "
                "strategy — never a silent approximation"
            )
        seeds = self._seeds.intents
        if scale <= len(seeds):
            return GenerationCorpus(
                corpus_id=f"{self._seeds.corpus_id}-s{scale}",
                intents=tuple(seeds[:scale]),
            )
        derived: list[Any] = []
        for k in range(1, scale - len(seeds) + 1):
            seed = seeds[(k - 1) % len(seeds)]
            tier = 1 + (k - 1) // len(seeds)
            derived.append(
                dataclasses.replace(
                    seed,
                    intent_id=f"{seed.intent_id}-v{tier}",
                    problem_statement=(
                        f"{seed.problem_statement} — scale variant {tier}: "
                        "the same declared problem at increased corpus scale."
                    ),
                )
            )
        return GenerationCorpus(
            corpus_id=f"{self._seeds.corpus_id}-s{scale}",
            intents=seeds + tuple(derived),
        )


def evidence_to_observation(
    outcome: GenerationOutcome,
) -> FailureObservation:
    """The bridge from a campaign failure outcome to a 31.3
    FailureObservation — taxonomy stability at scale is checked with the
    SAME classifier 31.3 validated, over the SAME evidence the real
    execution produced."""

    failure = outcome.failure
    assert failure is not None
    resource: ResourceEvidence | None = None
    contract: ContractEvidence | None = None
    verification: VerificationEvidence | None = None
    if failure.category in (
        FailureCategory.RESOURCE_EXHAUSTION,
        FailureCategory.TIMEOUT,
    ):
        resource = ResourceEvidence(
            indicates_resource_exhaustion=(
                failure.category is FailureCategory.RESOURCE_EXHAUSTION
            ),
            indicates_timeout=failure.category is FailureCategory.TIMEOUT,
            details=failure.evidence,
        )
    if failure.category is FailureCategory.COMPILATION_CONTRACT_VIOLATION:
        contract = ContractEvidence(
            backend_declared_unsupported=False,
            contract_violated=True,
            violation_details=failure.evidence,
        )
    if failure.category is FailureCategory.VERIFICATION_FAILED:
        verification = VerificationEvidence(
            artifact_failed_verification=True,
            failure_reason=failure.evidence,
            is_artifact_fault=True,  # R2.10.8: verification failure = artifact fault
        )
    return FailureObservation(
        observation_id=f"scale-{outcome.intent_id}-{failure.stage}",
        intent_id=outcome.intent_id,
        backend_id=backend_for(outcome.category),
        stage=failure.stage,
        error_evidence=failure.evidence,
        resource_evidence=resource,
        contract_evidence=contract,
        verification_evidence=verification,
    )


@dataclass(frozen=True)
class ScaleLevelResult:
    scale: int
    total_cases: int
    success_count: int
    failure_count: int
    failure_tally: Mapping[FailureCategory, int]
    canary_tally: Mapping[str, int]  # per MatrixDisposition value
    canary_invariance: bool
    gates_held: Mapping[ScaleRampGate, bool]
    envelope_hit: bool  # infrastructure envelope reached at this scale
    envelope_reason: str | None
    duration_ms: int
    seed_outcomes: Mapping[str, tuple[bool, str | None]]
    canary_outcomes: Mapping[
        tuple[str, str], tuple[str, str | None, str | None, bool | None]
    ]


@dataclass(frozen=True)
class ScaleRampReport:
    """The durable artifact of 31.4 — the scale envelope, measured not
    assumed."""

    ramp_id: str
    per_level: tuple[ScaleLevelResult, ...]
    scale_envelope: int  # largest scale at which all ten gates held
    ramp_complete: bool  # every level up to the declared top ran, no envelope hit
    envelope_hit_at: int | None
    envelope_reason: str | None
    scheduled_levels: tuple[int, ...]
    reachable_top: int  # declared BEFORE the ramp — named, never silent
    level_budget_seconds: int  # a real resource, measured by the real clock
    corpus_growth_strategy: CorpusGrowthStrategy
    rerun_subset: DeterministicRerunSubset
    taxonomy_exercised: bool  # whether any real failure was observed at scale
    declared_assumptions: tuple[str, ...]  # inherited from 31.1-31.3 + 31.4 methodology
    verdict: ScaleRampVerdict
    ramp_event_ref: str


def level_payload(level: ScaleLevelResult) -> dict[str, Any]:
    """JSON-safe ledger payload for one scale level."""
    return {
        "scale": level.scale,
        "total_cases": level.total_cases,
        "success_count": level.success_count,
        "failure_count": level.failure_count,
        "failure_tally": {
            category.value: count
            for category, count in level.failure_tally.items()
        },
        "canary_tally": dict(level.canary_tally),
        "canary_invariance": level.canary_invariance,
        "gates_held": {
            gate.value: held for gate, held in level.gates_held.items()
        },
        "envelope_hit": level.envelope_hit,
        "envelope_reason": level.envelope_reason,
        "duration_ms": level.duration_ms,
    }


class ScaleRampHarness:
    """31.4 — Scale ramp.

    Climbs the scale levels, observing whether the properties established
    at small scale remain true as workload increases. OBSERVATIONAL: it
    never changes the semantic contract to fit scale. At every level it
    runs the real campaign pipeline over the level corpus (real
    derivation, evolution, compilation, verification, ledger records) and
    replays the predeclared rerun subset through the full seven-backend
    matrix. It stops climbing when a gate fails, the declared reachable
    top is reached, or a real resource signal marks the infrastructure
    envelope — and reports the envelope: the largest scale at which all
    ten gates held.
    """

    def __init__(
        self,
        campaign_harness: Any,
        intent_pipeline: Any,
        registry: Any,
        evaluator: Any,
        verifier: Any,
        conformance_registry: Any,
        ledger: Any,
        corpus_builder: CorpusBuilder,
        taxonomy_classifier: TaxonomyClassifier,
        rerun_subset: DeterministicRerunSubset,
        declared_assumptions: tuple[str, ...] = (),
        scale_levels: tuple[int, ...] = SCALE_LEVELS,
        corpus_growth_strategy: CorpusGrowthStrategy = (
            CorpusGrowthStrategy.DERIVED_FROM_SEEDS
        ),
        reachable_top: int = DEFAULT_REACHABLE_TOP,
        level_budget_seconds: int = DEFAULT_LEVEL_BUDGET_SECONDS,
    ) -> None:
        self._campaign_harness = campaign_harness
        self._corpus_builder = corpus_builder
        self._taxonomy_classifier = taxonomy_classifier
        self._rerun_subset = rerun_subset
        self._ledger = ledger
        self._declared_assumptions = declared_assumptions
        self._scale_levels = scale_levels
        self._corpus_growth_strategy = corpus_growth_strategy
        self._reachable_top = reachable_top
        self._level_budget_seconds = level_budget_seconds
        self._matrix = MatrixHarness(
            intent_pipeline=intent_pipeline,
            registry=registry,
            evaluator=evaluator,
            verifier=verifier,
            conformance_registry=conformance_registry,
            ledger=ledger,
            declared_assumptions=declared_assumptions,
        )

    def run(self, config: CampaignConfig) -> ScaleRampReport:
        per_level: list[ScaleLevelResult] = []
        scale_envelope = 0
        envelope_hit_at: int | None = None
        envelope_reason: str | None = None
        taxonomy_exercised = False
        seed_baseline: dict[str, tuple[bool, str | None]] | None = None
        canary_baseline: dict[
            tuple[str, str], tuple[str, str | None, str | None, bool | None]
        ] | None = None
        for scale in self._scale_levels:
            if scale > self._reachable_top:
                break
            level = self._run_level(config, scale, seed_baseline, canary_baseline)
            per_level.append(level)
            taxonomy_exercised |= level.failure_count > 0
            if level.envelope_hit and envelope_hit_at is None:
                envelope_hit_at = scale
                envelope_reason = level.envelope_reason
            if seed_baseline is None:
                seed_baseline = dict(level.seed_outcomes)
            if canary_baseline is None:
                canary_baseline = dict(level.canary_outcomes)
            if all(level.gates_held.values()):
                scale_envelope = scale
            else:
                break  # a gate failed: measure the envelope, stop
            if level.envelope_hit:
                break  # infrastructure envelope: honest stop
        verdict = (
            ScaleRampVerdict.READY_FOR_31_5
            if per_level
            and all(all(level.gates_held.values()) for level in per_level)
            and self._declared_assumptions
            else ScaleRampVerdict.NOT_READY
        )
        ramp_complete = bool(
            per_level
            and per_level[-1].scale == self._reachable_top
            and envelope_hit_at is None
            and all(all(level.gates_held.values()) for level in per_level)
        )
        assumptions = (
            self._declared_assumptions + self._methodology_assumptions()
        )
        ramp_ref = self._ledger.record_scale_ramp(
            ramp_id=config.campaign_id,
            per_level=tuple(level_payload(level) for level in per_level),
            scale_envelope=scale_envelope,
            ramp_complete=ramp_complete,
            envelope_hit_at=envelope_hit_at,
            envelope_reason=envelope_reason,
            corpus_growth_strategy=self._corpus_growth_strategy.value,
            rerun_subset={
                "subset_id": self._rerun_subset.subset_id,
                "intent_ids": list(self._rerun_subset.intent_ids),
            },
            reachable_top=self._reachable_top,
            scheduled_levels=list(self._scale_levels),
            level_budget_seconds=self._level_budget_seconds,
            taxonomy_exercised=taxonomy_exercised,
            verdict=verdict.value,
            declared_assumptions=assumptions,
        )
        return ScaleRampReport(
            ramp_id=config.campaign_id,
            per_level=tuple(per_level),
            scale_envelope=scale_envelope,
            ramp_complete=ramp_complete,
            envelope_hit_at=envelope_hit_at,
            envelope_reason=envelope_reason,
            scheduled_levels=self._scale_levels,
            reachable_top=self._reachable_top,
            level_budget_seconds=self._level_budget_seconds,
            corpus_growth_strategy=self._corpus_growth_strategy,
            rerun_subset=self._rerun_subset,
            taxonomy_exercised=taxonomy_exercised,
            declared_assumptions=assumptions,
            verdict=verdict,
            ramp_event_ref=ramp_ref,
        )

    def _methodology_assumptions(self) -> tuple[str, ...]:
        """The ramp's own declared methodology — the growth strategy, the
        predeclared rerun subset, the reachable top, and the per-level
        budget. Named, never implicit; composed onto the inherited 31.1
        assumptions."""
        unreached = ", ".join(
            str(scale)
            for scale in self._scale_levels
            if scale > self._reachable_top
        )
        return (
            "corpus_growth: DERIVED_FROM_SEEDS — every scale corpus is the "
            "26 calibrated seeds plus deterministic derived variants (a pure "
            "function of seed intent and tier index); the ramp measures "
            "volume-of-similar, never diversity-at-scale; NEW_INTENTS/MIXED "
            "are declared unreachable on this platform",
            f"rerun_subset: predeclared {self._rerun_subset.subset_id} "
            f"({len(self._rerun_subset.intent_ids)} seed intents) replayed "
            "with the full seven-backend matrix at every level — chosen "
            "before the ramp runs, never after",
            f"reachable_top: {self._reachable_top} — scheduled levels "
            f"beyond it ({unreached}) are NOT run: full real per-intent "
            "compilation bounds the runnable top within the declared "
            "per-level budget; the measured cost at the reached top is "
            "recorded and the unreached levels are named, never silently "
            "dropped",
            f"level_budget: {self._level_budget_seconds}s per level — a "
            "real resource measured by the real clock; a breach is "
            "envelope evidence, never a campaign defect",
        )

    def _run_level(
        self,
        config: CampaignConfig,
        scale: int,
        seed_baseline: dict[str, tuple[bool, str | None]] | None,
        canary_baseline: dict[
            tuple[str, str], tuple[str, str | None, str | None, bool | None]
        ] | None,
    ) -> ScaleLevelResult:
        level_campaign_id = f"{config.campaign_id}-s{scale}"
        corpus = self._corpus_builder.build(scale, self._corpus_growth_strategy)
        level_config = CampaignConfig(
            campaign_id=level_campaign_id,
            corpus_id=corpus.corpus_id,
            resource_budget=config.resource_budget,
            generations_per_intent=config.generations_per_intent,
            seed=config.seed,
        )
        started = time.perf_counter()
        try:
            result = self._campaign_harness.run(level_config, corpus)
        except MemoryError as error:
            return ScaleLevelResult(
                scale=scale,
                total_cases=len(corpus.intents),
                success_count=0,
                failure_count=0,
                failure_tally={},
                canary_tally={},
                canary_invariance=False,
                gates_held={gate: False for gate in ScaleRampGate},
                envelope_hit=True,
                envelope_reason=(
                    f"real MemoryError during the campaign at scale {scale}: "
                    f"{error}"
                ),
                duration_ms=0,
                seed_outcomes={},
                canary_outcomes={},
            )
        subset_corpus = GenerationCorpus(
            corpus_id=f"{corpus.corpus_id}-canary",
            intents=tuple(
                intent
                for intent in corpus.intents
                if intent.intent_id in self._rerun_subset.intent_ids
            ),
        )
        canary = self._matrix.run(subset_corpus, level_config)
        duration_ms = int((time.perf_counter() - started) * 1000)

        envelope_hit, envelope_reason = self._detect_envelope_hit(
            scale, result, duration_ms
        )
        gates = {
            ScaleRampGate.SCALE_MONOTONICITY: self._check_scale_monotonicity(
                result, seed_baseline
            ),
            ScaleRampGate.FAILURE_RATE_ACCOUNTING:
                self._check_failure_rate_accounting(result),
            ScaleRampGate.TAXONOMY_STABILITY:
                self._check_taxonomy_stability(result),
            ScaleRampGate.NO_SILENT_OMISSION:
                self._check_no_silent_omission(level_campaign_id, result, canary),
            ScaleRampGate.LEDGER_COMPLETENESS:
                self._check_ledger_completeness(result, canary),
            ScaleRampGate.PROVENANCE_PRESERVATION:
                self._check_provenance_preservation(result, canary),
            ScaleRampGate.RESOURCE_BOUND_HONESTY:
                self._check_resource_bound_honesty(result, envelope_hit),
            ScaleRampGate.DETERMINISTIC_RERUN_SUBSET:
                self._check_deterministic_rerun_subset(canary, canary_baseline),
            ScaleRampGate.NO_CROSS_INTENT_CONTAMINATION:
                self._check_no_cross_intent_contamination(
                    level_campaign_id, result
                ),
            ScaleRampGate.NO_CERTIFICATION_INFLATION:
                self._check_no_certification_inflation(),
        }
        return ScaleLevelResult(
            scale=scale,
            total_cases=len(corpus.intents),
            success_count=result.success_count,
            failure_count=result.failure_count,
            failure_tally=self._tally_failures(result),
            canary_tally=self._tally_canary(canary),
            canary_invariance=canary.cross_backend_invariance_held,
            gates_held=gates,
            envelope_hit=envelope_hit,
            envelope_reason=envelope_reason,
            duration_ms=duration_ms,
            seed_outcomes=self._seed_outcomes_of(result),
            canary_outcomes=self._canary_outcomes_of(canary),
        )

    def _detect_envelope_hit(
        self, scale: int, result: Any, duration_ms: int
    ) -> tuple[bool, str | None]:
        """Real resource signals, never inference from failure counts: a
        real classified resource exhaustion from the real execution, or
        the declared per-level wall-clock budget measured by the real
        clock."""
        for outcome in result.outcomes:
            if outcome.failure is not None and outcome.failure.category in (
                FailureCategory.RESOURCE_EXHAUSTION,
                FailureCategory.TIMEOUT,
            ):
                return (
                    True,
                    f"real {outcome.failure.category.value} classified "
                    f"during the campaign at scale {scale}",
                )
        if duration_ms > self._level_budget_seconds * 1000:
            return (
                True,
                f"measured duration {duration_ms / 1000:.1f}s exceeds the "
                f"declared per-level budget {self._level_budget_seconds}s",
            )
        return False, None

    # -- gate checks -----------------------------------------------------------

    def _check_scale_monotonicity(
        self,
        result: Any,
        seed_baseline: dict[str, tuple[bool, str | None]] | None,
    ) -> bool:
        """Growing workload does not silently change semantic behavior:
        every seed intent's outcome must be identical to its level-26
        outcome (same success, same artifact hash)."""
        if seed_baseline is None:
            return True  # the first level establishes the baseline
        current = self._seed_outcomes_of(result)
        return set(current) == set(seed_baseline) and all(
            current[intent_id] == baseline
            for intent_id, baseline in seed_baseline.items()
        )

    def _check_failure_rate_accounting(self, result: Any) -> bool:
        """Every case receives exactly one terminal disposition."""
        if result.success_count + result.failure_count != len(result.outcomes):
            return False
        for outcome in result.outcomes:
            if outcome.succeeded:
                if (
                    outcome.failure is not None
                    or outcome.metrics is None
                    or outcome.metrics.provenance_chain_ref is None
                ):
                    return False
            elif (
                outcome.failure is None
                or outcome.failure.category is None
                or outcome.metrics is not None
            ):
                return False
        return True

    def _check_taxonomy_stability(self, result: Any) -> bool:
        """Identical causal evidence maps to the same class regardless of
        scale — classified by the SAME 31.3 classifier over the real
        evidence."""
        for outcome in result.outcomes:
            if outcome.failure is None:
                continue
            observation = evidence_to_observation(outcome)
            disposition = self._taxonomy_classifier.classify(observation)
            if disposition.class_ is not failure_category_map(
                outcome.failure.category
            ):
                return False
        return True

    def _level_generation_events(self, level_campaign_id: str) -> list[Any]:
        return [
            event
            for event in self._ledger.events()
            if event.event_type is EventType.GENERATION_OUTCOME
            and (event.payload or {}).get("campaign_id") == level_campaign_id
        ]

    def _check_no_silent_omission(
        self, level_campaign_id: str, result: Any, canary: Any
    ) -> bool:
        """Unsupported carriers remain explicitly represented: every level
        outcome is chain-recorded (no dropped cases), every canary case
        binds to its conformance evidence, and any EXPLICITLY_UNSUPPORTED
        case names its unsupported semantics."""
        events = self._level_generation_events(level_campaign_id)
        if len(events) != result.success_count:
            return False
        for case in canary.cases:
            if self._ledger.event_by_ref(case.conformance_evidence_ref) is None:
                return False
            if (
                case.disposition is MatrixDisposition.EXPLICITLY_UNSUPPORTED
                and not case.unsupported_semantics
            ):
                return False
        return True

    def _canary_chain_complete(self, case: Any) -> bool:
        """A canary case's chain is complete when every anchor it claims
        resolves on the ledger: the terminal ref (the verification event,
        or the conformance event for an explicitly-unsupported case), the
        compilation event (deterministic id bound by the artifact), and
        the conformance evidence."""
        if case.provenance_chain_ref is not None and (
            self._ledger.event_by_ref(case.provenance_chain_ref) is None
        ):
            return False
        if case.artifact_hash is not None:
            compilation_ref = (
                f"compilation-{case.backend_id}-{case.artifact_hash[:8]}"
            )
            if self._ledger.event_by_ref(compilation_ref) is None:
                return False
            if case.provenance_chain_ref is None:
                return False
        if self._ledger.event_by_ref(case.conformance_evidence_ref) is None:
            return False
        return True

    def _check_ledger_completeness(self, result: Any, canary: Any) -> bool:
        """Every outcome remains chain-addressable."""
        if not self._ledger.verify_event_chain():
            return False
        for outcome in result.outcomes:
            if outcome.succeeded and not self._ledger.chain_complete(
                outcome.metrics.provenance_chain_ref
            ):
                return False
        for case in canary.cases:
            if not self._canary_chain_complete(case):
                return False
        return True

    def _check_provenance_preservation(self, result: Any, canary: Any) -> bool:
        """ISR -> target -> backend -> artifact -> verification remains
        reconstructible, and one semantic source per intent across
        backends."""
        for outcome in result.outcomes:
            if outcome.succeeded:
                event = self._ledger.event_by_ref(
                    outcome.metrics.provenance_chain_ref
                )
                if event is None or (
                    event.payload or {}
                ).get("artifact_hash") != outcome.metrics.artifact_hash:
                    return False
        for case in canary.cases:
            if case.isr_hash is None:
                return False
            if not self._canary_chain_complete(case):
                return False
        return canary.cross_backend_invariance_held

    def _check_resource_bound_honesty(
        self, result: Any, envelope_hit: bool
    ) -> bool:
        """Exhaustion is INFRASTRUCTURE evidence about the envelope, never
        a campaign defect: a resource-classified failure MUST flag the
        envelope, not blur into the failure rate."""
        for outcome in result.outcomes:
            if outcome.failure is not None and outcome.failure.category in (
                FailureCategory.RESOURCE_EXHAUSTION,
                FailureCategory.TIMEOUT,
            ):
                return envelope_hit
        return True

    def _check_deterministic_rerun_subset(
        self,
        canary: Any,
        canary_baseline: dict[
            tuple[str, str], tuple[str, str | None, str | None, bool | None]
        ] | None,
    ) -> bool:
        """The canary: the fixed sample yields equivalent semantic
        outcomes at every level (same disposition, same semantic source,
        same realization, same verification)."""
        if canary_baseline is None:
            return True  # the first level establishes the canary baseline
        current = self._canary_outcomes_of(canary)
        return set(current) == set(canary_baseline) and all(
            current[key] == baseline
            for key, baseline in canary_baseline.items()
        )

    def _check_no_cross_intent_contamination(
        self, level_campaign_id: str, result: Any
    ) -> bool:
        """The R2.10.9 concurrency isolation holds at scale: every level
        outcome event binds to its own intent (subject == payload == the
        outcome's intent), every intent compiled against ITS category's
        declared realization, nothing missing or foreign on the chain."""
        events = self._level_generation_events(level_campaign_id)
        if len(events) != result.success_count:
            return False
        by_intent = {outcome.intent_id: outcome for outcome in result.outcomes}
        for event in events:
            payload = event.payload or {}
            intent_id = payload.get("intent_id")
            if event.subject_id != intent_id:
                return False
            outcome = by_intent.get(intent_id)
            if outcome is None:
                return False
            if payload.get("backend_id") != backend_for(outcome.category):
                return False
        return True

    def _check_no_certification_inflation(self) -> bool:
        """The verdict space contains no CERTIFIED."""
        return not hasattr(ScaleRampVerdict, "CERTIFIED")

    # -- helpers ---------------------------------------------------------------

    def _tally_failures(self, result: Any) -> Mapping[FailureCategory, int]:
        tally: dict[FailureCategory, int] = {}
        for outcome in result.outcomes:
            if outcome.failure is not None:
                tally[outcome.failure.category] = (
                    tally.get(outcome.failure.category, 0) + 1
                )
        return tally

    def _tally_canary(self, canary: Any) -> Mapping[str, int]:
        tally: dict[str, int] = {}
        for case in canary.cases:
            tally[case.disposition.value] = (
                tally.get(case.disposition.value, 0) + 1
            )
        return tally

    def _seed_outcomes_of(
        self, result: Any
    ) -> dict[str, tuple[bool, str | None]]:
        seed_ids = set(self._corpus_builder.seed_intent_ids())
        return {
            outcome.intent_id: (
                outcome.succeeded,
                outcome.metrics.artifact_hash if outcome.metrics else None,
            )
            for outcome in result.outcomes
            if outcome.intent_id in seed_ids
        }

    def _canary_outcomes_of(
        self, canary: Any
    ) -> dict[
        tuple[str, str], tuple[str, str | None, str | None, bool | None]
    ]:
        return {
            (case.intent_id, case.backend_id): (
                case.disposition.value,
                case.isr_hash,
                case.artifact_hash,
                case.verification_verified,
            )
            for case in canary.cases
        }
