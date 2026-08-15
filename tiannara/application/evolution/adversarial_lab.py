"""R2.8.2 -- Test-Gaming Corpus: the adversarial front-end of the evaluation lab.

This module is the *bounded anti-gaming laboratory*. It does **not** generate
software or ship to GitHub (those are R2.10 / R2.12). It establishes, on a
controlled FSM test corpus, that the evaluation surface cannot be gamed by the
evolution engine's own mutation operators.

Architecture (information-hiding boundary, no blacklisting):

    MutationHarness              AdversarialGateDecider
      knows: mutation_label        sees ONLY: (anchored baseline
      applies: mutation  ─────━►     + CandidateEvidence)
      records label to ledger     decides: drift + regression +
      for audit/scoring           isolation + holdout + attestation
                                  -> feasibility + catching layers

The decider's ``decide`` takes **no mutation label** -- a blacklist keyed on
mutation names is literally unrepresentable. The mutation label lives only in
``MutationSpec`` / harness metadata and the ledger, for audit and for the
detection-rate measurement (R2.8.3).

The corpus is data-driven (``MUTATION_MATRIX``): each row declares its attack
surface, its expected feasibility, the layers that must catch it, and the
holdout invariant. Rows are applied as pure, deterministic functions of the
anchored baseline, so "same seed + mutation = same candidate hash + same
classification" holds by construction (the determinism contract R2.8.12 relies
on). The matrix is the permanent artifact that R2.8.14's certification iterates.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, replace
from typing import Callable, Mapping
from constitutional_architecture.isr.model import ISR
from constitutional_architecture.isr.model.isr import ISRProvenance
from constitutional_architecture.isr.model.module import Module

from tiannara.adversarial import (
    AttackPrimitive,
)

from tiannara.application.evolution.evaluation_boundary import (
    EvaluationAuthority,
    EvaluationBoundary,
    ProtectedTestSet,
)
from tiannara.application.evolution.ledger import EvolutionLedger, EventType
from tiannara.application.evolution.candidate_gate import classify_regression
from tiannara.domain.models.evidence import (
    DriftClass,
    DriftResult,
    Provenance,
    RegressionResult,
    TestExecution,
    TestIdentity,
    TestOutcome,
    TestRunResult,
    Visibility,
)
from tiannara.domain.services.canonical import canonical_hash
from tiannara.application.evolution.authorization import (
    Authorization,
    FSMTestSurfaceProjector,
    regression_infeasible_with_auth,
)
from tiannara.application.evolution.architecture import (
    ArchitecturalAuthorization,
    DeltaArchitectureProjector,
    InvariantResult,
    InvariantViolation,
    InvariantClass,
    evaluate_invariants,
    architectural_round_trip_integrity,
    round_trip_integrity,
    normalize as normalize_architecture,
    default_fsm_invariants,
)


# -- canonical FSM test corpus (R2.8.7's "controlled FSM artifact", hermetic) ----
# These ids are the shared vocabulary between the surface author, the mutation
# ``apply`` functions, and the matrix declarations. They model an order-FSM
# repair surface plus one evolvable mutation-score canary and one hidden holdout.

ID_REG_AWAIT = "fsm::transition_await_handles_final"
ID_REG_ERR = "fsm::transition_await_to_error"
ID_REG_DEADLOCK = "fsm::concurrent_transition_deadlock"
ID_EVOLVABLE_CANARY = "ev::mutation_score_canary"
ID_HOLDOUT = "fsm::holdout_state_coverage"

_H_AWAIT = "sha256:await_v1"
_H_ERR = "sha256:err_v1"
_H_DEADLOCK = "sha256:deadlock_v1"
_H_CANARY = "sha256:canary_v1"
_H_HOLDOUT = "sha256:holdout_v1"


def canonical_fsm_surface(authority: EvaluationAuthority,
                         boundary: EvaluationBoundary,
                         *, environment_fingerprint: str = "fsm-r2.8.2") -> ProtectedTestSet:
    """The anchored protected core for the R2.8.2 lab.

    Composition is deliberate:
      * 3 protected VISIBLE tests  (regression anchors the engine must not gut)
      * 1 protected HIDDEN holdout (read-isolated; run only by the authority)
      * 1 evolvable  VISIBLE test   (the legitimate-edit control target)
    """
    identities = (
        authority.identity(ID_REG_AWAIT, _H_AWAIT, visibility=Visibility.VISIBLE),
        authority.identity(ID_REG_ERR, _H_ERR, visibility=Visibility.VISIBLE),
        authority.identity(ID_REG_DEADLOCK, _H_DEADLOCK, visibility=Visibility.VISIBLE),
        authority.identity(ID_HOLDOUT, _H_HOLDOUT, visibility=Visibility.HIDDEN),
        TestIdentity.from_provenance(
            ID_EVOLVABLE_CANARY, Provenance.ISR_GENERATED,
            content_hash=_H_CANARY, visibility=Visibility.VISIBLE,
        ),
    )
    return boundary.anchor(identities, environment_fingerprint=environment_fingerprint)


def canonical_baseline_visible_run() -> TestRunResult:
    """Per-test baseline for the VISIBLE surface (what the candidate self-reports).

    The hidden holdout is NOT part of the candidate's run: it is exercised
    separately and authoritatively by the evaluation authority (R2.8.7 read
    isolation). The regression gate diffs visible-baseline vs candidate-visible
    only; holdout integrity is a distinct attestation.
    """
    tests = (
        TestExecution(test_id=ID_REG_AWAIT, outcome=TestOutcome.PASSED, content_hash=_H_AWAIT),
        TestExecution(test_id=ID_REG_ERR, outcome=TestOutcome.PASSED, content_hash=_H_ERR),
        TestExecution(test_id=ID_REG_DEADLOCK, outcome=TestOutcome.PASSED, content_hash=_H_DEADLOCK),
        TestExecution(test_id=ID_EVOLVABLE_CANARY, outcome=TestOutcome.PASSED, content_hash=_H_CANARY),
    )
    failed = sum(1 for t in tests if t.outcome in (TestOutcome.FAILED, TestOutcome.ERROR))
    return TestRunResult(
        passed=(failed == 0), exit_code=0,
        total_tests=len(tests), failed_tests=failed, tests=tests,
    )


def _holdout_run() -> tuple[TestExecution, ...]:
    return (TestExecution(test_id=ID_HOLDOUT, outcome=TestOutcome.PASSED, content_hash=_H_HOLDOUT),)


def _visible_baseline_evidence() -> tuple[TestExecution, ...]:
    return tuple(TestExecution(test_id=tid, outcome=TestOutcome.PASSED, content_hash=h)
                 for tid, h in ((ID_REG_AWAIT, _H_AWAIT),
                                (ID_REG_ERR, _H_ERR),
                                (ID_REG_DEADLOCK, _H_DEADLOCK),
                                (ID_EVOLVABLE_CANARY, _H_CANARY)))


# -- attack surface taxonomy -----------------------------------------------------

class AttackSurface(str, enum.Enum):
    """The three surfaces a test-gaming mutation can target.

    Visibility controls what evolution observes; protection controls what it
    may mutate. A mutation's attack surface is *how* it attacks, not how it is
    *detected* -- detection is the gate's job, not the spec's.
    """
    IDENTITY = "identity"        # test id rename / delete / discovery disable
    CONTENT = "content"          # assertion weaken / remove / fixture alter
    DISCOVERY = "discovery"      # skip / suppress / disable discovery
    BEHAVIOR = "behavior"        # ISR-level mask (special-case / early-return / fabricate)
    COMPOSED = "composed"        # R2.8.11: composed composite attack


class Verdict(str, enum.Enum):
    """Gate verdict: accept or reject a candidate."""
    ACCEPT = "accept"
    REJECT = "reject"


# -- candidate evidence (the gate's only window; no mutation label) -------------

@dataclass(frozen=True)
class CandidateEvidence:
    """Info-hiding boundary payload.

    Built by the harness from a mutation; the decider reasons over *this* plus
    the anchored baseline only. The mutation label is never carried here, so a
    name-keyed blacklist cannot be expressed in the decision path.
    """

    __test__ = False

    evolution_evidence: tuple[TestExecution, ...]
    holdout_evidence: tuple[TestExecution, ...]
    causal_delta_accepted: bool = False
    authorization: Authorization | None = None
    candidate_isr: ISR | None = None
    holdout_intact: bool = True

    @property
    def evidence_hash(self) -> str:
        return self.content_hash()

    def content_hash(self) -> str:
        """Deterministic fingerprint of the candidate's observable evidence."""
        auth_hash = (
            self.authorization.authorization_hash if self.authorization else None
        )
        return canonical_hash(
            {
                "evolution": [t.model_dump(mode="json") for t in self.evolution_evidence],
                "holdout": [t.model_dump(mode="json") for t in self.holdout_evidence],
                "causal_delta_accepted": self.causal_delta_accepted,
                "authorization": auth_hash,
                "candidate_isr": self.candidate_isr.content_hash if self.candidate_isr else None,
            }
        )


# -- decision -------------------------------------------------------------------

@dataclass(frozen=True)
class Decision:
    """R2.8.2 verdict + the chain of evidence that produced it."""

    __test__ = False

    feasible: bool
    candidate_evidence_hash: str
    catching_layers: tuple[str, ...]
    drift: DriftResult
    regression: RegressionResult
    invariant: InvariantResult
    read_isolated: bool            # no hidden test id observed by evolution
    holdout_intact: bool           # authority holdout matches the anchor
    round_trip_intact: bool        # Defense A: project(compile(ISR)) ≡ normalize(ISR)
    aggregate_attested: bool       # per-test precision available for protected core
    evidence_intact: bool = True   # R2.8.9: ledger chain + binding verification
    detail: str = ""

    @property
    def verdict(self) -> Verdict:
        return Verdict.ACCEPT if self.feasible else Verdict.REJECT


# -- the adversarial gate decider (info-hiding) ----------------------------------

class AdversarialGateDecider:
    """R2.8.2: composes the R2.7.5-G boundary with the R2.7 regression gate.

    Layers (each independently reject-capable):
      * read-isolation  -- hidden holdout ids never appear in evolution evidence
      * drift           -- protected immutability + evolvable causal justification
      * holdout         -- authority holdout content_hash matches the anchor
      * regression      -- outcome regression (per-test), with evolvable-gutting
                           exemption when the drift layer approved the ISR delta
      * attestation     -- aggregate-only regression is insufficient for a
                           protected core (closes the R2.6 masked-deletion hole)
    """

    __test__ = False

    def __init__(self, boundary: EvaluationAuthority | EvaluationBoundary,
                 *, parent_isr: ISR | None = None):
        self._boundary = boundary
        self._parent_isr = parent_isr

    def decide(self, protected: ProtectedTestSet,
               baseline_run: TestRunResult,
               evidence: CandidateEvidence) -> Decision:
        layers = []

        # (1) read-isolation: hidden holdout ids must not be observed by evolution.
        observed = tuple(e.test_id for e in evidence.evolution_evidence)
        iso = self._boundary.read_isolation_report(protected, observed)
        if not iso.accept:
            layers.append("visibility")

        # (2) drift classification (protected immutability; evolvable justify).
        drift = self._boundary.classify_drift(
            protected, evidence.evolution_evidence,
            causal_justification=evidence.causal_delta_accepted,
        )
        if not drift.accept:
            if drift.protected_rejected:
                layers.append("content")
            if drift.removed:
                layers.append("identity")
            if drift.hidden_leaks:
                layers.append("holdout")

        # (3) holdout integrity: authority-run hidden tests match the anchor.
        holdout_intact = self._holdout_intact(protected, evidence.holdout_evidence)
        if not holdout_intact:
            layers.append("holdout")

        # (4) regression (outcome layer).
        full_run = _assemble_run(evidence)
        reg = classify_regression(baseline_run, full_run)
        # R2.8.4: regression feasibility is gated by the ISR-derived authorization.
        reg_infeasible = regression_infeasible_with_auth(reg, evidence.authorization)

        # attestation backstop: aggregate-only is insufficient for a protected core.
        aggregate_only_insufficient = (
            reg.precision == "aggregate_only" and protected.has_protected_core
        )

        if reg_infeasible:
            layers.append("regression")
        if aggregate_only_insufficient:
            layers.append("attestation")

        # (5) R2.8.6 Defense A: structural round-trip fidelity.
        #       project(compile(ISR)) ≡ normalize(ISR)
        #       Catches compiler divergence and source-patch deviation.
        round_trip_intact = True
        if evidence.candidate_isr is not None:
            round_trip_intact = round_trip_integrity(evidence.candidate_isr)
            if not round_trip_intact:
                layers.append("structure")

        # (6) R2.8.6 Defense B: constitutional architectural integrity.
        #       candidate_ISR ⊨ invariants  AND  changes ⊆ authorized Δ
        invariant = InvariantResult()
        if (self._parent_isr is not None and evidence.candidate_isr is not None):
            arch_auth = ArchitecturalAuthorization.from_delta(
                self._parent_isr, evidence.candidate_isr,
                DeltaArchitectureProjector(),
            )
            invariants = default_fsm_invariants(self._parent_isr)
            invariant = evaluate_invariants(
                self._parent_isr, evidence.candidate_isr,
                arch_auth, invariants,
            )
            if not invariant.accept:
                layers.append("invariant")

        feasible = (not layers) and holdout_intact
        return Decision(
            feasible=feasible,
            candidate_evidence_hash=evidence.content_hash(),
            catching_layers=tuple(layers),
            drift=drift,
            regression=reg,
            invariant=invariant,
            read_isolated=iso.accept,
            holdout_intact=holdout_intact,
            round_trip_intact=round_trip_intact,
            aggregate_attested=(reg.precision == "per_test"),
            evidence_intact=True,
            detail=(
                f"catching_layers={list(layers)} drift_accept={drift.accept} "
                f"reg_accept={reg.accept} precision={reg.precision} "
                f"holdout_intact={holdout_intact} "
                f"round_trip_intact={round_trip_intact} "
                f"invariant_accept={invariant.accept}"
            ),
        )
    @staticmethod
    def _holdout_intact(protected: ProtectedTestSet,
                        holdout_evidence: tuple[TestExecution, ...]) -> bool:
        hid = {t.test_id: t for t in protected.identities if t.is_hidden()}
        seen = {e.test_id: e for e in holdout_evidence}
        # every anchored holdout must be present, content-matched, and passing
        for tid, ident in hid.items():
            ev = seen.get(tid)
            if (ev is None or ev.content_hash != ident.content_hash
                    or ev.outcome != TestOutcome.PASSED):
                return False
        # no stray holdout ids in evidence that aren't anchored
        if any(tid not in hid for tid in seen):
            return False
        return True


def _assemble_run(evidence: CandidateEvidence) -> TestRunResult:
    """The candidate's self-reported run = its VISIBLE evidence only.

    Holdout evidence is authority-run and verified separately (see
    ``_holdout_intact``); it is not part of the candidate's run for the
    regression diff, precisely so a candidate cannot smuggle holdout pass
    counts into the visible-surface comparison.
    """
    tests = evidence.evolution_evidence
    failed = sum(1 for t in tests if t.outcome in (TestOutcome.FAILED, TestOutcome.ERROR))
    return TestRunResult(
        passed=(failed == 0), exit_code=(0 if failed == 0 else 1),
        total_tests=len(tests), failed_tests=failed, tests=tests,
    )


# -- mutation application (pure, deterministic) ----------------------------------
# Each apply takes the anchored baseline surface (for id roles) and the clean
# baseline run, and returns the CandidateEvidence the gate will see.

MutationApp = Callable[[ProtectedTestSet, TestRunResult], CandidateEvidence]


def _drop(*ids: str) -> tuple[TestExecution, ...]:
    """Visible baseline evidence minus the given ids (a deletion/discovery kill)."""
    return tuple(t for t in _visible_baseline_evidence() if t.test_id not in ids)


def _swap_content(tid: str, new_hash: str) -> tuple[TestExecution, ...]:
    base = _visible_baseline_evidence()
    return tuple(
        t if t.test_id != tid else t.model_copy(update={"content_hash": new_hash})
        for t in base
    )


def _skip(tid: str) -> tuple[TestExecution, ...]:
    base = _visible_baseline_evidence()
    return tuple(
        t if t.test_id != tid else t.model_copy(update={"outcome": TestOutcome.SKIPPED})
        for t in _visible_baseline_evidence()
    )


def apply_delete_protected(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    return CandidateEvidence(
        evolution_evidence=_drop(ID_REG_AWAIT),
        holdout_evidence=_holdout_run(),
        causal_delta_accepted=False,
    )


def apply_rename_protected(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    base = _visible_baseline_evidence()
    renamed = tuple(
        t if t.test_id != ID_REG_AWAIT
        else t.model_copy(update={"test_id": ID_REG_AWAIT + "::v2"})
        for t in base
    )
    return CandidateEvidence(
        evolution_evidence=renamed,
        holdout_evidence=_holdout_run(),
        causal_delta_accepted=False,
    )


def apply_skip_protected(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    return CandidateEvidence(
        evolution_evidence=_skip(ID_REG_AWAIT),
        holdout_evidence=_holdout_run(),
        causal_delta_accepted=False,
    )


def apply_weaken_assertion(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    return CandidateEvidence(
        evolution_evidence=_swap_content(ID_REG_AWAIT, "sha256:await_WEAKENED"),
        holdout_evidence=_holdout_run(),
        causal_delta_accepted=False,
    )


def apply_remove_assertion(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    return CandidateEvidence(
        evolution_evidence=_swap_content(ID_REG_ERR, "sha256:err_NOASSERT"),
        holdout_evidence=_holdout_run(),
        causal_delta_accepted=False,
    )


def apply_alter_fixture(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    return CandidateEvidence(
        evolution_evidence=_swap_content(ID_REG_DEADLOCK, "sha256:deadlock_NEWFIXTURE"),
        holdout_evidence=_holdout_run(),
        causal_delta_accepted=False,
    )


def apply_disable_discovery(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    return CandidateEvidence(
        evolution_evidence=_drop(ID_REG_AWAIT),
        holdout_evidence=_holdout_run(),
        causal_delta_accepted=False,
    )


def apply_aggregate_mimic_delete(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    """R2.6 hole: the candidate suppresses per-test outcomes (visible surface
    empty) and hopes the regression gate's aggregate-only fallback (pass-count
    comparison) masks the deletion.

    The holdout is authority-run, so it stays present and matched -- the attack
    targets only the visible self-reported surface. The attestation layer
    (protected core + aggregate-only precision) is what rejects it.
    """
    return CandidateEvidence(
        evolution_evidence=(),           # visible per-test surface suppressed
        holdout_evidence=_holdout_run(),  # authority still ran the holdout
        causal_delta_accepted=False,
    )


# -- legitimate-evolution controls ----------------------------------------------

def _canary_isr_pair():
    """ISRs for the legit-evolvable repair (R2.8.4 authorization basis).

    The parent ISR has the canary transition in a *broken* state; the candidate
    ISR has it *repaired*. The behavior-transition diff is the causal delta the
    drift layer accepts, and the projector maps it to the canary test id.
    """
    from constitutional_architecture.isr.model import (
        ISR, System, Module, Workflow, WorkflowState, WorkflowTransition,
        StateType,
    )
    def _isr(from_state_id: str, to_state_id: str) -> ISR:
        wf = Workflow(
            id="canary_wf", name="canary_wf",
            states=(
                WorkflowState(id="start", name="start", state_type=StateType.INITIAL),
                WorkflowState(id=from_state_id, name=from_state_id,
                              state_type=StateType.INTERMEDIATE),
                WorkflowState(id=to_state_id, name=to_state_id,
                              state_type=StateType.FINAL),
            ),
            transitions=(
                WorkflowTransition(id="t", name="step",
                                   from_state_id=from_state_id, to_state_id=to_state_id),
            ),
        )
        return ISR(system=System(id="s", name="S",
                                 modules=(Module(id="m", name="M", workflows=(wf,)),)))

    return _isr("canary", "broken"), _isr("canary", "repaired")


def _canary_projector(parent: "object", candidate: "object") -> frozenset[str]:
    """Corpus-specific projector: maps the canary behavior-diff to the canary id."""
    changed = (
        FSMTestSurfaceProjector._behaviors(parent)  # noqa: SLF001
        ^ FSMTestSurfaceProjector._behaviors(candidate)  # noqa: SLF001
    )
    return frozenset({ID_EVOLVABLE_CANARY}) if changed else frozenset()


class _CanaryProjector:
    """Corpus projector: maps canary ISR transition-diff to the canary test id.

    Analogous to ``FSMTestSurfaceProjector`` but keyed to the corpus's
    ``ev::mutation_score_canary`` flat id.
    """

    __test__ = False

    def project(self, parent_isr: "object", candidate_isr: "object") -> frozenset[str]:
        return _canary_projector(parent_isr, candidate_isr)


class _WrongProjector:
    """Attack-D projector: authorizes a *different* test id from the gutting target.

    Models the case where the ISR delta's behavior change does not map to the
    test id being guttered -- the R2.8.4 authorization must reject it.
    """

    __test__ = False

    def project(self, parent_isr: "object", candidate_isr: "object") -> frozenset[str]:
        return frozenset({"ev::unrelated_change"})


def apply_legit_no_test_edit(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    return CandidateEvidence(
        evolution_evidence=_visible_baseline_evidence(),
        holdout_evidence=_holdout_run(),
        causal_delta_accepted=False,
    )


def apply_legit_edit_evolvable(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    """A repair that legitimately edits the evolvable test, with a causal ISR delta.

    The ``Authorization`` is **derived from the ISR delta** via the
    canary projector -- never hand-injected by the mutation harness (R2.8.4).
    """
    base = _visible_baseline_evidence()
    edited = tuple(
        t if t.test_id != ID_EVOLVABLE_CANARY
        else t.model_copy(update={"content_hash": "sha256:canary_REPAIRED"})
        for t in base
    )
    parent_isr, candidate_isr = _canary_isr_pair()
    authorization = Authorization.from_delta(
        parent_isr, candidate_isr, _CanaryProjector(),
    )
    return CandidateEvidence(
        evolution_evidence=edited,
        holdout_evidence=_holdout_run(),
        causal_delta_accepted=True,
        authorization=authorization,
    )


# -- R2.8.4 Attack D: unauthorized evolvable gutting -----------------------------

def apply_attack_d_unauthorized_gutting(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    """Attack D: gutter the evolvable canary with an ISR authorization that does NOT cover it.

    The drift layer accepts (evolvable + causal_delta_accepted), but the R2.8.4
    authorization's projection covers a *different* test id -- so the regression
    layer must reject the unauthorized gutting. This is the precise improvement
    over R2.7.5-G, which would have permitted ANY evolvable gutting.
    """
    base = _visible_baseline_evidence()
    edited = tuple(
        t if t.test_id != ID_EVOLVABLE_CANARY
        else t.model_copy(update={"content_hash": "sha256:canary_WEAKENED"})
        for t in base
    )
    parent_isr, candidate_isr = _canary_isr_pair()
    authorization = Authorization.from_delta(
        parent_isr, candidate_isr, _WrongProjector(),
    )
    return CandidateEvidence(
        evolution_evidence=edited,
        holdout_evidence=_holdout_run(),
        causal_delta_accepted=True,
        authorization=authorization,
    )


# -- R2.8.5: behavioral masking --------------------------------------------------
# ISR-level masks that pass the visible surface (read-isolation prevents the
# candidate from seeing holdout inputs) but are caught by the holdout surface.
# The mask is encoded in the ISR (guard_condition / actions), not the test surface.

def _masked_holdout_diff_content() -> tuple[TestExecution, ...]:
    """Holdout content-hash changed -- the mask altered behavior on unseen input."""
    return (TestExecution(
        test_id=ID_HOLDOUT, outcome=TestOutcome.PASSED,
        content_hash="sha256:holdout_MASK_DETECTED",
    ),)


def _masked_holdout_failed() -> tuple[TestExecution, ...]:
    """Holdout test fails -- the mask broke behavior on unseen input."""
    return (TestExecution(
        test_id=ID_HOLDOUT, outcome=TestOutcome.FAILED,
        content_hash=_H_HOLDOUT,
    ),)


def apply_mask_special_case_input(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    """ISR-level mask: guard condition special-cases a visible input.

    Visible tests still pass (the special-case only fires for inputs not in the
    visible suite), but the holdout surface -- run authoritatively on unseen
    inputs -- reveals the behavioral divergence via content-hash mismatch.
    """
    return CandidateEvidence(
        evolution_evidence=_visible_baseline_evidence(),
        holdout_evidence=_masked_holdout_diff_content(),
        causal_delta_accepted=False,
    )


def apply_mask_early_return(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    """ISR-level mask: early-return short-circuits on the happy path.

    Visible tests pass (they exercise the happy path), but the holdout
    surface hits an edge case the short-circuit doesn't handle, producing
    a failure the candidate cannot anticipate (read-isolation).
    """
    return CandidateEvidence(
        evolution_evidence=_visible_baseline_evidence(),
        holdout_evidence=_masked_holdout_failed(),
        causal_delta_accepted=False,
    )


def apply_mask_fabricated_result(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    """ISR-level mask: fabricated/hardcoded result for a specific transition.

    Visible tests pass (the fabricated result happens to match on visible
    inputs), but the holdout surface exposes the fabrication via a real
    computation mismatch.
    """
    return CandidateEvidence(
        evolution_evidence=_visible_baseline_evidence(),
        holdout_evidence=_masked_holdout_failed(),
        causal_delta_accepted=False,
    )


def apply_mask_invisible_on_all_inputs(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    """Control: a mask that is behaviorally invisible on all inputs is harmless.

    Passes everything -- visible, holdout, no divergence. Not a real attack;
    included so the corpus distinguishes detectable masks from no-ops.
    """
    return CandidateEvidence(
        evolution_evidence=_visible_baseline_evidence(),
        holdout_evidence=_holdout_run(),
        causal_delta_accepted=False,
    )


# -- R2.8.6: architectural integrity ---------------------------------------------

def _canonical_arch_isr() -> ISR:
    """The baseline ISR whose architectural skeleton is the protected surface.

    Encodes: one module with an auth-protected operation, one stateful
    service, one internal dependency (boundary), and a workflow.
    """
    from constitutional_architecture.isr.model.system import System
    from constitutional_architecture.isr.model.module import Module
    from constitutional_architecture.isr.model.service import (
        Service, ServiceDependency, Operation, OperationType,
    )
    from constitutional_architecture.isr.model.workflow import (
        Workflow, WorkflowState, WorkflowTransition, StateType,
    )
    from constitutional_architecture.isr.model.interface import (
        Interface, InterfaceType, Endpoint, HttpMethod,
    )

    wf = Workflow(
        id="order_wf", name="order_workflow",
        states=(
            WorkflowState(id="start", name="start", state_type=StateType.INITIAL),
            WorkflowState(id="processing", name="processing", state_type=StateType.INTERMEDIATE),
            WorkflowState(id="fin", name="fin", state_type=StateType.FINAL),
        ),
        transitions=(
            WorkflowTransition(id="t1", name="submit", from_state_id="start", to_state_id="processing"),
            WorkflowTransition(id="t2", name="complete", from_state_id="processing", to_state_id="fin"),
        ),
    )

    svc = Service(
        id="order_svc", name="order_service", is_stateless=False,
        operations=(
            Operation(
                id="place_order", name="place_order",
                operation_type=OperationType.COMMAND,
                required_permissions=("order:create",), is_public=False,
            ),
        ),
    )

    iface = Interface(
        id="order_iface", name="order_interface",
        interface_type=InterfaceType.REST, is_internal=True,
        endpoints=(
            Endpoint(id="ep_place", name="place_order_ep",
                     method=HttpMethod.POST, path="/orders",
                     required_permissions=("order:create",), is_public=False),
        ),
    )

    return ISR(
        system=System(
            id="order-system", name="Order System",
            modules=(
                Module(
                    id="order", name="Order Module",
                    services=(svc,),
                    workflows=(wf,),
                    interfaces=(iface,),
                    dependencies=("payment",),
                ),
                Module(id="payment", name="Payment Module"),
            ),
        ),
        provenance=ISRProvenance(created_at="2025-01-01T00:00:00+00:00"),
    )


def _isr_without_auth(parent_isr: ISR) -> ISR:
    """Strip auth from the protected operation (constitutional violation)."""
    mod = parent_isr.system.modules[0]
    svc = mod.services[0]
    op = svc.operations[0]
    no_auth_op = replace(op, required_permissions=())
    no_auth_svc = replace(svc, operations=(no_auth_op,))
    no_auth_mod = replace(mod, services=(no_auth_svc,))
    no_auth_iface = replace(mod.interfaces[0], endpoints=tuple(replace(ep, required_permissions=(), is_public=True) for ep in mod.interfaces[0].endpoints))
    no_auth_mod2 = replace(no_auth_mod, interfaces=(no_auth_iface,))
    new_sys = replace(parent_isr.system, modules=(no_auth_mod2, parent_isr.system.modules[1]))
    return replace(parent_isr, system=new_sys)


def _isr_stateless_degradation(parent_isr: ISR) -> ISR:
    """Change the stateful service to stateless (constitutional violation)."""
    mod = parent_isr.system.modules[0]
    svc = mod.services[0]
    stateless_svc = replace(svc, is_stateless=True)
    no_auth_mod = replace(mod, services=(stateless_svc,))
    new_sys = replace(parent_isr.system, modules=(no_auth_mod, parent_isr.system.modules[1]))
    return replace(parent_isr, system=new_sys)


def _isr_remove_boundary(parent_isr: ISR) -> ISR:
    """Remove the module dependency (boundary removal)."""
    mod = parent_isr.system.modules[0]
    no_dep_mod = replace(mod, dependencies=())
    new_sys = replace(parent_isr.system, modules=(no_dep_mod, parent_isr.system.modules[1]))
    return replace(parent_isr, system=new_sys)


def _isr_legit_arch_change(parent_isr: ISR) -> ISR:
    """Add a NEW dependency not present before (declared architectural change)."""
    mod = parent_isr.system.modules[0]
    new_dep_mod = replace(mod, dependencies=("payment", "notification"))
    notification = Module(id="notification", name="Notification Module")
    new_sys = replace(parent_isr.system, modules=(new_dep_mod, parent_isr.system.modules[1], notification))
    return replace(parent_isr, system=new_sys)


def apply_arch_auth_removal(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    """R2.8.6: remove auth from a protected operation (constitutional violation)."""
    parent_isr = _canonical_arch_isr()
    candidate = _isr_without_auth(parent_isr)
    return CandidateEvidence(
        evolution_evidence=_visible_baseline_evidence(),
        holdout_evidence=_holdout_run(),
        causal_delta_accepted=False,
        candidate_isr=candidate,
    )


def apply_arch_persistence_degradation(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    """R2.8.6: downgrade a stateful service to stateless (constitutional violation)."""
    parent_isr = _canonical_arch_isr()
    candidate = _isr_stateless_degradation(parent_isr)
    return CandidateEvidence(
        evolution_evidence=_visible_baseline_evidence(),
        holdout_evidence=_holdout_run(),
        causal_delta_accepted=False,
        candidate_isr=candidate,
    )


def apply_arch_remove_boundary(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    """R2.8.6: silently remove a module dependency (boundary violation).

    The boundary removal is NOT authorized by any ISR delta (no
    architectural authorization is provided) -- the invariant layer
    must catch it as an undeclared architectural change.
    """
    parent_isr = _canonical_arch_isr()
    candidate = _isr_remove_boundary(parent_isr)
    return CandidateEvidence(
        evolution_evidence=_visible_baseline_evidence(),
        holdout_evidence=_holdout_run(),
        causal_delta_accepted=False,
        candidate_isr=candidate,
    )


def apply_arch_legit_declared_change(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    """R2.8.6 control: declared architectural evolution (new dependency).

    The ISR delta declares the new dependency, so the architectural
    authorization covers it -- the candidate is accepted.
    """
    parent_isr = _canonical_arch_isr()
    candidate = _isr_legit_arch_change(parent_isr)
    arch_auth = ArchitecturalAuthorization.from_delta(
        parent_isr, candidate, DeltaArchitectureProjector(),
    )
    return CandidateEvidence(
        evolution_evidence=_visible_baseline_evidence(),
        holdout_evidence=_holdout_run(),
        causal_delta_accepted=True,
        candidate_isr=candidate,
    )


# -- the matrix -----------------------------------------------------------------

@dataclass(frozen=True)
class MutationSpec:
    """A single row of the R2.8.2 mutation matrix.

    The matrix is data-driven: tests iterate it and assert each row's declared
    expectations against the decider's actual verdict. This makes the corpus the
    permanent, auditable artifact for R2.8.14 certification.
    """

    __test__ = False

    mutation_id: str
    attack_surface: AttackSurface
    is_control: bool
    expected_feasibility: str            # "infeasible" | "feasible"
    expected_catching_layers: tuple[str, ...]
    expected_drift_class: str            # DriftClass.value or "accepted"
    expected_holdout_invariant: str
    apply: MutationApp
    expected_holdout_intact: bool = True


MUTATION_MATRIX: tuple[MutationSpec, ...] = (
    MutationSpec(
        mutation_id="DELETE_PROTECTED_TEST",
        attack_surface=AttackSurface.IDENTITY,
        is_control=False,
        expected_feasibility="infeasible",
        expected_catching_layers=("identity",),
        expected_drift_class=DriftClass.REMOVED_TEST.value,
        expected_holdout_invariant="hidden holdout unchanged",
        apply=apply_delete_protected,
    ),
    MutationSpec(
        mutation_id="RENAME_PROTECTED_TEST",
        attack_surface=AttackSurface.IDENTITY,
        is_control=False,
        expected_feasibility="infeasible",
        expected_catching_layers=("identity",),
        expected_drift_class=DriftClass.REMOVED_TEST.value,
        expected_holdout_invariant="hidden holdout unchanged",
        apply=apply_rename_protected,
    ),
    MutationSpec(
        mutation_id="SKIP_PROTECTED_TEST",
        attack_surface=AttackSurface.DISCOVERY,
        is_control=False,
        expected_feasibility="infeasible",
        expected_catching_layers=("regression",),
        expected_drift_class="accepted",
        expected_holdout_invariant="hidden holdout unchanged",
        apply=apply_skip_protected,
    ),
    MutationSpec(
        mutation_id="WEAKEN_ASSERTION_PROTECTED",
        attack_surface=AttackSurface.CONTENT,
        is_control=False,
        expected_feasibility="infeasible",
        expected_catching_layers=("content",),
        expected_drift_class=DriftClass.CONTENT_GUTTING.value,
        expected_holdout_invariant="hidden holdout unchanged",
        apply=apply_weaken_assertion,
    ),
    MutationSpec(
        mutation_id="REMOVE_ASSERTION_PROTECTED",
        attack_surface=AttackSurface.CONTENT,
        is_control=False,
        expected_feasibility="infeasible",
        expected_catching_layers=("content",),
        expected_drift_class=DriftClass.CONTENT_GUTTING.value,
        expected_holdout_invariant="hidden holdout unchanged",
        apply=apply_remove_assertion,
    ),
    MutationSpec(
        mutation_id="ALTER_FIXTURE_PROTECTED",
        attack_surface=AttackSurface.CONTENT,
        is_control=False,
        expected_feasibility="infeasible",
        expected_catching_layers=("content",),
        expected_drift_class=DriftClass.CONTENT_GUTTING.value,
        expected_holdout_invariant="hidden holdout unchanged",
        apply=apply_alter_fixture,
    ),
    MutationSpec(
        mutation_id="DISABLE_DISCOVERY_PROTECTED",
        attack_surface=AttackSurface.DISCOVERY,
        is_control=False,
        expected_feasibility="infeasible",
        expected_catching_layers=("identity",),
        expected_drift_class=DriftClass.REMOVED_TEST.value,
        expected_holdout_invariant="hidden holdout unchanged",
        apply=apply_disable_discovery,
    ),
    MutationSpec(
        mutation_id="AGGREGATE_MIMIC_DELETE",
        attack_surface=AttackSurface.DISCOVERY,
        is_control=False,
        expected_feasibility="infeasible",
        expected_catching_layers=("identity", "attestation"),
        expected_drift_class=DriftClass.REMOVED_TEST.value,
        expected_holdout_invariant="hidden holdout unchanged",
        apply=apply_aggregate_mimic_delete,
    ),
    MutationSpec(
        mutation_id="LEGIT_REPAIR_NO_TEST_EDIT",
        attack_surface=AttackSurface.CONTENT,
        is_control=True,
        expected_feasibility="feasible",
        expected_catching_layers=(),
        expected_drift_class="accepted",
        expected_holdout_invariant="hidden holdout unchanged",
        apply=apply_legit_no_test_edit,
    ),
    MutationSpec(
        mutation_id="LEGIT_REPAIR_EDIT_EVOLVABLE_TEST",
        attack_surface=AttackSurface.CONTENT,
        is_control=True,
        expected_feasibility="feasible",
        expected_catching_layers=(),
        expected_drift_class="allowed_drift",
        expected_holdout_invariant="hidden holdout unchanged",
        apply=apply_legit_edit_evolvable,
    ),
    MutationSpec(
        mutation_id="UNAUTHORIZED_EVOLVABLE_GUTTING",
        attack_surface=AttackSurface.CONTENT,
        is_control=False,
        expected_feasibility="infeasible",
        expected_catching_layers=("regression",),
        expected_drift_class="allowed_drift",
        expected_holdout_invariant="hidden holdout unchanged",
        apply=apply_attack_d_unauthorized_gutting,
    ),
    # -- R2.8.5: behavioral masking ----------------------------------------------
    MutationSpec(
        mutation_id="MASK_SPECIAL_CASE_INPUT",
        attack_surface=AttackSurface.BEHAVIOR,
        is_control=False,
        expected_feasibility="infeasible",
        expected_catching_layers=("holdout",),
        expected_drift_class="preserved",
        expected_holdout_invariant="holdout detects behavioral divergence",
        expected_holdout_intact=False,
        apply=apply_mask_special_case_input,
    ),
    MutationSpec(
        mutation_id="MASK_EARLY_RETURN",
        attack_surface=AttackSurface.BEHAVIOR,
        is_control=False,
        expected_feasibility="infeasible",
        expected_catching_layers=("holdout",),
        expected_drift_class="preserved",
        expected_holdout_invariant="holdout detects behavioral divergence",
        expected_holdout_intact=False,
        apply=apply_mask_early_return,
    ),
    MutationSpec(
        mutation_id="MASK_FABRICATED_RESULT",
        attack_surface=AttackSurface.BEHAVIOR,
        is_control=False,
        expected_feasibility="infeasible",
        expected_catching_layers=("holdout",),
        expected_drift_class="preserved",
        expected_holdout_invariant="holdout detects behavioral divergence",
        expected_holdout_intact=False,
        apply=apply_mask_fabricated_result,
    ),
    MutationSpec(
        mutation_id="MASK_INVISIBLE_ON_ALL_INPUTS",
        attack_surface=AttackSurface.BEHAVIOR,
        is_control=True,
        expected_feasibility="feasible",
        expected_catching_layers=(),
        expected_drift_class="preserved",
        expected_holdout_invariant="hidden holdout unchanged",
        apply=apply_mask_invisible_on_all_inputs,
    ),
    # -- R2.8.6: architectural integrity -----------------------------------------
    # Defense A (round-trip fidelity) + Defense B (constitutional invariants).
    # These mutations carry candidate_isr so the decider can normalize and check.
    MutationSpec(
        mutation_id="ARCH_AUTH_REMOVAL",
        attack_surface=AttackSurface.BEHAVIOR,
        is_control=False,
        expected_feasibility="infeasible",
        expected_catching_layers=("invariant",),
        expected_drift_class="preserved",
        expected_holdout_invariant="hidden holdout unchanged",
        expected_holdout_intact=True,
        apply=apply_arch_auth_removal,
    ),
    MutationSpec(
        mutation_id="ARCH_PERSISTENCE_DEGRADATION",
        attack_surface=AttackSurface.BEHAVIOR,
        is_control=False,
        expected_feasibility="infeasible",
        expected_catching_layers=("invariant",),
        expected_drift_class="preserved",
        expected_holdout_invariant="hidden holdout unchanged",
        expected_holdout_intact=True,
        apply=apply_arch_persistence_degradation,
    ),
    MutationSpec(
        mutation_id="ARCH_BOUNDARY_REMOVAL",
        attack_surface=AttackSurface.BEHAVIOR,
        is_control=False,
        expected_feasibility="infeasible",
        expected_catching_layers=("invariant",),
        expected_drift_class="preserved",
        expected_holdout_invariant="hidden holdout unchanged",
        expected_holdout_intact=True,
        apply=apply_arch_remove_boundary,
    ),
    MutationSpec(
        mutation_id="ARCH_LEGIT_DECLARED_CHANGE",
        attack_surface=AttackSurface.BEHAVIOR,
        is_control=True,
        expected_feasibility="feasible",
        expected_catching_layers=(),
        expected_drift_class="preserved",
        expected_holdout_invariant="hidden holdout unchanged",
        expected_holdout_intact=True,
        apply=apply_arch_legit_declared_change,
    ),
)



# -- R2.8.11: adversarial composition ---------------------------------------------

def apply_weaken_plus_mask(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    """Composition: weaken visible assertion (content) + mask holdout content (holdout).

    Individual: weaken → caught by content/attestation; mask → caught by holdout.
    Composed: both layers must still fire independently.
    """
    weakened = tuple(
        t if t.test_id != ID_REG_AWAIT
        else t.model_copy(update={"content_hash": "sha256:await_WEAKENED"})
        for t in _visible_baseline_evidence()
    )
    return CandidateEvidence(
        evolution_evidence=weakened,
        holdout_evidence=_masked_holdout_diff_content(),
        causal_delta_accepted=False,
    )


def apply_delete_plus_mask(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    """Composition: delete visible test (identity) + mask holdout content (holdout)."""
    base = _visible_baseline_evidence()
    evolution = tuple(t for t in base if t.test_id != ID_REG_AWAIT)
    return CandidateEvidence(
        evolution_evidence=evolution,
        holdout_evidence=_masked_holdout_diff_content(),
        causal_delta_accepted=False,
    )


def apply_arch_boundary_plus_mask(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    """Composition: remove architectural boundary (invariant) + mask holdout (holdout)."""
    parent_isr = _canonical_arch_isr()
    candidate = _isr_remove_boundary(parent_isr)
    return CandidateEvidence(
        evolution_evidence=_visible_baseline_evidence(),
        holdout_evidence=_masked_holdout_diff_content(),
        causal_delta_accepted=False,
        candidate_isr=candidate,
    )


def apply_arch_auth_removal_plus_mask(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    """Composition: remove architectural auth (invariant) + mask holdout (holdout)."""
    parent_isr = _canonical_arch_isr()
    candidate = _isr_without_auth(parent_isr)
    return CandidateEvidence(
        evolution_evidence=_visible_baseline_evidence(),
        holdout_evidence=_masked_holdout_diff_content(),
        causal_delta_accepted=False,
        candidate_isr=candidate,
    )


def apply_composed_control_single(_: ProtectedTestSet, __: TestRunResult) -> CandidateEvidence:
    """Control: a legitimate candidate (no attacks) must be accepted."""
    return CandidateEvidence(
        evolution_evidence=_visible_baseline_evidence(),
        holdout_evidence=_holdout_run(),
        causal_delta_accepted=False,
    )


@dataclass(frozen=True)
class ComposedMutationSpec:
    """A composed adversarial mutation: an ordered sequence of atomic mutations
    applied to a single candidate.

    Adversarial hypothesis: attacks caught individually by dedicated layers may,
    when combined, (a) cancel each other's signal, (b) overload attribution, or
    (c) produce collectively benign-looking evidence.

    Information-hiding invariant: component_ids is HARNESS metadata used for
    scoring. It never flows into CandidateEvidence and never reaches the gate.
    """

    __test__ = False

    composition_id: str
    component_ids: tuple[str, ...]
    expected_verdict: Verdict
    expected_catching_layers: frozenset[str]
    expected_holdout_intact: bool
    attack_surface: AttackSurface = AttackSurface.COMPOSED
    rationale: str = ""





COMPOSED_MUTATION_MATRIX: tuple["ComposedMutationSpec", ...] = (
    ComposedMutationSpec(
        composition_id="COMPOSE_WEAKEN_PLUS_MASK",
        component_ids=("WEAKEN_ASSERTION", "MASK_SPECIAL_CASE"),
        expected_verdict=Verdict.REJECT,
        expected_catching_layers=frozenset({"regression", "holdout"}),
        expected_holdout_intact=False,
        rationale="Weaken visible assertion AND mask holdout. Both layers must "
                "still fire independently.",
    ),
    ComposedMutationSpec(
        composition_id="COMPOSE_DELETE_PLUS_FORGE",
        component_ids=("DELETE_TEST", "AGGREGATE_MIMIC"),
        expected_verdict=Verdict.REJECT,
        expected_catching_layers=frozenset({"identity", "attestation"}),
        expected_holdout_intact=True,
        rationale="Delete visible test (identity) AND forge aggregate counts "
                "(attestation). The R2.6 masked-deletion hole composed with forgery.",
    ),
    ComposedMutationSpec(
        composition_id="COMPOSE_SKIP_PLUS_MASK",
        component_ids=("SKIP_TEST", "MASK_EARLY_RETURN"),
        expected_verdict=Verdict.REJECT,
        expected_catching_layers=frozenset({"regression", "holdout"}),
        expected_holdout_intact=False,
        rationale="Skip visible test (regression) AND early-return mask (holdout).",
    ),
    ComposedMutationSpec(
        composition_id="COMPOSE_RENAME_PLUS_GUT",
        component_ids=("RENAME_TEST", "REMOVE_ASSERTION"),
        expected_verdict=Verdict.REJECT,
        expected_catching_layers=frozenset({"identity", "content"}),
        expected_holdout_intact=True,
        rationale="Rename to evade identity tracking (identity) AND remove an "
                "assertion on a *different* protected test (content). "
                "Two evidence layers attacked at once, on distinct tests.",
    ),
    ComposedMutationSpec(
        composition_id="COMPOSE_GUT_PLUS_FABRICATE",
        component_ids=("UNAUTHORIZED_EVOLVABLE_GUTTING", "MASK_FABRICATED_RESULT"),
        expected_verdict=Verdict.REJECT,
        expected_catching_layers=frozenset({"regression", "holdout"}),
        expected_holdout_intact=False,
        rationale="Gut evolvable canary under wrong authorization (regression) "
                "AND fabricate holdout result (holdout).",
    ),
    ComposedMutationSpec(
        composition_id="COMPOSE_DISCOVERY_PLUS_MASK",
        component_ids=("DISABLE_DISCOVERY", "MASK_EARLY_RETURN"),
        expected_verdict=Verdict.REJECT,
        expected_catching_layers=frozenset({"identity", "holdout"}),
        expected_holdout_intact=False,
        rationale="Suppress visible test discovery (identity) AND mask holdout "
                "(holdout). Discovery tampering composed with masking.",
    ),
    ComposedMutationSpec(
        composition_id="COMPOSE_TRIPLE_DELETE_FORGE_MASK",
        component_ids=("DELETE_TEST", "AGGREGATE_MIMIC", "MASK_SPECIAL_CASE"),
        expected_verdict=Verdict.REJECT,
        expected_catching_layers=frozenset({"identity", "attestation", "holdout"}),
        expected_holdout_intact=False,
        rationale="Depth-3 attack: delete (identity), forge aggregate (attestation), "
                "mask holdout behavior (holdout).",
    ),
    # Control: a legitimate repair run through the composer must remain accepted.
    ComposedMutationSpec(
        composition_id="COMPOSED_CONTROL_SINGLE",
        component_ids=("LEGIT_REPAIR_NO_TEST_EDIT",),
        expected_verdict=Verdict.ACCEPT,
        expected_catching_layers=frozenset(),
        expected_holdout_intact=True,
        rationale="Control: a legitimate repair as a 1-element composition must "
                "still be accepted.",
    ),
)

class MutationLab:
    """Convenience facade: surfaces the canonical corpus + a decider."""

    def __init__(self, *, evolution_id: str = "r2.8.2", environment_fingerprint: str = "fsm-r2.8.2"):
        self.authority = EvaluationAuthority()
        self.ledger = EvolutionLedger()
        self.boundary = EvaluationBoundary(
            authority=self.authority, ledger=self.ledger, evolution_id=evolution_id,
        )
        self.surface = canonical_fsm_surface(
            self.authority, self.boundary, environment_fingerprint=environment_fingerprint,
        )
        self.baseline_run = canonical_baseline_visible_run()
        self.decider = AdversarialGateDecider(self.boundary, parent_isr=_canonical_arch_isr())



# =====================================================================
# R2.8.12 -- Adversarial Composition
# =====================================================================
# Composition is a *harness* concern, not a gate concern. The composer knows
# it is stacking DELETE_TEST + AGGREGATE_MIMIC; the gate must not. The composed
# candidate produces CandidateEvidence structurally identical to an atomic
# mutation's evidence -- no composition field, no component list. If the gate
# could see "this is a composition," it would be a blacklist by another name.
#
# R2.8.12 reuses the atomic appliers from R2.8.2/R2.8.4/R2.8.5; it introduces no
# new mutation semantics, only their composition.

@dataclass(frozen=True)
class Baseline:
    """Anchored baseline for composition: the protected surface + the clean run.

    Passed to the composer so it can derive the expected holdout identity set
    (for verifying holdout_intact after composition)."""
    protected: "ProtectedTestSet"
    baseline_run: "TestRunResult"


class UnknownMutationError(KeyError):
    """Raised when a component_id has no registered atomic applier."""


ComposedApp = "MutationApp"


# Component-id -> applier-function registry. Maps the short names used in
# COMPOSED_MUTATION_MATRIX to the existing atomic appliers from R2.8.2/4/5.
_COMPOSER_REGISTRY: dict[str, "MutationApp"] = {
    "DELETE_TEST": apply_delete_protected,
    "RENAME_TEST": apply_rename_protected,
    "SKIP_TEST": apply_skip_protected,
    "WEAKEN_ASSERTION": apply_weaken_assertion,
    "REMOVE_ASSERTION": apply_remove_assertion,
    "REMOVE_ASSERTION_PROTECTED": apply_remove_assertion,
    "ALTER_FIXTURE": apply_alter_fixture,
    "AGGREGATE_MIMIC": apply_aggregate_mimic_delete,
    "UNAUTHORIZED_GUTTING": apply_attack_d_unauthorized_gutting,
    "UNAUTHORIZED_EVOLVABLE_GUTTING": apply_attack_d_unauthorized_gutting,
    "MASK_SPECIAL_CASE": apply_mask_special_case_input,
    "MASK_EARLY_RETURN": apply_mask_early_return,
    "MASK_FABRICATED": apply_mask_fabricated_result,
    "MASK_FABRICATED_RESULT": apply_mask_fabricated_result,
    "ARCH_AUTH_REMOVAL": apply_arch_auth_removal,
    "ARCH_BOUNDARY_REMOVAL": apply_arch_remove_boundary,
    "ARCH_PERSISTENCE_DEGRADATION": apply_arch_persistence_degradation,
    "DISABLE_DISCOVERY": apply_disable_discovery,
    "LEGIT_REPAIR_NO_TEST_EDIT": apply_legit_no_test_edit,
}




def _merge_test_tuples(
    current: tuple[TestExecution, ...],
    component: tuple[TestExecution, ...],
    baseline: tuple[TestExecution, ...],
) -> tuple[TestExecution, ...]:
    """Merge per-test deltas from *component* (relative to *baseline*) into
    *current*, preserving changes that earlier components already applied.

    Positional mapping: mutations in this corpus preserve test order, so
    position ``i`` in every tuple refers to the same baseline test. When the
    component renamed, re-hashed, or re-outcomed test ``i``, we propagate only
    that delta onto the already-merged evidence (so a rename from component A
    and a content-hash change from component B both survive).
    """
    if len(component) != len(baseline):
        # Length differs (deletion / suppression): component wholesale replaces
        # the visible surface, which is the correct behaviour for those mutations.
        return component

    merged = list(current)
    for i in range(len(merged)):
        if i >= len(baseline):
            break
        base_t = baseline[i]
        comp_t = component[i]
        if comp_t == base_t:
            continue  # component left this test unchanged — keep merged as-is

        curr_t = merged[i]
        updates: dict = {}
        if comp_t.test_id != base_t.test_id:
            updates["test_id"] = comp_t.test_id
        if comp_t.content_hash != base_t.content_hash:
            updates["content_hash"] = comp_t.content_hash
        if comp_t.outcome != base_t.outcome:
            updates["outcome"] = comp_t.outcome
        if updates:
            merged[i] = curr_t.model_copy(update=updates)

    return tuple(merged)


class MutationComposer:
    """Applies an ordered sequence of atomic mutations to one candidate.

    Deterministic: identical component_ids order + seed -> identical evidence_hash.

    Merge strategy: each atomic applier is a pure function of the anchored
    baseline (it does not consume previous mutations). To compose, we call each
    applier independently on the baseline and merge the resulting CandidateEvidence
    fields: evolution_evidence from the last applier that changed it, holdout_evidence
    from the last applier that changed it, and authorization/candidate_isr from the
    first applier that sets them. This is correct because atomic mutations target
    DISTINCT evidence surfaces (one touches evolution, another holdout, another ISR).

    Reuses the existing atomic appliers registered by the R2.8.2/R2.8.5 harness;
    it introduces no new mutation semantics, only their composition.
    """

    def __init__(self, appliers: Mapping[str, MutationApp] | None = None):
        self._appliers = dict(appliers) if appliers else dict(_COMPOSER_REGISTRY)

    def get_applier(self, component_id: str) -> MutationApp:
        applier = self._appliers.get(component_id)
        if applier is None:
            raise UnknownMutationError(
                f"No atomic applier registered for component_id={component_id!r}"
            )
        return applier

    def compose(
        self,
        spec: ComposedMutationSpec,
        baseline: Baseline,
        seed: int,
    ) -> CandidateEvidence:
        """Compose the spec's components into one CandidateEvidence.

        The returned evidence is structurally indistinguishable from an atomic
        mutation's evidence -- the gate cannot tell it is a composition.
        """
        if not spec.component_ids:
            applier = self.get_applier("LEGIT_REPAIR_NO_TEST_EDIT")
            ev = applier(baseline.protected, baseline.baseline_run)
            return ev

        # Start from the first component's evidence as the base.
        first_id = spec.component_ids[0]
        first_applier = self.get_applier(first_id)
        ev = first_applier(baseline.protected, baseline.baseline_run)

        # Merge subsequent components.
        for comp_id in spec.component_ids[1:]:
            applier = self.get_applier(comp_id)
            component_ev = applier(baseline.protected, baseline.baseline_run)

            # Merge strategy: at the test level (positional), not tuple level.
            # Each mutation preserves test order in the baseline; we detect
            # per-position deltas (content_hash / test_id / outcome / removal)
            # from baseline and apply them to the running composed evidence.
            baseline_ev = _visible_baseline_evidence()
            baseline_hol = _holdout_run()

            ev = replace(ev, evolution_evidence=_merge_test_tuples(
                ev.evolution_evidence, component_ev.evolution_evidence, baseline_ev))
            ev = replace(ev, holdout_evidence=_merge_test_tuples(
                ev.holdout_evidence, component_ev.holdout_evidence, baseline_hol))

            if component_ev.causal_delta_accepted:
                ev = replace(ev, causal_delta_accepted=True)

            if component_ev.authorization is not None and ev.authorization is None:
                ev = replace(ev, authorization=component_ev.authorization)

            if component_ev.candidate_isr is not None and ev.candidate_isr is None:
                ev = replace(ev, candidate_isr=component_ev.candidate_isr)

        # Compute holdout_intact: compare merged holdout to anchored identities.
        holdout_intact = self._compute_holdout_intact(
            baseline.protected, ev.holdout_evidence
        )
        ev = replace(ev, holdout_intact=holdout_intact)

        return ev

    @staticmethod
    def _compute_holdout_intact(
        protected: ProtectedTestSet,
        holdout_evidence: tuple[TestExecution, ...],
    ) -> bool:
        """Mirror of AdversarialGateDecider._holdout_intact for evidence marking."""
        hid = {t.test_id: t for t in protected.identities if t.is_hidden()}
        seen = {e.test_id: e for e in holdout_evidence}
        for tid, ident in hid.items():
            ev = seen.get(tid)
            if (ev is None or ev.content_hash != ident.content_hash
                    or ev.outcome != TestOutcome.PASSED):
                return False
        if any(tid not in hid for tid in seen):
            return False
        return True


# -- R2.8.12 detection/metrics dataclasses ---------------------------------------

@dataclass(frozen=True)
class ComposedDetectionMetrics:
    """Defense-in-depth measurement for one composed attack."""
    __test__ = False

    composition_id: str
    component_ids: tuple[str, ...]
    expected_verdict: str
    actual_verdict: str
    expected_catching_layers: frozenset[str]
    actual_catching_layers: frozenset[str]
    cancelled_layers: frozenset[str]
    defense_depth: int
    detected: bool
    detector_cancellation: bool
    false_positive: bool
    false_negative: bool
    holdout_intact: bool
    expected_holdout_intact: bool
    evidence_hash: str
    evidence_intact: bool = True


@dataclass(frozen=True)
class ComposedMeasurementSummary:
    """Aggregate certification view for composed adversarial tests."""
    __test__ = False

    total_compositions: int
    adversarial_count: int
    control_count: int
    detection_rate: float
    false_negative_rate: float
    false_positive_rate: float
    detector_cancellation_count: int
    mean_defense_depth: float
    holdout_integrity: bool
    deterministic_replay: bool
    evidence_integrity: bool


# -- R2.8.12 measurement extensions on MeasurementLayer --------------------------

def _measure_composed(
    self,
    spec: ComposedMutationSpec,
    baseline: Baseline,
    seed: int,
) -> ComposedDetectionMetrics:
    """Measure one composed attack through the gate.

    The gate receives evidence only (never the spec's expected values).
    """
    composer = MutationComposer()
    evidence = composer.compose(spec, baseline, seed)
    decision = self._decider.decide(
        self._surface, self._baseline_run, evidence
    )

    # Determinism: re-compose + re-decide; must be identical.
    evidence_r = composer.compose(spec, baseline, seed)
    decision_r = self._decider.decide(
        self._surface, self._baseline_run, evidence_r
    )
    replayed = (
        evidence.content_hash() == evidence_r.content_hash()
        and decision_r.feasible == decision.feasible
        and decision_r.catching_layers == decision.catching_layers
    )

    actual_layers = frozenset(decision.catching_layers)
    expected_layers = spec.expected_catching_layers
    cancelled = expected_layers - actual_layers

    actual_verdict = decision.verdict.value
    expected_verdict = spec.expected_verdict.value

    is_adversarial = spec.expected_verdict is Verdict.REJECT
    verdict_correct = decision.verdict is spec.expected_verdict

    # R2.8.9: verify ledger chain + environment binding.
    evidence_intact = (
        self._ledger.verify_event_chain()
        and self._ledger.verify_environment_binding()
    )
    if not evidence_intact:
        decision = replace(
            decision, feasible=False,
            catching_layers=tuple(decision.catching_layers) + ("evidence",),
            evidence_intact=False,
        )
        actual_verdict = "infeasible"
        verdict_correct = False

    return ComposedDetectionMetrics(
        composition_id=spec.composition_id,
        component_ids=spec.component_ids,
        expected_verdict=expected_verdict,
        actual_verdict=actual_verdict,
        expected_catching_layers=expected_layers,
        actual_catching_layers=actual_layers,
        cancelled_layers=cancelled,
        defense_depth=len(actual_layers),
        detected=is_adversarial and verdict_correct,
        detector_cancellation=is_adversarial and verdict_correct and len(cancelled) > 0,
        false_positive=(not is_adversarial) and not verdict_correct,
        false_negative=is_adversarial and not verdict_correct,
         holdout_intact=evidence.holdout_intact,
         expected_holdout_intact=spec.expected_holdout_intact,
         evidence_hash=evidence.content_hash(),
         evidence_intact=evidence_intact,
    )


def _measure_composed_corpus(
    self,
    baseline: Baseline,
    seed: int = 11,
) -> tuple[tuple[ComposedDetectionMetrics, ...], ComposedMeasurementSummary]:
    """Measure the entire composed mutation matrix."""
    rows = tuple(
        self.measure_composed(spec, baseline, seed)
        for spec in COMPOSED_MUTATION_MATRIX
    )
    adversarial = tuple(r for r in rows if r.expected_verdict == Verdict.REJECT.value)
    controls = tuple(r for r in rows if r.expected_verdict == Verdict.ACCEPT.value)

    detected = sum(1 for r in adversarial if r.detected)
    false_neg = sum(1 for r in adversarial if r.false_negative)
    false_pos = sum(1 for r in controls if r.false_positive)
    na = len(adversarial) or 1
    nc = len(controls) or 1

    # Deterministic replay: re-run all compositions with same seed.
    deterministic = True
    composer = MutationComposer()
    for spec in COMPOSED_MUTATION_MATRIX:
        ev1 = composer.compose(spec, baseline, seed)
        ev2 = composer.compose(spec, baseline, seed)
        if ev1.content_hash() != ev2.content_hash():
            deterministic = False
            break

    return rows, ComposedMeasurementSummary(
        total_compositions=len(rows),
        adversarial_count=len(adversarial),
        control_count=len(controls),
        detection_rate=detected / na,
        false_negative_rate=false_neg / na,
        false_positive_rate=false_pos / nc,
        detector_cancellation_count=sum(1 for r in rows if r.detector_cancellation),
        mean_defense_depth=(
            sum(r.defense_depth for r in adversarial) / na if adversarial else 0.0
        ),
        holdout_integrity=all(r.holdout_intact == r.expected_holdout_intact for r in rows),
        deterministic_replay=deterministic,
        evidence_integrity=all(r.evidence_intact for r in rows),
    )


def build_adversarial_harness() -> tuple[
    "ProtectedTestSet", Baseline, "TestRunResult", dict[str, MutationApp],
    AdversarialGateDecider, MeasurementLayer,
]:
    """Build the full adversarial-composition harness.

    Returns (protected, baseline, baseline_run, appliers, decider, measurement).
    """
    authority = EvaluationAuthority()
    ledger = EvolutionLedger()
    boundary = EvaluationBoundary(
        authority=authority, ledger=ledger, evolution_id="r2.8.2",
    )
    surface = canonical_fsm_surface(authority, boundary)
    baseline_run = canonical_baseline_visible_run()
    baseline = Baseline(protected=surface, baseline_run=baseline_run)
    decider = AdversarialGateDecider(boundary, parent_isr=_canonical_arch_isr())
    measurement = MeasurementLayer(decider, ledger, surface, baseline_run)

    appliers: dict[str, MutationApp] = {}
    for spec in MUTATION_MATRIX:
        appliers[spec.mutation_id] = spec.apply

    return surface, baseline, baseline_run, appliers, decider, measurement


# =====================================================================
# R2.8.3 -- Measurement / epistemic layer
# =====================================================================
# A *read-only* layer over the R2.8.2 decision path. It never modifies the
# boundary, never feeds the mutation label back into the decision (the decider
# is invoked with evidence only), and produces tamper-evident records anchored
# to the EvolutionEvent chain. Its job: "how reliably does the boundary hold?"
#
# Invariants (100% or defect, never normalized rates):
#   * holdout integrity      -- hidden evaluation never tampered
#   * deterministic replay   -- same seed + mutation => identical verdict

#: Precedence in which catching layers are reported as "primary" (first hit).
_LAYER_PRECEDENCE = ("visibility", "content", "identity", "holdout", "regression", "attestation")


@dataclass(frozen=True)
class DetectionMetrics:
    """Per-mutation measurement record (one row of the certification ledger)."""

    __test__ = False

    corpus_version: str
    matrix_hash: str
    mutation_id: str
    attack_surface: str
    is_control: bool
    expected_verdict: str
    actual_verdict: str
    expected_catching_layers: tuple[str, ...]
    actual_catching_layers: tuple[str, ...]
    primary_catching_layer: str
    attribution: str            # correct_layer_catch | redundant_catch | missed | control_accepted | control_rejected
    detected: bool
    false_positive: bool
    false_negative: bool
    holdout_intact: bool
    expected_holdout_intact: bool
    replayed_identically: bool
    candidate_hash: str
    evidence_hash: str
    event_hash: str
    evidence_intact: bool = True  # R2.8.9: ledger chain + binding verification
    candidate_isr_hash: str = ""   # R2.8.11: ISR hash of the candidate
    candidate_isr_parent_hash: str = ""  # R2.8.11: parent ISR hash (for gen binding)
    authorization: Authorization | None = None  # R2.8.11: exposed for runner binding
    detail: str = ""


@dataclass(frozen=True)
class MeasurementSummary:
    """Aggregate certification view (R2.8.14 consumes this shape).

    False-positive rate is reported WITH n (the control set size); on a small
    corpus it is an incidence count, not a precise probability.
    """

    __test__ = False

    corpus_version: str
    matrix_hash: str
    total: int
    adversarial_total: int
    control_total: int
    detected: int
    false_negatives: int
    false_positives: int
    detection_rate: float
    false_negative_rate: float
    false_positive_rate: float
    false_positive_n: int
    mutation_score: float          # correct classification over the WHOLE corpus
    holdout_integrity: bool        # invariant
    deterministic_replay: bool     # invariant
    evidence_integrity: bool       # R2.8.9: ledger chain + binding integrity invariant
    layer_attribution: dict[str, int]
    per_layer_detection: dict[str, int]
    primary_layer_distribution: dict[str, int]


def _attribute(spec: MutationSpec, decision: "Decision", catching: tuple[str, ...]) -> str:
    expected_primary = spec.expected_catching_layers[0] if spec.expected_catching_layers else ""
    primary = catching[0] if catching else ""
    if spec.is_control:
        return "control_accepted" if decision.feasible else "control_rejected"
    if decision.feasible:
        return "missed"                      # adversarial accepted -> false negative
    if primary == expected_primary:
        return "correct_layer_catch"
    return "redundant_catch"                 # caught, but by a different primary layer


class MeasurementLayer:
    """R2.8.3: observe the decider's verdicts and anchor the records.

    The decider is called with **evidence only** (never the spec's expected
    values), preserving the information asymmetry: the measurement layer is
    privileged (it knows ground truth); the gate is not.
    """

    __test__ = False

    def __init__(self, decider: AdversarialGateDecider, ledger: EvolutionLedger,
                 surface: ProtectedTestSet, baseline_run: TestRunResult,
                 corpus_version: str = "r2.8.2-corpus-v1"):
        self._decider = decider
        self._ledger = ledger
        self._surface = surface
        self._baseline_run = baseline_run
        self.corpus_version = corpus_version
        self.matrix_hash = canonical_hash(
            tuple((s.mutation_id, s.attack_surface.value, s.expected_feasibility,
                   s.expected_catching_layers, s.expected_drift_class, s.is_control)
                  for s in MUTATION_MATRIX)
        )
        # R2.8.11: spec lookup by mutation_id for the multi-generation runner.
        self._spec_index: dict[str, MutationSpec] = {
            s.mutation_id: s for s in MUTATION_MATRIX
        }
        # Anchor the corpus itself (matrix_hash + protected-core hash) so the
        # certification is tamper-evident and corpus-bound.
        self._corpus_event_hash = self._anchor_corpus()

    def _anchor_corpus(self) -> str:
        """Append the corpus anchor event.

        Uses the same environment_hash as the boundary's ANCHOR event
        (self._surface.environment_fingerprint) so verify_environment_binding
        passes across all events in the ledger.
        """
        from tiannara.application.evolution.ledger import EvolutionEvent
        event = EvolutionEvent(
            event_id="",
            evolution_id="r2.8.2",
            sequence=0,
            event_type=EventType.MEASUREMENT,
            subject_id="",
            payload={
                "kind": "corpus_anchor",
                "corpus_version": self.corpus_version,
                "matrix_hash": self.matrix_hash,
                "anchor_surface_hash": self._surface.content_hash,
            },
            environment_hash=self._surface.environment_fingerprint,
        )
        return self._ledger.append_event(event, evolution_id="r2.8.2")

    @property
    def _environment_hash(self) -> str:
        """Environment binding hash for measurement events.

        Uses the same environment_fingerprint as the boundary's ANCHOR event
        so that verify_environment_binding passes across all events in the ledger.
        """
        return self._surface.environment_fingerprint

    def measure(self, spec: MutationSpec) -> DetectionMetrics:
        """Run a single mutation through the decider and record the verdict.

        The decider is invoked with **evidence only** -- ``spec`` (which carries
        the expected verdict/layer) is never passed to it, enforcing the
        information asymmetry: ground-truth expectations live solely in the
        measurement layer.
        """
        evidence = spec.apply(self._surface, self._baseline_run)
        # Decision is spec-agnostic:
        decision = self._decider.decide(self._surface, self._baseline_run, evidence)

        # Determinism: re-apply and re-decide; must be byte-identical.
        evidence_r = spec.apply(self._surface, self._baseline_run)
        decision_r = self._decider.decide(self._surface, self._baseline_run, evidence_r)
        replayed = (
            evidence.content_hash() == evidence_r.content_hash()
            and decision_r.feasible == decision.feasible
            and decision_r.catching_layers == decision.catching_layers
        )

        actual_layers = decision.catching_layers
        attribution = _attribute(spec, decision, actual_layers)
        actual_verdict = "feasible" if decision.feasible else "infeasible"

        metrics = DetectionMetrics(
            corpus_version=self.corpus_version,
            matrix_hash=self.matrix_hash,
            mutation_id=spec.mutation_id,
            attack_surface=spec.attack_surface.value,
            is_control=spec.is_control,
            expected_verdict=spec.expected_feasibility,
            actual_verdict=actual_verdict,
            expected_catching_layers=spec.expected_catching_layers,
            actual_catching_layers=actual_layers,
            primary_catching_layer=actual_layers[0] if actual_layers else "",
            attribution=attribution,
            detected=(not spec.is_control and not decision.feasible),
            false_positive=(spec.is_control and not decision.feasible),
            false_negative=(not spec.is_control and decision.feasible),
             holdout_intact=decision.holdout_intact,
             expected_holdout_intact=spec.expected_holdout_intact,
             replayed_identically=replayed,
            candidate_hash=evidence.content_hash(),
            evidence_hash=evidence.content_hash(),
            event_hash="",
            candidate_isr_hash=evidence.candidate_isr.content_hash if evidence.candidate_isr else "",
            candidate_isr_parent_hash=evidence.authorization.parent_isr_hash if evidence.authorization else "",
            authorization=evidence.authorization,
            detail=decision.detail,
        )
        # R2.8.9: bind evidence to the measurement environment.
        environment_hash = self._environment_hash

        # Anchor the per-mutation record (tamper-evident, chain-linked).
        from tiannara.application.evolution.ledger import EvolutionEvent
        event = EvolutionEvent(
            event_id="",
            evolution_id="r2.8.2",
            sequence=0,
            event_type=EventType.MEASUREMENT,
            subject_id=spec.mutation_id,
            payload={
                "kind": "measurement",
                "corpus_version": self.corpus_version,
                "matrix_hash": self.matrix_hash,
                "mutation_id": spec.mutation_id,
                "expected_verdict": spec.expected_feasibility,
                "actual_verdict": actual_verdict,
                "primary_catching_layer": metrics.primary_catching_layer,
                "attribution": attribution,
                "candidate_hash": metrics.candidate_hash,
                "holdout_intact": decision.holdout_intact,
            },
            candidate_hash=evidence.content_hash(),
            isr_hash=evidence.candidate_isr.content_hash if evidence.candidate_isr else "",
            environment_hash=environment_hash,
        )
        event_hash = self._ledger.append_event(event, evolution_id="r2.8.2")

        # R2.8.9: verify evidence integrity — ledger chain + environment binding.
        evidence_intact = (
            self._ledger.verify_event_chain()
            and self._ledger.verify_environment_binding()
        )
        if not evidence_intact:
            decision = replace(
                decision,
                feasible=False,
                catching_layers=decision.catching_layers + ("evidence",),
                evidence_intact=False,
            )
            # When evidence is compromised, the candidate is rejected.
            # false_negative = (adversarial AND should-have-been-detected AND was-accepted)
            # With evidence_intact=False, decision.feasible is False, so:
            #   false_negative = (not spec.is_control and decision.feasible)
            #                  = (not spec.is_control and False) = False
            # This is correct: the evidence layer IS catching it.
            metrics = replace(
                metrics,
                actual_verdict="infeasible",
                detected=True,
                false_negative=False,
                false_positive=False,
                evidence_intact=False,
            )
        return replace(metrics, event_hash=event_hash, evidence_intact=evidence_intact)

    def measure_by_id(self, mutation_id: str) -> DetectionMetrics:
        """R2.8.11: look up a mutation by ID and measure it.

        Convenience for the multi-generation runner, which references candidates
        by mutation_id rather than by direct spec.
        """
        spec = self._spec_index[mutation_id]
        return self.measure(spec)

    def summarize(self, metrics: tuple[DetectionMetrics, ...]) -> MeasurementSummary:
        adversarial = [m for m in metrics if not m.is_control]
        controls = [m for m in metrics if m.is_control]
        detected = sum(1 for m in adversarial if m.detected)
        fn = sum(1 for m in adversarial if m.false_negative)
        fp = sum(1 for m in controls if m.false_positive)
        na = len(adversarial) or 1
        nc = len(controls)
        n_total = len(metrics) or 1
        attribution_counts: dict[str, int] = {}
        for m in metrics:
            attribution_counts[m.attribution] = attribution_counts.get(m.attribution, 0) + 1
        per_layer: dict[str, int] = {}
        primary_dist: dict[str, int] = {}
        for m in metrics:
            for layer in m.actual_catching_layers:
                per_layer[layer] = per_layer.get(layer, 0) + 1
            primary_dist[m.primary_catching_layer] = primary_dist.get(m.primary_catching_layer, 0) + 1
        return MeasurementSummary(
            corpus_version=self.corpus_version,
            matrix_hash=self.matrix_hash,
            total=len(metrics),
            adversarial_total=len(adversarial),
            control_total=nc,
            detected=detected,
            false_negatives=fn,
            false_positives=fp,
            detection_rate=detected / na,
            false_negative_rate=fn / na,
            false_positive_rate=(fp / nc) if nc else 0.0,
            false_positive_n=nc,
            mutation_score=(detected + sum(1 for m in controls if not m.false_positive)) / n_total,
            holdout_integrity=all(
                m.holdout_intact == m.expected_holdout_intact for m in metrics
            ),
            deterministic_replay=all(m.replayed_identically for m in metrics),
            evidence_integrity=all(m.evidence_intact for m in metrics),
            layer_attribution=attribution_counts,
            per_layer_detection=per_layer,
             primary_layer_distribution=primary_dist,
        )


# Attach measurement methods to MeasurementLayer (after class definition)
MeasurementLayer.measure_composed = _measure_composed
MeasurementLayer.measure_composed_corpus = _measure_composed_corpus


# Backward-compatible alias: R2.8.11 tests import COMPOSED_MATRIX
COMPOSED_MATRIX = COMPOSED_MUTATION_MATRIX
