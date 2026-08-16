"""R2.9.6 -- Multiple simultaneous and interacting defects.

Proves the four R2.9.6 refinements against the R2.9.2-R2.9.5 machinery,
without new architectural authority:

1. Joint evaluation is unconditional: every candidate is re-evaluated against
   EVERY defect observation through the R2.8 boundary. Interaction detection
   is emergent from execution -- there is no special-case interaction rule.
2. Partial repair is a legitimate step forward, compared by strict-superset
   subset dominance (never a scalar "defects fixed" score).
3. The cumulative resolution tracker grows monotonically (anti-oscillation);
   a candidate that un-resolves a previously resolved defect is hard-rejected.
4. Repair stability is recorded per-defect in the ledger (cumulative
   ``resolved_defects`` evidence) and surfaced on the run result.

The canonical resolution signal is the boundary's own target_failure verdict
(``_resolves_observation``); the deceptive candidate (awaiting-surface strip)
is rejected at the identity layer (``AwaitingSurfaceIntactInvariant``) and
the rewire candidate (fixes B by dropping A's fix) is rejected by the
tracker as a regression -- discovered by execution, not by rule.

Determinism note (Phase-28 provenance debt, tracked for R2.9.7): the base ISR
carries a FIXED ``created_at`` so generation-0 candidates are reproducible;
generation >= 1 parents are created at run time via ``with_system``, so
cross-run determinism is asserted at the trajectory/profile level (never on
gen >= 1 hashes).
"""
from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from constitutional_architecture.isr.model import (
    ISR,
    ISRProvenance,
    Module,
    StateType,
    System,
    Workflow,
    WorkflowState,
    WorkflowTransition,
)

from tiannara.application.evolution import (
    AwaitingSurfaceIntactInvariant,
    CandidateGate,
    DeterministicComplexityPreference,
    EvolutionLedger,
    MultiGenerationEvolutionCoordinator,
    TransitionRestoration,
    apply_restoration,
    stable_isr_hash,
)
from tiannara.application.evolution.candidate_gate import (
    CandidateVerdict,
    GateResult,
)
from tiannara.application.evolution.candidate_sandbox import CompiledCandidate
from tiannara.application.evolution.competitive_evolution import ScoredCandidate
from tiannara.application.evolution.compiler_sandbox import hash_artifact
from tiannara.application.evolution.evolution_state import TerminationReason
from tiannara.application.evolution.fitness import FitnessVector
from tiannara.application.evolution.multi_defect import (
    CumulativeResolutionTracker,
    DefectResolutionProfile,
    DefectSet,
    MultiDefectEvaluator,
    MultiDefectGeneration,
    MultiDefectRunResult,
    MultiDefectScore,
    MultiDefectSelector,
)
from tiannara.application.evolution.mutation_operators import (
    ISRDelta,
    MutationCandidate,
)
from tiannara.domain.models.evidence import TestRunResult
from tiannara.domain.models.observation import (
    FailureCategory,
    FailureObservation,
    FailurePhase,
)

COROUTINE_A = "process_payment"
COROUTINE_B = "send_invoice"
OBS_A = "obs-a"
OBS_B = "obs-b"

_FIXED_PROVENANCE = ISRProvenance(created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))


# -- observation model ---------------------------------------------------------

def _obs(coroutine: str, evidence_hash: str) -> FailureObservation:
    diagnostic = f"coroutine '{coroutine}' was never awaited"
    return FailureObservation(
        execution_id=f"exec-{evidence_hash}", backend_id="stub",
        phase=FailurePhase.TEST, category=FailureCategory.TEST_FAILURE,
        exit_code=1, command=["pytest", "-W", "error::RuntimeWarning", "-q"],
        diagnostics=(diagnostic,),
        evidence_hash=evidence_hash,
        stderr_excerpt=f"RuntimeWarning: {diagnostic}",
    )


def _defect_set() -> DefectSet:
    return DefectSet((_obs(COROUTINE_A, OBS_A), _obs(COROUTINE_B, OBS_B)))


# -- ISR fixtures ---------------------------------------------------------------

def _awaiting_state(state_id: str, coroutine: str) -> WorkflowState:
    return WorkflowState(
        id=state_id, name="awaiting", state_type=StateType.INTERMEDIATE,
        metadata={"awaits": coroutine},
    )


def _edge(state: WorkflowState, final: WorkflowState, coroutine: str) -> WorkflowTransition:
    return WorkflowTransition(
        id=f"resolve-{coroutine}", name=f"resolve {coroutine}",
        from_state_id=state.id, to_state_id=final.id, trigger=coroutine,
    )


def _interacting_workflow(resolving: bool) -> Workflow:
    """ONE workflow with TWO awaiting states: the interacting substrate. Both
    defects share a workflow, so repairing one is co-located with the other."""
    await_a = _awaiting_state(f"order-await-{COROUTINE_A}", COROUTINE_A)
    await_b = _awaiting_state(f"order-await-{COROUTINE_B}", COROUTINE_B)
    final = WorkflowState(id="order-final", name="final", state_type=StateType.FINAL)
    transitions = ()
    if resolving:
        transitions = (
            _edge(await_a, final, COROUTINE_A),
            _edge(await_b, final, COROUTINE_B),
        )
    return Workflow(
        id="order", name="order", states=(await_a, await_b, final),
        transitions=transitions,
    )


def _independent_workflow(wf_id: str, coroutine: str, resolving: bool) -> Workflow:
    """One workflow per coroutine: the non-interacting substrate."""
    awaited = _awaiting_state(f"{wf_id}-await-{coroutine}", coroutine)
    final = WorkflowState(id=f"{wf_id}-final", name="final", state_type=StateType.FINAL)
    transitions = ()
    if resolving:
        transitions = (_edge(awaited, final, coroutine),)
    return Workflow(
        id=wf_id, name=wf_id, states=(awaited, final), transitions=transitions,
    )


def _isr(interacting: bool, resolving: bool) -> ISR:
    if interacting:
        workflows = (_interacting_workflow(resolving),)
    else:
        workflows = (
            _independent_workflow("order", COROUTINE_A, resolving),
            _independent_workflow("invoicing", COROUTINE_B, resolving),
        )
    return ISR(system=System(
        id="sys", name="OrderSystem",
        modules=(Module(id="m", name="M", workflows=workflows),),
    ), provenance=_FIXED_PROVENANCE)


def _known_good(interacting: bool) -> ISR:
    return _isr(interacting, resolving=True)


def _defective(interacting: bool) -> ISR:
    return _isr(interacting, resolving=False)


def _has_resolution(isr: ISR, coroutine: str | None = None) -> bool:
    """Faithful substrate predicate: a state awaiting ``coroutine`` is resolved
    iff a transition with that trigger exists in the same workflow. With no
    coroutine, every awaiting state must be resolved (the full-suite run)."""
    for module in isr.system.modules:
        for wf in module.workflows:
            awaiting = [
                s for s in wf.states
                if s.metadata.get("awaits")
                and (coroutine is None or s.metadata.get("awaits") == coroutine)
            ]
            for state in awaiting:
                if not any(
                    t.from_state_id == state.id
                    and t.trigger == state.metadata.get("awaits")
                    for t in wf.transitions
                ):
                    return False
    return True


def _awaiting_target(isr: ISR, coroutine: str):
    """(workflow_id, state_id, final_id) for the unique awaiting state."""
    targets = []
    for module in isr.system.modules:
        for wf in module.workflows:
            awaiting = [s for s in wf.states if s.metadata.get("awaits") == coroutine]
            finals = [s for s in wf.states if s.state_type is StateType.FINAL]
            if len(awaiting) == 1 and len(finals) == 1:
                targets.append((wf.id, awaiting[0].id, finals[0].id))
    if len(targets) == 1:
        return targets[0]
    return None


# -- sandbox (observation-aware execution oracle) -------------------------------

class FsmStubSandbox:
    """Hermetic FSM substrate. ``run_tests(artifact, observation=None)`` is
    the per-observation execution oracle: with an observation it re-runs the
    surface for that defect only; without one it runs the full surface."""

    def __init__(self):
        self._artifact_isr: dict[str, ISR] = {}

    def build(self, isr: ISR, workspace: str | None = None) -> CompiledCandidate:
        root = Path(workspace) if workspace else Path(tempfile.mkdtemp(prefix="r296-"))
        lines = []
        for module in isr.system.modules:
            for wf in module.workflows:
                for state in wf.states:
                    coroutine = state.metadata.get("awaits")
                    if not coroutine:
                        continue
                    if any(t.trigger == coroutine for t in wf.transitions):
                        lines.append(f"    await {coroutine}()")
                    else:
                        lines.append(f"    {coroutine}()  # fire-and-forget")
        (root / "generated.py").write_text(
            "\n".join(lines) + "\n" if lines else "", encoding="utf-8",
        )
        artifact = CompiledCandidate(
            source_root=str(root), compile_ok=True,
            artifact_hash=hash_artifact(root),
        )
        self._artifact_isr[artifact.artifact_hash] = isr
        return artifact

    def run_tests(
        self, artifact: CompiledCandidate, observation: FailureObservation | None = None,
    ) -> TestRunResult:
        isr = self._artifact_isr.get(artifact.artifact_hash)
        if observation is not None:
            coroutine = TransitionRestoration.extract_coroutine_name(observation)
        else:
            coroutine = None
        repaired = isr is not None and _has_resolution(isr, coroutine)
        return TestRunResult(
            passed=repaired, exit_code=0 if repaired else 1,
            total_tests=1, failed_tests=0 if repaired else 1,
            pass_count=1 if repaired else 0, duration_seconds=1.0,
        )


# -- R2.9.6 variation: staged repair + attack vectors -----------------------------

def _apply_op_candidate(
    operator_id: str, parent_isr: ISR, desc: dict, hypothesis: str,
) -> MutationCandidate:
    import json as _json
    entry = _json.dumps(desc, sort_keys=True)
    candidate_isr = apply_restoration(parent_isr, (entry,))
    return MutationCandidate(
        candidate_id=f"{operator_id}:{stable_isr_hash(candidate_isr)[:12]}",
        operator_id=operator_id,
        candidate_isr=candidate_isr,
        parent_isr=parent_isr,
        mutation_delta=ISRDelta((entry,)),
        hypothesis=hypothesis,
    )


def _restore_candidate(current_isr: ISR, obs: FailureObservation):
    """Honest repair: restore the resolution edge for the observation's
    coroutine, built through ``apply_restoration`` (closure-valid). Unlike
    ``TransitionRestorationOperator`` this also fires when the coroutine is
    already resolved (an idempotent re-assertion), which the StuckVariation
    partial-repair path relies on."""
    coroutine = TransitionRestoration.extract_coroutine_name(obs)
    located = _awaiting_target(current_isr, coroutine)
    if located is None:
        return None
    workflow_id, state_id, final_id = located
    return _apply_op_candidate(
        "transition_restoration", current_isr, {
            "workflow_id": workflow_id,
            "from_state_id": state_id,
            "to_state_id": final_id,
            "trigger": coroutine,
        },
        hypothesis=f"restore required async resolution of '{coroutine}'",
    )


def _rewire_candidate(current_isr: ISR, target_obs: FailureObservation, sacrificed_obs: FailureObservation):
    """Interaction attack vector: fix the target coroutine's defect by
    re-pointing the whole workflow at it, silently dropping the other
    defect's resolution. Boundary-valid (surfaces intact); must be caught as
    a regression by execution + tracker."""
    target = TransitionRestoration.extract_coroutine_name(target_obs)
    sacrificed = TransitionRestoration.extract_coroutine_name(sacrificed_obs)
    located = _awaiting_target(current_isr, target)
    if located is None:
        return None
    workflow_id, state_id, final_id = located
    return _apply_op_candidate(
        "rewire_vector", current_isr, {
            "workflow_id": workflow_id,
            "from_state_id": state_id,
            "to_state_id": final_id,
            "trigger": target,
            "op": "rewire",
            "sacrifices": sacrificed,
        },
        hypothesis=f"rewire '{target}' at the expense of '{sacrificed}'",
    )


def _strip_candidate(current_isr: ISR, target_obs: FailureObservation):
    """Deceptive control: strip the awaiting surface the failing test checks.
    Must be rejected at the identity layer (``AwaitingSurfaceIntactInvariant``)."""
    coroutine = TransitionRestoration.extract_coroutine_name(target_obs)
    located = _awaiting_target(current_isr, coroutine)
    if located is None:
        return None
    workflow_id, state_id, _ = located
    return _apply_op_candidate(
        "test_deletion", current_isr, {
            "workflow_id": workflow_id,
            "from_state_id": state_id,
            "to_state_id": state_id,
            "trigger": coroutine,
            "op": "strip_awaits",
            "state_id": state_id,
        },
        hypothesis=f"strip awaiting surface of '{coroutine}' (deceptive)",
    )


class StagedRepairVariation:
    """R2.9.6 harness variation: repairs the FIRST defect's coroutine before
    ``seed >= gate``, then proposes the SECOND defect's repair, optionally
    alongside the interaction attack vector (rewire) and the deceptive
    control (strip).

    Honest repairs reuse ``TransitionRestorationOperator`` (closure-valid ISR
    deltas, deterministic); the attack vectors are built through
    ``apply_restoration`` so the CausalGate's closure check holds for them
    too -- they must be rejected on their merits, never on construction."""

    def __init__(
        self,
        gate: int = 1,
        include_rewire: bool = False,
        include_deceptive: bool = False,
    ):
        self._gate = gate
        self._include_rewire = include_rewire
        self._include_deceptive = include_deceptive

    @property
    def operator_ids(self):
        return ("transition_restoration", "rewire_vector", "test_deletion")

    def generate(self, current_isr, defect_set, population_size, seed):
        order = list(defect_set.observations)
        if seed < self._gate:
            targets = (order[0],)
        else:
            targets = (order[1],)
        candidates = []
        for obs in targets:
            proposed = _restore_candidate(current_isr, obs)
            if proposed is not None:
                candidates.append(proposed)
        if seed >= self._gate and self._include_rewire:
            rewire = _rewire_candidate(current_isr, order[1], order[0])
            if rewire is not None:
                candidates.append(rewire)
        if seed >= self._gate and self._include_deceptive:
            deceptive = _strip_candidate(current_isr, order[1])
            if deceptive is not None:
                candidates.append(deceptive)
        return tuple(sorted(candidates, key=lambda c: c.candidate_id))


class DeceptiveOnlyVariation:
    """Negative control: only the deceptive strip candidate is ever proposed.
    The boundary must reject it at the identity layer, leaving the run with no
    feasible candidate."""

    def generate(self, current_isr, defect_set, population_size, seed):
        strip = _strip_candidate(current_isr, defect_set.observations[1])
        return (strip,) if strip is not None else ()


# -- coordinator wiring ----------------------------------------------------------

def _make(variation, ledger: EvolutionLedger | None = None, interacting: bool = False):
    sandbox = FsmStubSandbox()
    known_good = _known_good(interacting)
    defective = _defective(interacting)
    defect_set = _defect_set()
    baseline_artifact = sandbox.build(known_good)
    baseline_run = sandbox.run_tests(baseline_artifact)
    broken_artifact = sandbox.build(defective)
    broken_run = sandbox.run_tests(broken_artifact)
    assert not broken_run.passed
    coordinator = MultiGenerationEvolutionCoordinator(
        sandbox=sandbox,
        gate=CandidateGate.default(),
        variation=variation,
        selection=DeterministicComplexityPreference(),
        ledger=ledger,
    )
    return (
        coordinator, defective, defect_set,
        broken_artifact, broken_run, baseline_artifact, baseline_run,
    )


# -- 1. Defect isolation ----------------------------------------------------------

def test_defect_set_isolates_observations_by_evidence_hash():
    defect_set = _defect_set()
    assert defect_set.observation_ids == (OBS_A, OBS_B)
    assert len(defect_set) == 2
    assert defect_set.for_observation(OBS_A).evidence_hash == OBS_A
    assert defect_set.for_observation(OBS_B).evidence_hash == OBS_B
    with pytest.raises(KeyError):
        defect_set.for_observation("nope")


# -- 2. Subset dominance is strict-superset, never a scalar -----------------------

def test_profile_subset_dominance_is_strict_superset():
    partial = DefectResolutionProfile({OBS_A: True, OBS_B: False})
    full = DefectResolutionProfile({OBS_A: True, OBS_B: True})
    other = DefectResolutionProfile({OBS_A: False, OBS_B: True})
    assert full.dominates(partial)
    assert not partial.dominates(full)
    assert not partial.dominates(other)          # incomparable, not "worse"
    assert full.all_resolved and not partial.all_resolved
    assert partial.resolution_fraction == 0.5    # observable, never the objective
    assert partial.resolved_set() == frozenset({OBS_A})


def test_selector_uses_subset_dominance_not_scalar_score():
    partial = MultiDefectScore(
        None, DefectResolutionProfile({OBS_A: True, OBS_B: False}),
        {OBS_A: True, OBS_B: False}, None,
    )
    full = MultiDefectScore(
        None, DefectResolutionProfile({OBS_A: True, OBS_B: True}),
        {OBS_A: True, OBS_B: True}, None,
    )
    assert partial.eligible and full.eligible
    assert full.profile.dominates(partial.profile)
    assert not partial.profile.dominates(full.profile)


# -- 3. Cumulative tracker: monotonic growth, hard regression rejection -------------

def test_tracker_grows_monotonically_and_rejects_regressions():
    tracker = CumulativeResolutionTracker()
    tracker.accept(DefectResolutionProfile({OBS_A: True, OBS_B: False}))
    assert tracker.resolved == frozenset({OBS_A})
    assert tracker.regressed_by(
        DefectResolutionProfile({OBS_A: False, OBS_B: True})
    ) == frozenset({OBS_A})
    assert tracker.regressed_by(
        DefectResolutionProfile({OBS_A: True, OBS_B: True})
    ) == frozenset()
    tracker.accept(DefectResolutionProfile({OBS_A: True, OBS_B: True}))
    assert tracker.resolved == frozenset({OBS_A, OBS_B})
    # accepting a partial snapshot NEVER shrinks the set
    tracker.accept(DefectResolutionProfile({OBS_A: True, OBS_B: False}))
    assert tracker.resolved == frozenset({OBS_A, OBS_B})


def test_selector_hard_rejects_regressing_candidates():
    tracker = CumulativeResolutionTracker()
    tracker.accept(DefectResolutionProfile({OBS_A: True, OBS_B: False}))
    clean = MultiDefectScore(
        None, DefectResolutionProfile({OBS_A: True, OBS_B: True}),
        {OBS_A: True, OBS_B: True}, None,
    )
    rewire = MultiDefectScore(
        None, DefectResolutionProfile({OBS_A: False, OBS_B: True}),
        {OBS_B: True}, None,
    )
    selector = MultiDefectSelector()
    assert selector.select([clean, rewire], tracker) is clean
    # when ONLY the regressing candidate is viable -> nothing selectable
    assert selector.select([rewire], tracker) is None


def test_selector_excludes_boundary_ineligible_candidates():
    tracker = CumulativeResolutionTracker()
    ineligible = MultiDefectScore(
        None, DefectResolutionProfile({OBS_A: True}), {}, None,
    )
    clean = MultiDefectScore(
        None, DefectResolutionProfile({OBS_A: True, OBS_B: True}),
        {OBS_A: True, OBS_B: True}, None,
    )
    selector = MultiDefectSelector()
    assert selector.select([ineligible, clean], tracker) is clean
    assert selector.select([ineligible], tracker) is None


# -- 4. Joint evaluation is unconditional through the boundary ----------------------

def test_evaluator_runs_every_candidate_against_every_observation():
    calls: list[str] = []
    probe: dict[str, ScoredCandidate] = {}

    def score_one(candidate, observation):
        calls.append(observation.evidence_hash)
        scored = probe[observation.evidence_hash]
        # the resolution signal is the boundary's target_failure verdict,
        # exactly as ``_resolves_observation`` reads it
        return scored, scored.verdict.gate_results[0].passed

    for oid, accept in ((OBS_A, True), (OBS_B, False)):
        probe[oid] = ScoredCandidate(
            None,
            CandidateVerdict(
                accept, (GateResult("target_failure", accept, ""),),
                candidate_hash="c", parent_hash="p",
            ),
            FitnessVector({}), accept,
        )
    evaluator = MultiDefectEvaluator(score_one)
    score = evaluator.evaluate(object(), _defect_set())
    assert set(calls) == {OBS_A, OBS_B}
    assert score.profile.resolutions == {OBS_A: True, OBS_B: False}
    assert score.acceptances == {OBS_A: True, OBS_B: False}
    assert score.tiebreak is not None and score.tiebreak.verdict.accept


def test_joint_evaluations_counted_in_result():
    coordinator, defective, defect_set, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(
        StagedRepairVariation(),
    )
    state = coordinator.run_multi_defect(
        defective, defect_set, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=5, population_size=4, seed=0,
    )
    # gen 0: 1 candidate x 2 observations; gen 1: 1 x 2 -> 4 joint evaluations
    assert state.total_joint_evaluations == 4


# -- 5. Two independent defects: staged repair to full resolution -------------------

def test_two_independent_defects_repaired_in_stages():
    coordinator, defective, defect_set, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(
        StagedRepairVariation(),
    )
    state = coordinator.run_multi_defect(
        defective, defect_set, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=5, population_size=4, seed=0,
    )
    assert state.succeeded
    assert state.termination_reason is TerminationReason.SUCCESS
    assert len(state.generations) == 2
    gen0, gen1 = state.generations
    assert gen0.selected_operator_id == "transition_restoration"
    assert gen0.profile.resolutions == {OBS_A: True, OBS_B: False}
    assert gen0.resolved_defects == frozenset({OBS_A})
    assert gen1.profile.resolutions == {OBS_A: True, OBS_B: True}
    assert gen1.resolved_defects == frozenset({OBS_A, OBS_B})
    assert gen1.all_resolved


def test_partial_repair_is_a_legitimate_step_until_generation_limit():
    """Partial repair is a forward step (never a regression); when the search
    budget runs out before full resolution, the run reports GENERATION_LIMIT
    honestly -- it never pretends, oscillates, or re-litigates."""
    coordinator, defective, defect_set, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(
        StagedRepairVariation(),
    )
    state = coordinator.run_multi_defect(
        defective, defect_set, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=1, population_size=4, seed=0,
    )
    assert state.termination_reason is TerminationReason.GENERATION_LIMIT
    assert not state.succeeded
    (gen0,) = state.generations
    assert gen0.profile.resolutions == {OBS_A: True, OBS_B: False}
    assert gen0.resolved_defects == frozenset({OBS_A})
    assert gen0.all_resolved is False
    # the resolved defect is stably resolved for every generation it appears in
    assert state.repair_stability == 1.0


# -- 6. Interacting defects: interaction discovered by execution ----------------------

def test_interacting_defects_rewire_regression_rejected_by_execution():
    ledger = EvolutionLedger()
    coordinator, defective, defect_set, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(
        StagedRepairVariation(include_rewire=True),
        ledger=ledger,
        interacting=True,
    )
    state = coordinator.run_multi_defect(
        defective, defect_set, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=5, population_size=4, seed=0,
    )
    assert state.succeeded
    gen0, gen1 = state.generations
    # gen 0 fixes A first; gen 1 re-proposes the rewire attack
    assert gen0.selected_operator_id == "transition_restoration"
    assert gen0.profile.resolutions == {OBS_A: True, OBS_B: False}
    # the rewire candidate (fix B, drop A) is a regression, discovered by
    # re-running A against it -- the tracker hard-rejects it
    assert len(gen1.regression_rejections) == 1
    rewire_id, regressed = gen1.regression_rejections[0]
    assert "rewire_vector" in rewire_id
    assert regressed == frozenset({OBS_A})
    # the honest repair_B wins; A stays resolved
    assert gen1.selected_operator_id == "transition_restoration"
    assert gen1.profile.resolutions == {OBS_A: True, OBS_B: True}
    # ledger records the regression rejection
    rejected = [e for e in ledger.events()
                if e.event_type.name == "CANDIDATE_REJECTED"
                and e.payload.get("reason") == "regression"]
    assert len(rejected) == 1
    assert rejected[0].payload["regressed_defects"] == [OBS_A]


# -- 7. Deceptive candidate rejected at the identity layer ----------------------------

def test_deceptive_strip_rejected_by_invariant_and_run_continues():
    ledger = EvolutionLedger()
    coordinator, defective, defect_set, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(
        StagedRepairVariation(include_deceptive=True),
        ledger=ledger,
    )
    state = coordinator.run_multi_defect(
        defective, defect_set, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=5, population_size=4, seed=0,
        protected_invariants=(AwaitingSurfaceIntactInvariant(),),
        deceptive_operator_ids=("test_deletion",),
    )
    assert state.succeeded
    assert state.deceptive_rejected
    boundary = [e for e in ledger.events()
                if e.event_type.name == "CANDIDATE_REJECTED"
                and e.payload.get("reason") == "boundary"]
    assert any("test_deletion" in e.payload["candidate"] for e in boundary)
    # the honest repair still wins
    assert state.generations[-1].all_resolved


def test_deceptive_not_detected_when_absent():
    coordinator, defective, defect_set, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(
        StagedRepairVariation(),
    )
    state = coordinator.run_multi_defect(
        defective, defect_set, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=5, population_size=4, seed=0,
    )
    assert state.succeeded
    assert not state.deceptive_rejected


def test_deceptive_only_variation_terminates_no_feasible():
    coordinator, defective, defect_set, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(
        DeceptiveOnlyVariation(),
    )
    state = coordinator.run_multi_defect(
        defective, defect_set, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=3, population_size=4, seed=0,
        protected_invariants=(AwaitingSurfaceIntactInvariant(),),
        deceptive_operator_ids=("test_deletion",),
    )
    assert state.termination_reason is TerminationReason.NO_FEASIBLE_CANDIDATES
    assert not state.succeeded
    assert state.deceptive_rejected
    assert state.generations == ()


# -- 8. Repair stability: ledger evidence + formula ------------------------------------

def test_repair_stability_recorded_per_defect():
    ledger = EvolutionLedger()
    coordinator, defective, defect_set, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(
        StagedRepairVariation(),
        ledger=ledger,
    )
    state = coordinator.run_multi_defect(
        defective, defect_set, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=5, population_size=4, seed=0,
    )
    # clean monotonic run: 1.0 for both defects by construction
    assert state.repair_stability == 1.0
    completed = [e for e in ledger.events()
                 if e.event_type.name == "GENERATION_COMPLETED"]
    assert len(completed) == 2
    sets = [set(e.payload["resolved_defects"]) for e in completed]
    assert sets[0] == {OBS_A}
    assert sets[1] == {OBS_A, OBS_B}
    # per-defect ledger evidence: every generation records the per-defect map
    for event in completed:
        assert set(event.payload["per_defect"].keys()) == {OBS_A, OBS_B}
    assert ledger.verify_event_chain() is True


def test_repair_stability_formula_counts_gaps():
    def gen(i, resolved):
        return MultiDefectGeneration(
            generation_id=f"g{i}", generation_index=i, parent_generation_id="",
            parent_isr_hash="", selected_candidate_id="c", selected_operator_id="o",
            profile=DefectResolutionProfile(
                {oid: oid in resolved for oid in (OBS_A, OBS_B)}
            ),
            resolved_defects=frozenset(resolved),
            evaluated_count=1, eligible_count=1,
        )

    stable = MultiDefectRunResult(
        evolution_id="e", initial_isr_hash="h", defect_ids=(OBS_A, OBS_B),
        generations=(gen(0, {OBS_A}), gen(1, {OBS_A, OBS_B}),
                      gen(2, {OBS_A, OBS_B}), gen(3, {OBS_A, OBS_B})),
        termination_reason=TerminationReason.SUCCESS, final_isr_hash="h",
    )
    assert stable.repair_stability == 1.0
    # oscillation evidence: A resolved 0..3 (stable); B resolved at 1 and 3
    # only -> one gap -> B's stability 0.0 -> mean 0.5
    gapped = MultiDefectRunResult(
        evolution_id="e", initial_isr_hash="h", defect_ids=(OBS_A, OBS_B),
        generations=(gen(0, {OBS_A}), gen(1, {OBS_A, OBS_B}),
                      gen(2, {OBS_A}), gen(3, {OBS_A, OBS_B})),
        termination_reason=TerminationReason.SUCCESS, final_isr_hash="h",
    )
    assert gapped.repair_stability == 0.5
    empty = MultiDefectRunResult(
        evolution_id="e", initial_isr_hash="h", defect_ids=(OBS_A, OBS_B),
        generations=(), termination_reason=TerminationReason.SUCCESS,
        final_isr_hash="h",
    )
    assert empty.repair_stability == 1.0  # no resolutions -> vacuous 1.0


# -- 9. Determinism at trajectory level ------------------------------------------------

def test_replay_determinism_at_trajectory_level():
    results = []
    for _ in range(2):
        coordinator, defective, defect_set, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(
            StagedRepairVariation(include_rewire=True),
            interacting=True,
        )
        results.append(coordinator.run_multi_defect(
            defective, defect_set, broken_artifact, broken_run,
            baseline_artifact, baseline_run,
            max_generations=5, population_size=4, seed=0,
        ))
    a, b = results
    assert a.termination_reason is b.termination_reason
    assert a.succeeded == b.succeeded
    assert len(a.generations) == len(b.generations)
    for ga, gb in zip(a.generations, b.generations):
        assert ga.selected_operator_id == gb.selected_operator_id
        assert dict(ga.profile.resolutions) == dict(gb.profile.resolutions)
        assert ga.resolved_defects == gb.resolved_defects
        # trajectory-level comparison: same operator attacked, same defect
        # regressed (candidate_ids embed run-volatile gen>=1 ISR hashes --
        # Phase-28 provenance debt, tracked for R2.9.7)
        assert [
            (rid.split(":", 1)[0], reg) for rid, reg in ga.regression_rejections
        ] == [
            (rid.split(":", 1)[0], reg) for rid, reg in gb.regression_rejections
        ]
    assert a.repair_stability == b.repair_stability
