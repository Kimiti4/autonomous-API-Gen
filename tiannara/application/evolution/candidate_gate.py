"""R2.5 -- Evolution Safety: the validation frontier for candidate ISRs.

A ``CandidateGate`` scores a candidate ISR against an independently evaluable,
evidence-producing frontier of gates. The Evolution Engine -- never the
compiler -- decides ACCEPT/REJECT (COMPILER PURITY INVARIANT: the compiler only
maps ``ISR -> artifact`` and never inspects failure observations, history, or
candidate fitness). Compilation / execution are performed once by the caller
and shared across all gates via ``GateContext``.

The six gates generalize the R2.4.0b acceptance assertions into reusable,
replaceable rules so the same frontier scores every future operator's
candidates (incl. R2.6's competing mutations):

    compile            -> candidate artifact exists & is valid
    target_failure     -> the observed target signature no longer occurs
    regression         -> no baseline passing test regresses
    isr_validity       -> candidate ISR is structurally sound
    invariant          -> every protected invariant still holds
    causal             -> mutation is an ISR delta, closes to the candidate, and
                          a fresh independent recompile is byte-identical

``protected_invariants`` is seeded minimally in R2.5 (see
``BrokenTreeIntactInvariant``) and grown with architectural/security/behavioral
invariants as those become evidence-checkable (R2.7/R2.8).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Protocol

from constitutional_architecture.isr.model import ISR

from tiannara.application.evolution.candidate_sandbox import CompiledCandidate
from tiannara.application.evolution.compiler_sandbox import hash_artifact
from tiannara.application.evolution.ledger import stable_isr_hash
from tiannara.application.evolution.mutation_operators import MutationCandidate
from tiannara.application.evolution.transition_restoration import (
    TransitionRestoration,
    apply_restoration,
)
from tiannara.domain.models.evidence import (
    REGRESSION_REJECT_CLASSES,
    RegressionClass,
    RegressionResult,
    TestExecution,
    TestOutcome,
    TestRunResult,
    DimensionAvailability,
    DimensionPolicy,
    DimensionResult,
    DimensionStatus,
)
from tiannara.domain.models.observation import FailureObservation


# R2.8.1: declared dimension policy. Critical dimensions whose evaluators are not
# yet implemented are ALLOWED today (transitional) but flagged -- ``critical=True``
# means that once the evaluator lands (``implemented=True``), an unevaluated
# result becomes infeasible. ``complexity_efficiency`` is advisory (Pareto-only).
DEFAULT_DIMENSION_POLICY: dict[str, DimensionPolicy] = {
    "correctness": DimensionPolicy(
        name="correctness", critical=True, implemented=True,
        evaluator="TargetFailureGate",
        availability=DimensionAvailability.AVAILABLE,
        when_unevaluated="infeasible",
    ),
    "regression_safety": DimensionPolicy(
        name="regression_safety", critical=True, implemented=True,
        evaluator="RegressionGate",
        availability=DimensionAvailability.AVAILABLE,
        when_unevaluated="infeasible",
    ),
    "structural_validity": DimensionPolicy(
        name="structural_validity", critical=True, implemented=True,
        evaluator="CompileGate + ISRValidityGate",
        availability=DimensionAvailability.AVAILABLE,
        when_unevaluated="infeasible",
    ),
    "causal_validity": DimensionPolicy(
        name="causal_validity", critical=True, implemented=True,
        evaluator="CausalGate",
        availability=DimensionAvailability.AVAILABLE,
        when_unevaluated="infeasible",
    ),
    "invariant_compliance": DimensionPolicy(
        name="invariant_compliance", critical=True, implemented=True,
        evaluator="InvariantGate",
        availability=DimensionAvailability.AVAILABLE,
        when_unevaluated="infeasible",
    ),
     "performance": DimensionPolicy(
        name="performance", critical=True, implemented=True,
        evaluator="PerformanceGate",
        availability=DimensionAvailability.AVAILABLE,
        when_unevaluated="infeasible",
    ),
    "security": DimensionPolicy(
        name="security", critical=True, implemented=True,
        evaluator="SecurityGate",
        availability=DimensionAvailability.AVAILABLE,
        when_unevaluated="infeasible",
    ),
    "complexity_efficiency": DimensionPolicy(
        name="complexity_efficiency", critical=False, implemented=True,
        evaluator="candidate mutation delta size",
        availability=DimensionAvailability.AVAILABLE,
        when_unevaluated="allow",
    ),
}


# -- evidence containers ------------------------------------------------------

@dataclass(frozen=True)
class GateResult:
    """Outcome of a single gate. Frozen so verdicts are tamper-evident."""

    gate_id: str
    passed: bool
    reason: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GateContext:
    """Shared, immutable inputs assembled once by the caller.

    The caller compiles/runs the candidate and baseline ISRs (and, for the
    CausalGate, an independent recompile of the candidate) and hands the
    already-computed results here so no gate repeats expensive execution.
    """

    candidate_isr: ISR
    candidate_artifact: CompiledCandidate
    candidate_run: TestRunResult
    baseline_artifact: CompiledCandidate
    baseline_run: TestRunResult
    observation: FailureObservation
    mutation: MutationCandidate
    parent_isr: ISR
    protected_invariants: tuple["ProtectedInvariant", ...] = ()
    broken_artifact: Optional[CompiledCandidate] = None
    broken_artifact_hash: str = ""
    independent_recompile_hash: str = ""


@dataclass(frozen=True)
class CandidateVerdict:
    accept: bool
    gate_results: tuple[GateResult, ...]
    candidate_hash: str
    parent_hash: str

    def content_hash(self) -> str:
        """Deterministic hash over the verdict + per-gate evidence chain."""
        from tiannara.domain.services.canonical import canonical_hash

        return canonical_hash(
            {
                "accept": self.accept,
                "candidate_hash": self.candidate_hash,
                "parent_hash": self.parent_hash,
                "gate_results": [
                    {"gate": r.gate_id, "passed": r.passed, "evidence": r.evidence}
                    for r in self.gate_results
                ],
            }
        )


# -- protected invariants -----------------------------------------------------

class ProtectedInvariant(Protocol):
    """A property that must not regress under repair (R2.5 seed surface)."""

    invariant_id: str

    def holds(self, ctx: GateContext) -> bool:
        ...


@dataclass(frozen=True)
class BrokenTreeIntactInvariant:
    """R2.4.0b A5a -- the repair path must not mutate the broken artifact's
    generated source. The candidate's broken tree must still hash as before
    (ignoring test-run cache side effects excluded by ``hash_artifact``)."""

    invariant_id = "broken_tree_intact"
    expected_hash: str

    def holds(self, ctx: GateContext) -> bool:
        if ctx.broken_artifact is None:
            return True
        return hash_artifact(ctx.broken_artifact.source_root) == self.expected_hash


# -- ISR structural validation (seed, evidence-producing) ---------------------

def validate_isr(isr: ISR) -> tuple[bool, list[str]]:
    """Minimal structural sanity for a candidate ISR.

    Returns ``(ok, issues)``. Seeded in R2.5 with checks that are unconditional
    and technology-neutral; expanded in later phases alongside richer invariants.
    """
    issues: list[str] = []
    for module in isr.system.modules:
        for wf in module.workflows:
            state_ids = [s.id for s in wf.states]
            if len(state_ids) != len(set(state_ids)):
                issues.append(f"workflow '{wf.id}': duplicate state ids")
            idset = set(state_ids)
            for t in wf.transitions:
                if t.from_state_id not in idset:
                    issues.append(f"workflow '{wf.id}': transition '{t.id}' "
                                  f"references unknown from_state {t.from_state_id!r}")
                if t.to_state_id not in idset:
                    issues.append(f"workflow '{wf.id}': transition '{t.id}' "
                                  f"references unknown to_state {t.to_state_id!r}")
            awaiting = [s for s in wf.states if s.metadata.get("awaits")]
            if awaiting and not any(s.state_type.value == "final" for s in wf.states):
                issues.append(f"workflow '{wf.id}': declares 'awaits' states "
                              f"but has no final state to resolve to")
    return (not issues, issues)


# -- gates --------------------------------------------------------------------

class Gate(Protocol):
    gate_id: str

    def evaluate(self, ctx: GateContext) -> GateResult:
        ...


class CompileGate:
    gate_id = "compile"

    def evaluate(self, ctx: GateContext) -> GateResult:
        ok = ctx.candidate_artifact is not None and ctx.candidate_artifact.compile_ok
        return GateResult(
            self.gate_id, ok,
            reason="candidate compiled" if ok else "candidate failed to compile",
            evidence={"artifact_hash": getattr(ctx.candidate_artifact, "artifact_hash", None)},
        )


class TargetFailureGate:
    """The observed failure signature must be resolved by the candidate run.

    The signature is recovered through the same operator primitive
    (``TransitionRestoration.extract_coroutine_name``) that produced the repair,
    keeping the gate backend-agnostic: it checks the *specific diagnostic
    signature*, not the coarse ``test_failure`` class, so ordinary failing tests
    never satisfy target resolution.
    """
    gate_id = "target_failure"

    def evaluate(self, ctx: GateContext) -> GateResult:
        name = TransitionRestoration().extract_coroutine_name(ctx.observation)
        signature = f"coroutine '{name}' was never awaited" if name else None
        logs = ""
        if ctx.candidate_run.logs_path:
            logs = Path(ctx.candidate_run.logs_path).read_text("utf-8", "replace")
        resolved = ctx.candidate_run.exit_code == 0 and ctx.candidate_run.passed
        if signature is not None:
            resolved = resolved and signature not in logs
        return GateResult(
            self.gate_id, resolved,
            reason="target failure resolved" if resolved else "target failure persists",
            evidence={
                "target_signature": signature,
                "candidate_exit_code": ctx.candidate_run.exit_code,
                "candidate_passed": ctx.candidate_run.passed,
                "signature_present": signature in logs if signature else False,
            },
        )


# -- R2.7: precise regression comparison ----------------------------------------
#
# The regression gate is a *set difference* over normalized per-test outcomes,
# not a pass-count delta. A candidate is refused when any test that passed in the
# (immutable, content-hash pinned) baseline was regressed, removed, skipped, or
# flaked, or when an assertion was gutt ed (same name, changed body). Name
# identity catches deletion/rename; content identity catches gutting. Both are
# reject-by-default -- the default is to refuse a candidate that *looks* better
# but is not. When per-test outcomes are unavailable (the R2.3-R2.6 aggregate
# path) the gate degrades to the historical pass-count comparison so existing
# evidence stays green.


def _transition(base: TestOutcome, cand: TestOutcome) -> RegressionClass:
    """Classify an outcome transition for a test present in both runs."""
    if base == TestOutcome.PASSED:
        if cand == TestOutcome.PASSED:
            return RegressionClass.PRESERVED_PASS
        if cand == TestOutcome.SKIPPED:
            return RegressionClass.NEW_SKIP
        return RegressionClass.REGRESSED_FAILURE
    if base in (TestOutcome.FAILED, TestOutcome.ERROR):
        if cand == TestOutcome.PASSED:
            return RegressionClass.RESOLVED_FAILURE
        return RegressionClass.PERSISTING_FAILURE
    # base == SKIPPED
    if cand == TestOutcome.PASSED:
        return RegressionClass.NEW_PASS
    if cand in (TestOutcome.FAILED, TestOutcome.ERROR):
        return RegressionClass.NEW_FAILURE
    return RegressionClass.NEW_PASS


def _new_outcome_to_class(outcome: TestOutcome) -> RegressionClass:
    """Classify a test present only in the candidate (genuinely new test)."""
    return {
        TestOutcome.PASSED: RegressionClass.NEW_PASS,
        TestOutcome.FAILED: RegressionClass.NEW_FAILURE,
        TestOutcome.ERROR: RegressionClass.NEW_ERROR,
        TestOutcome.SKIPPED: RegressionClass.NEW_SKIP,
    }[outcome]


def classify_regression(
    baseline: TestRunResult, candidate: TestRunResult
) -> RegressionResult:
    """R2.7 set-difference regression classification.

    Compares two runs by test *name* (the name layer) with a content-hash
    cross-check (the content layer). Returns reject-by-default semantics: any
    test that regressed, vanished, was skipped, flaked, or was gutted rejects
    the candidate unless an explicit protection opts it in.
    """
    if not baseline.tests and not candidate.tests:
        # R2.6 aggregate fallback: no per-test surface to diff over.
        delta = baseline.pass_count - candidate.pass_count
        accept = candidate.exit_code == 0 and delta <= 0
        return RegressionResult(
            baseline_id="",
            class_counts={"aggregate_only": 1},
            accept=accept,
            precision="aggregate_only",
            detail="per-test outcomes unavailable; pass-count comparison only",
        )

    base_by_id = {t.test_id: t for t in baseline.tests}
    cand_by_id = {t.test_id: t for t in candidate.tests}

    counts: dict[str, int] = {}
    regressed: list[str] = []
    newly_failing: list[str] = []
    persisting: list[str] = []
    new_added: list[str] = []
    vanished: list[str] = []
    flake: list[str] = []
    gutting: list[str] = []

    def _bump(cls: RegressionClass) -> None:
        counts[cls.value] = counts.get(cls.value, 0) + 1

    # Tests present in BOTH runs: name identity holds -> compare outcome + body.
    for tid, b in base_by_id.items():
        c = cand_by_id.pop(tid, None)
        if c is None:
            _bump(RegressionClass.REMOVED_TEST)
            vanished.append(tid)
            continue
        # Content layer: same name, rewritten body => assertion gutting.
        if b.content_hash and c.content_hash and b.content_hash != c.content_hash:
            _bump(RegressionClass.CONTENT_GUTTING)
            gutting.append(tid)
            continue
        if c.flaky or b.flaky:
            _bump(RegressionClass.FLAKE)
            flake.append(tid)
            continue
        cls = _transition(b.outcome, c.outcome)
        _bump(cls)
        if cls == RegressionClass.REGRESSED_FAILURE:
            regressed.append(tid)
        elif cls in (RegressionClass.NEW_FAILURE, RegressionClass.NEW_ERROR):
            newly_failing.append(tid)
        elif cls == RegressionClass.PERSISTING_FAILURE:
            persisting.append(tid)
        elif cls == RegressionClass.NEW_SKIP:
            new_added.append(tid)

    # Tests only in the candidate: genuinely new (e.g. a hidden/added test).
    for tid, c in cand_by_id.items():
        if c.flaky:
            _bump(RegressionClass.FLAKE)
            flake.append(tid)
            continue
        cls = _new_outcome_to_class(c.outcome)
        _bump(cls)
        if cls == RegressionClass.NEW_SKIP:
            new_added.append(tid)
        elif cls in (RegressionClass.NEW_FAILURE, RegressionClass.NEW_ERROR):
            newly_failing.append(tid)

    reject = any(
        RegressionClass(k) in REGRESSION_REJECT_CLASSES for k in counts
    )
    detail = (
        f"regressed={regressed} newly_failing={newly_failing} "
        f"persisting={persisting} vanished={vanished} new={new_added} "
        f"flake={flake} gutting={gutting}"
    )
    return RegressionResult(
        baseline_id=getattr(baseline, "baseline_id", ""),
        class_counts=counts,
        regressed=tuple(regressed),
        newly_failing=tuple(newly_failing),
        persisting=tuple(persisting),
        newly_added=tuple(new_added),
        vanished=tuple(vanished),
        flake=tuple(flake),
        gutting=tuple(gutting),
        accept=not reject,
        precision=("per_test" if (baseline.tests and candidate.tests)
                   else "aggregate_only"),
        detail=detail,
    )


class RegressionGate:
    """No baseline passing test may regress.

    R2.7: exact set-difference classification over normalized per-test outcomes.
    A previously-passing test that regressed, was removed, was skipped, flaked,
    or was gutt ed (assertion stripped while still green) refuses the candidate.
    When per-test outcomes are unavailable, the gate degrades to the historical
    pass-count comparison rather than failing silently -- the precision loss is
    recorded as evidence.
    """

    gate_id = "regression"

    def evaluate(self, ctx: GateContext) -> GateResult:
        if ctx.candidate_run.tests and ctx.baseline_run.tests:
            reg = classify_regression(ctx.baseline_run, ctx.candidate_run)
            passed = reg.accept
            regressed_total = (
                len(reg.regressed) + len(reg.newly_failing)
                + len(reg.persisting) + len(reg.vanished)
                + len(reg.flake) + len(reg.gutting)
            )
            reason = (
                "no protected regressions" if passed
                else f"{regressed_total} protected test(s) regressed/removed/flaked/gutted"
            )
            return GateResult(
                self.gate_id, passed, reason,
                evidence={
                    "class_counts": reg.class_counts,
                    "regressed": list(reg.regressed),
                    "newly_failing": list(reg.newly_failing),
                    "persisting": list(reg.persisting),
                    "vanished": list(reg.vanished),
                    "newly_added": list(reg.newly_added),
                    "flake": list(reg.flake),
                    "gutting": list(reg.gutting),
                    "precision": reg.precision,
                },
            )
        # R2.6 aggregate fallback (preserved for evidence without per-test data).
        baseline = ctx.baseline_run.pass_count
        candidate = ctx.candidate_run.pass_count
        delta = baseline - candidate
        passed = ctx.candidate_run.exit_code == 0 and delta <= 0
        return GateResult(
            self.gate_id, passed,
            reason="no protected regressions" if passed else f"{delta} passing test(s) regressed",
            evidence={
                "baseline_pass_count": baseline,
                "candidate_pass_count": candidate,
                "regressed_count": max(delta, 0),
                "precision": "aggregate-only (per-test outcomes not exposed by TestRunResult)",
            },
        )


class ISRValidityGate:
    gate_id = "isr_validity"

    def evaluate(self, ctx: GateContext) -> GateResult:
        ok, issues = validate_isr(ctx.candidate_isr)
        return GateResult(
            self.gate_id, ok,
            reason="ISR structurally valid" if ok else f"ISR invalid: {issues}",
            evidence={"issues": issues},
        )


class InvariantGate:
    gate_id = "invariant"

    def evaluate(self, ctx: GateContext) -> GateResult:
        violated = [inv.invariant_id for inv in ctx.protected_invariants if not inv.holds(ctx)]
        passed = not violated
        return GateResult(
            self.gate_id, passed,
            reason=("no protected invariants violated" if passed
                    else f"violated: {violated}"),
            evidence={
                "checked": [inv.invariant_id for inv in ctx.protected_invariants],
                "violations": violated,
            },
        )


class CausalGate:
    """The EVOLUTION ENGINE invariant: the repair is an ISR mutation, not a
    source patch. Sub-checks recover R2.4.0b's causality guarantees
    (4: closure, 5b: fresh recompile byte-identical, 5c: repair changed source).

    An empty delta (the NullMutation / "choose restraint") is a *valid* identity
    ISR delta: closure and fresh-recompile hold, and the "changed" sub-check is
    skipped so the identity candidate is rejected by TargetFailureGate (failure
    persists) rather than by this gate."""
    gate_id = "causal"

    @staticmethod
    def _diff_is_isr_delta(entries: tuple[str, ...]) -> bool:
        # An empty delta is the identity mutation: structurally a valid ISR delta.
        if not entries:
            return True
        for entry in entries:
            try:
                desc = json.loads(entry)
            except json.JSONDecodeError:
                return False
            if not isinstance(desc, dict):
                return False
            required = {"workflow_id", "from_state_id", "to_state_id", "trigger"}
            if not required.issubset(desc.keys()):
                return False
        return True

    def evaluate(self, ctx: GateContext) -> GateResult:
        delta = ctx.mutation.mutation_delta
        entries = delta.entries
        is_null = delta.size == 0
        mutation_is_isr = self._diff_is_isr_delta(entries)
        # closure: applying the ISR delta to the parent ISR yields the candidate.
        if is_null:
            closure = stable_isr_hash(ctx.parent_isr) == stable_isr_hash(ctx.candidate_isr)
        else:
            closure = (
                stable_isr_hash(apply_restoration(ctx.parent_isr, entries))
                == stable_isr_hash(ctx.candidate_isr)
            )
        fresh = (bool(ctx.independent_recompile_hash)
                 and ctx.candidate_artifact.artifact_hash == ctx.independent_recompile_hash)
        changed = True if is_null else (
            bool(ctx.broken_artifact_hash)
            and ctx.candidate_artifact.artifact_hash != ctx.broken_artifact_hash
        )
        passed = mutation_is_isr and closure and fresh and changed
        return GateResult(
            self.gate_id, passed,
            reason=("valid ISR mutation with verified closure" if passed
                    else "causal chain broken"),
            evidence={
                "mutation_is_isr_delta": mutation_is_isr,
                "closure": closure,
                "fresh_recompile_matches": fresh,
                "repair_changed_artifact": changed,
                "delta_size": delta.size,
            },
        )


class _UnavailableDimensionGate:
    """Shared base for capability-declared-but-not-yet-evaluated dimensions.

    Policy-driven (R2.8.1 review point #3): an *unimplemented* capability is
    allowed in R2.7.5 (transitional -- there is no evaluator to fail it), but the
    dimension is declared ``critical``, so the moment the evaluator lands
    (``implemented=True``), an unevaluated result becomes infeasible and the
    candidate is rejected. This makes "we don't know" a recorded, visible state,
    never a silent pass.
    """

    gate_id: str
    dimension_name: str

    def _policy(self) -> DimensionPolicy:
        return DEFAULT_DIMENSION_POLICY.get(self.dimension_name, DimensionPolicy(
            name=self.dimension_name, critical=True, implemented=False,
            evaluator="none", availability=DimensionAvailability.UNAVAILABLE,
            when_unevaluated="infeasible",
        ))

    def _dimension(self) -> DimensionResult:
        policy = self._policy()
        return policy.to_dimension_result(
            status=DimensionStatus.UNEVALUATED,
            score=0.0,
            evidence={"capability": "declared", "implemented": policy.implemented},
        )

    def evaluate(self, ctx: GateContext) -> GateResult:
        policy = self._policy()
        dr = self._dimension()
        reject = policy.unevaluated_is_infeasible()
        if reject:
            reason = (
                f"{self.dimension_name} is a critical, implemented dimension and "
                "remains unevaluated"
            )
        else:
            reason = (
                f"{self.dimension_name} declared critical-but-unevaluated "
                f"(evaluator '{policy.evaluator}' not yet implemented: R2.7.5 "
                f"allows, R2.8 enforces)"
            )
        return GateResult(
            self.gate_id, passed=not reject, reason=reason,
            evidence={
                "status": dr.status.value,
                "availability": dr.availability.value,
                "evaluator": dr.evaluator,
                "critical": policy.critical,
                "implemented": policy.implemented,
                "when_unevaluated": policy.when_unevaluated,
                "unevaluated_is_infeasible": reject,
                "dimension_result": dr.model_dump(mode="json"),
            },
        )


# -- R2.8.8: implemented performance + security evaluators ----------------------
# These gates consume ISR + evidence, are technology-agnostic, and enforce hard
# feasibility constraints (not weighted objectives): a security critical failure
# or a performance regression beyond policy threshold -> infeasible.
# Thresholds live in the policy/evidence, not hard-coded in the gate.

import os as _os

#: Default multiplier: candidate duration must not exceed baseline * this factor.
_PERF_DEGRADATION_THRESHOLD = float(_os.environ.get("R288_PERF_THRESHOLD", "2.0"))


class PerformanceGate:
    """R2.8.8: evaluate performance dimension from ISR + evidence.

    Consumes TestRunResult.duration_seconds (candidate vs baseline). A
    regression beyond ``threshold`` is a hard feasibility constraint.

    KNOWN LIMITATIONS (logged for R2.8.14 certification):
      * Single-sample wall-clock is statistically fragile -- CI load, CPU
        throttling, and GC can produce false rejects. A production deployment
        should aggregate N samples and compare distributions.
      * Wall-clock duration is environment-dependent, which tensions with the
        determinism/reproducibility model. The primary performance signal
        should migrate to ISR-level characteristics (resource annotations,
        declared scaling) with wall-clock as a secondary/derived signal.
    """

    gate_id = "performance"
    dimension_name = "performance"
    threshold: float = _PERF_DEGRADATION_THRESHOLD

    def __init__(self, *, threshold: float | None = None):
        if threshold is not None:
            self.threshold = threshold

    def _policy(self) -> DimensionPolicy:
        return DEFAULT_DIMENSION_POLICY[self.dimension_name]

    def _dimension(self, passed: bool, score: float, evidence: dict) -> DimensionResult:
        policy = self._policy()
        if passed:
            status = DimensionStatus.EVALUATED
        else:
            status = DimensionStatus.FAILED
        return policy.to_dimension_result(
            status=status, score=score, evidence=evidence,
        )

    def evaluate(self, ctx: GateContext) -> GateResult:
        cand = ctx.candidate_run
        base = ctx.baseline_run
        evidence = {
            "candidate_duration": cand.duration_seconds,
            "baseline_duration": base.duration_seconds,
            "threshold": self.threshold,
        }

        if base.duration_seconds <= 0 and cand.duration_seconds <= 0:
            # No timing evidence available: UNKNOWN (not a silent pass).
            policy = self._policy()
            dr = policy.to_dimension_result(
                status=DimensionStatus.UNEVALUATED, score=0.0,
                evidence={**evidence, "note": "no timing data in either run"},
            )
            reject = policy.unevaluated_is_infeasible()
            return GateResult(
                self.gate_id, passed=not reject,
                reason=("performance: no timing data; unevaluated critical dimension"
                        if reject else "performance: no timing data available"),
                evidence={
                    "status": dr.status.value,
                    "availability": dr.availability.value,
                    "evaluator": dr.evaluator,
                    "critical": policy.critical,
                    "implemented": policy.implemented,
                    "when_unevaluated": policy.when_unevaluated,
                    "unevaluated_is_infeasible": reject,
                    "dimension_result": dr.model_dump(mode="json"),
                },
            )

        ratio = (cand.duration_seconds / base.duration_seconds
                 if base.duration_seconds > 0 else float("inf"))
        passed = ratio <= self.threshold
        score = 1.0 if passed else 0.0
        dr = self._dimension(passed, score, evidence)

        return GateResult(
            self.gate_id, passed,
            reason=("performance OK" if passed
                    else f"duration {cand.duration_seconds:.3f}s exceeds "
                         f"threshold {base.duration_seconds * self.threshold:.3f}s "
                         f"(ratio {ratio:.2f}x)"),
            evidence={
                "status": dr.status.value,
                "availability": dr.availability.value,
                "evaluator": dr.evaluator,
                "critical": self._policy().critical,
                "implemented": self._policy().implemented,
                "duration_ratio": ratio,
                "threshold": self.threshold,
                "dimension_result": dr.model_dump(mode="json"),
            },
        )


class SecurityGate:
    """R2.8.8: evaluate security dimension from the ISR graph.

    Technology-agnostic: inspects only ISR-level declarations
    (Interface, Service, Operation, Policy). No framework adapters, no
    dynamic scanning. A public endpoint without required_permissions is a
    hard feasibility constraint (security_critical=FAIL).

    KNOWN LIMITATIONS (logged for R2.8.14 certification):
      * Scope is authorization/access-control only. Secrets handling,
        isolation boundaries, dependency exposure, and attack-surface
        invariants are deferred to a future phase.
      * Checks are absolute invariants: any violation fails the candidate
        regardless of whether the baseline also violated. This is stricter
        than regression-oriented and is the intended default for security.
    """

    gate_id = "security"
    dimension_name = "security"

    def _policy(self) -> DimensionPolicy:
        return DEFAULT_DIMENSION_POLICY[self.dimension_name]

    def _evaluate_isr(self, isr: ISR) -> tuple[bool, list[str], dict]:
        """Return (passed, violations, evidence)."""
        violations: list[str] = []
        checks: dict[str, bool] = {}

        public_iface_no_policy = 0
        public_endpoint_no_perms = 0
        public_op_no_perms = 0

        for module in isr.system.modules:
            policies = {p.policy_type.value for p in module.policies}
            has_audit = "audit" in policies

            for iface in module.interfaces:
                if not iface.is_internal:
                    if iface.secured_by_policy_id is None:
                        public_iface_no_policy += 1
                        violations.append(
                            f"module '{module.id}' interface '{iface.id}' "
                            f"is public but lacks a security policy binding"
                        )
                    for ep in iface.endpoints:
                        if ep.is_public and not ep.required_permissions:
                            public_endpoint_no_perms += 1
                            violations.append(
                                f"interface '{iface.id}' endpoint '{ep.id}' "
                                f"is public without required_permissions"
                            )

            for svc in module.services:
                for op in svc.operations:
                    if op.is_public and not op.required_permissions:
                        public_op_no_perms += 1
                        violations.append(
                            f"service '{svc.id}' operation '{op.id}' "
                            f"is public without required_permissions"
                        )
            checks[f"module:{module.id}:audit_policy"] = has_audit

        passed = not violations
        evidence = {
            "public_iface_no_policy": public_iface_no_policy,
            "public_endpoint_no_perms": public_endpoint_no_perms,
            "public_op_no_perms": public_op_no_perms,
            "checks": checks,
            "violations": violations,
        }
        return passed, violations, evidence

    def evaluate(self, ctx: GateContext) -> GateResult:
        policy = self._policy()
        passed, violations, evidence = self._evaluate_isr(ctx.candidate_isr)

        if passed:
            status = DimensionStatus.EVALUATED
            score = 1.0
        else:
            status = DimensionStatus.FAILED
            score = 0.0

        dr = policy.to_dimension_result(status=status, score=score, evidence=evidence)
        return GateResult(
            self.gate_id, passed,
            reason=("security OK" if passed
                    else f"{len(violations)} security violation(s): {violations[:3]}"),
            evidence={
                "status": dr.status.value,
                "availability": dr.availability.value,
                "evaluator": dr.evaluator,
                "critical": policy.critical,
                "implemented": policy.implemented,
                "violation_count": len(violations),
                "public_iface_no_policy": evidence["public_iface_no_policy"],
                "public_endpoint_no_perms": evidence["public_endpoint_no_perms"],
                "public_op_no_perms": evidence["public_op_no_perms"],
                "violations": violations,
                "dimension_result": dr.model_dump(mode="json"),
            },
        )


# -- orchestrator -------------------------------------------------------------

class CandidateGate:
    """Runs the validation frontier over a pre-compiled/pre-run GateContext.

    ``CandidateGate`` performs no compilation/execution itself; doing so would
    couple the gate to a particular execution environment and risk re-running
    tests per gate. The caller (the Evolution Engine, e.g. the R2.4.0b loop) is
    responsible for producing ``candidate_run``/``baseline_run`` and feeding them
    in, preserving COMPILER PURITY and deterministic, shared evidence.
    """

    def __init__(self, gates: tuple[Gate, ...] = ()):
        self._gates = gates or self._default_gates()

    @staticmethod
    def _default_gates() -> tuple[Gate, ...]:
        return (
            CompileGate(),
            TargetFailureGate(),
            RegressionGate(),
            ISRValidityGate(),
            InvariantGate(),
            CausalGate(),
            PerformanceGate(),
            SecurityGate(),
        )

    @classmethod
    def default(cls) -> "CandidateGate":
        return cls()

    def evaluate(self, ctx: GateContext) -> CandidateVerdict:
        results = tuple(gate.evaluate(ctx) for gate in self._gates)
        accept = all(r.passed for r in results)
        return CandidateVerdict(
            accept=accept,
            gate_results=results,
            candidate_hash=stable_isr_hash(ctx.candidate_isr),
            parent_hash=stable_isr_hash(ctx.parent_isr),
        )
