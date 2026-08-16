"""R2.9.8 -- Evolution Engine certification gate.

Certifies the engine's BEHAVIOR across ten mandatory dimensions plus two
recorded debt dimensions. Every dimension is verified by RUNNING the actual
R2.8/R2.9.x machinery (multi-defect repair, R2.8 boundary, CausalGate,
CumulativeResolutionTracker/MultiDefectSelector, MonocultureDetector/
DeterministicDiversityInjection, EvidenceBasedScheduler, ledger chain + tamper
detection, R2.9.7 three-identity audit) and reducing the observed evidence to a
``DimensionResult`` -- never a flag or declaration.

Verdict rules (certifier-internal, exercised here):

* any mandatory FAIL                 -> NOT_CERTIFIED
* all mandatory PASS                 -> CERTIFIED
* otherwise (recorded debt/limitation)-> QUALIFIED

The debt dimensions are non-mandatory and actionable:

* ``provenance_content_identity`` -- KNOWN_DEBT with
  ``remediation_target="phase28_identity_migration"`` and the R2.9.7 audit
  evidence (semantic identity stable/reproducible; Phase-28 content_hash
  conflates volatile provenance). It must NOT block certification.
* ``phase28_identity_migration`` -- NOT_CERTIFIED (out of scope for R2.9.8),
  non-mandatory.

Determinism note (same discipline as R2.9.4-R2.9.7): the base ISR carries
default provenance and all verification seeds are fixed, so two certifications
of the same anchors produce the same certification_id and content_hash. The
content hash canonicalizes sets/enums so it never depends on hash-randomization.

The real-substrate (Docker) path is the honest environment gate: SUCCESS ->
PASS -> CERTIFIED; POPULATION_EXHAUSTION -> recorded KNOWN_DEBT limitation
(remediation_target -> r29.3 substrate) -> QUALIFIED; any other failure -> FAIL.
It is never silent.
"""
from __future__ import annotations

import dataclasses
import tempfile
from pathlib import Path

import pytest

from constitutional_architecture.isr.model import (
    ISR,
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
    DeterministicDiversityInjection,
    DiversityDiagnostics,
    EvolutionLedger,
    EvidenceBasedScheduler,
    MonocultureDetector,
    MultiGenerationEvolutionCoordinator,
    NullMutation,
    RandomFSMExploration,
    TerminationReason,
    TransitionRestoration,
    apply_restoration,
    docker_available,
    stable_isr_hash,
)
from tiannara.application.evolution.candidate_gate import GateContext
from tiannara.application.evolution.candidate_sandbox import CompiledCandidate
from tiannara.application.evolution.compiler_sandbox import hash_artifact
from tiannara.application.evolution.evolution_certification import (
    CertificationStatus,
    DimensionResult,
    EngineVerdict,
    EvolutionCertifier,
)
from tiannara.application.evolution.evolution_certification_dimensions import (
    DEBT_DIMENSIONS,
    build_all_dimension_verifiers,
    build_debt_dimension_verifiers,
    build_dimension_verifiers,
)
from tiannara.application.evolution.evolution_state import DiversityMetrics
from tiannara.application.evolution.identity import IdentityExtractor
from tiannara.application.evolution.multi_defect import DefectSet
from tiannara.application.evolution.mutation_operators import (
    ISRDelta,
    MutationCandidate,
)
from tiannara.application.evolution.operator_scheduling import OperatorStatistics
from tiannara.application.evolution.reproducibility_audit import (
    ReproducibilityAuditor,
)
from tiannara.domain.models.evidence import TestRunResult
from tiannara.domain.models.observation import (
    FailureCategory,
    FailureObservation,
    FailurePhase,
)

COROUTINES = tuple(f"op{i}" for i in range(12))

_DEFAULT = object()

_ANCHORS = {
    "engine": "r2.9.8",
    "substrate": "fsm",
    "semantic_schema": "fsm.semantic.v1",
    "ledger": "evolution",
}


# -- substrate helpers (faithful to R2.9.6/R2.9.7) ----------------------------

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


def _defect_set(n_defects: int) -> DefectSet:
    return DefectSet(tuple(
        _obs(COROUTINES[i], f"obs-{i}") for i in range(n_defects)
    ))


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


def _isr(n_defects: int, resolving: bool) -> ISR:
    """Independent substrate: one workflow per defect."""
    workflows = []
    for i in range(n_defects):
        coroutine = COROUTINES[i]
        awaited = _awaiting_state(f"wf{i}-await", coroutine)
        final = WorkflowState(id=f"wf{i}-final", name="final", state_type=StateType.FINAL)
        transitions = ()
        if resolving:
            transitions = (_edge(awaited, final, coroutine),)
        workflows.append(Workflow(
            id=f"wf{i}", name=f"wf{i}",
            states=(awaited, final), transitions=transitions,
        ))
    return ISR(system=System(
        id="sys", name="OrderSystem",
        modules=(Module(id="m", name="M", workflows=tuple(workflows)),),
    ))


def _interacting_isr(n_defects: int, resolving: bool) -> ISR:
    """Interacting substrate: ONE workflow with n awaiting states + one final."""
    awaits = [_awaiting_state(f"order-await-{COROUTINES[i]}", COROUTINES[i])
              for i in range(n_defects)]
    final = WorkflowState(id="order-final", name="final", state_type=StateType.FINAL)
    transitions = ()
    if resolving:
        transitions = tuple(
            _edge(aw, final, COROUTINES[i]) for i, aw in enumerate(awaits)
        )
    return ISR(system=System(
        id="sys", name="OrderSystem",
        modules=(Module(id="m", name="M", workflows=(
            Workflow(id="order", name="order", states=(*awaits, final),
                     transitions=transitions),
        )),),
    ))


def _has_resolution(isr: ISR, coroutine: str | None = None) -> bool:
    """Faithful substrate predicate: an awaiting state is resolved iff a
    transition with that trigger exists in the same workflow. With no
    coroutine, every awaiting state must be resolved (full-suite run)."""
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
    coroutine, built through ``apply_restoration`` (closure-valid)."""
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
    """Interaction attack vector: fix the target coroutine by re-pointing the
    whole workflow at it, silently dropping the other defect's resolution.
    Boundary-valid (surfaces intact); must be caught as a regression by
    execution + tracker."""
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


# -- variation ensembles --------------------------------------------------------

class LongHorizonVariation:
    """Staged repair: generation ``seed`` repairs defect ``seed % n``; the
    coordinator passes ``seed + index``, so consecutive seeds cover every
    defect exactly once -> genuine n-generation convergence to SUCCESS."""

    @property
    def operator_ids(self):
        return ("transition_restoration",)

    def generate(self, current_isr, defect_set, population_size, seed):
        obs = defect_set.observations[seed % len(defect_set)]
        proposed = _restore_candidate(current_isr, obs)
        return (proposed,) if proposed is not None else ()


class StagedRepairVariation:
    """Repairs the FIRST defect before ``seed >= gate``, then the SECOND,
    optionally alongside the rewire attack (regression control). Honest repairs
    reuse ``_restore_candidate``; the attack is built through ``apply_restoration``
    so it is rejected on its merits, never on construction."""

    def __init__(self, gate: int = 1, include_rewire: bool = False):
        self._gate = gate
        self._include_rewire = include_rewire

    @property
    def operator_ids(self):
        return ("transition_restoration", "rewire_vector")

    def generate(self, current_isr, defect_set, population_size, seed):
        order = list(defect_set.observations)
        targets = (order[0],) if seed < self._gate else (order[1],)
        candidates = []
        for obs in targets:
            proposed = _restore_candidate(current_isr, obs)
            if proposed is not None:
                candidates.append(proposed)
        if seed >= self._gate and self._include_rewire:
            rewire = _rewire_candidate(current_isr, order[1], order[0])
            if rewire is not None:
                candidates.append(rewire)
        return tuple(sorted(candidates, key=lambda c: c.candidate_id))


class DeceptiveOnlyVariation:
    """Negative control: only the deceptive strip candidate is ever proposed.
    The R2.8 boundary must reject it at the identity layer."""

    def generate(self, current_isr, defect_set, population_size, seed):
        strip = _strip_candidate(current_isr, defect_set.observations[1])
        return (strip,) if strip is not None else ()


# -- sandbox (observation-aware execution oracle) -------------------------------

class FsmStubSandbox:
    """Hermetic FSM substrate. ``run_tests(artifact, observation=None)`` is
    the per-observation execution oracle."""

    def __init__(self):
        self._artifact_isr: dict[str, ISR] = {}

    def build(self, isr: ISR, workspace: str | None = None) -> CompiledCandidate:
        root = Path(workspace) if workspace else Path(tempfile.mkdtemp(prefix="r298-"))
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


def _metrics(entropy, dup_rate, size=8):
    return DiversityMetrics(size, size, size, {"op": size}, entropy, 0.0, dup_rate)


# -- concrete machinery harness ---------------------------------------------------

class CertificationHarness:
    """Runs the actual R2.8/R2.9.x machinery per dimension. Each ``verify_*``
    method executes the real component and derives its ``DimensionResult`` from
    the observed evidence."""

    def __init__(self):
        self.extractor = IdentityExtractor()
        self.auditor = ReproducibilityAuditor(self.extractor)

    # -- low-level runs ------------------------------------------------------

    def _run_multi_defect(self, n_defects, seed, ledger=None):
        defective = _isr(n_defects, resolving=False)
        defect_set = _defect_set(n_defects)
        sandbox = FsmStubSandbox()
        baseline_artifact = sandbox.build(_isr(n_defects, resolving=True))
        baseline_run = sandbox.run_tests(baseline_artifact)
        broken_artifact = sandbox.build(defective)
        broken_run = sandbox.run_tests(broken_artifact)
        coordinator = MultiGenerationEvolutionCoordinator(
            sandbox=sandbox,
            gate=CandidateGate.default(),
            variation=LongHorizonVariation(),
            selection=DeterministicComplexityPreference(),
            ledger=ledger,
        )
        result = coordinator.run_multi_defect(
            defective, defect_set, broken_artifact, broken_run,
            baseline_artifact, baseline_run,
            max_generations=n_defects, population_size=1, seed=seed,
        )
        return defective, defect_set, result

    def _run_trajectory(self, n_defects, seed):
        """Deterministic reconstruction bound to the run's own reported hashes.
        Returns (all_bindings_hold, trajectory)."""
        defective, defect_set, result = self._run_multi_defect(n_defects, seed)
        if not result.succeeded:
            return False, [defective]
        current = defective
        variation = LongHorizonVariation()
        trajectory = [defective]
        for index, gen in enumerate(result.generations):
            candidates = variation.generate(current, defect_set, 1, seed + index)
            if len(candidates) != 1:
                return False, trajectory
            candidate = candidates[0]
            if gen.selected_operator_id != "transition_restoration":
                return False, trajectory
            if index == 0:
                if gen.parent_isr_hash != stable_isr_hash(current):
                    return False, trajectory
                if gen.selected_candidate_id != candidate.candidate_id:
                    return False, trajectory
            elif index == 1:
                if gen.parent_isr_hash != stable_isr_hash(current):
                    return False, trajectory
            expected_resolved = frozenset(
                defect_set.observations[(seed + j) % n_defects].evidence_hash
                for j in range(index + 1)
            )
            if gen.resolved_defects != expected_resolved:
                return False, trajectory
            current = candidate.candidate_isr
            trajectory.append(current)
        return True, trajectory

    # -- 1. constructive_capability ------------------------------------------

    def verify_constructive(self) -> DimensionResult:
        _, _, result = self._run_multi_defect(3, seed=0)
        ok = result.succeeded
        return DimensionResult(
            dimension="constructive_capability",
            status=CertificationStatus.PASS if ok else CertificationStatus.FAIL,
            mandatory=True,
            evidence={
                "termination_reason": result.termination_reason.value,
                "generations": len(result.generations),
            },
            notes=(
                "multi-defect repair with LongHorizonVariation converges to "
                "SUCCESS over a 3-defect substrate" if ok
                else f"multi-defect repair did not converge: {result.termination_reason.value}"
            ),
        )

    # -- 2. boundary_compliance ------------------------------------------------

    def verify_boundary(self) -> DimensionResult:
        defective = _interacting_isr(2, resolving=False)
        defect_set = _defect_set(2)
        sandbox = FsmStubSandbox()
        baseline_artifact = sandbox.build(_interacting_isr(2, resolving=True))
        baseline_run = sandbox.run_tests(baseline_artifact)
        broken_artifact = sandbox.build(defective)
        broken_run = sandbox.run_tests(broken_artifact)
        state = MultiGenerationEvolutionCoordinator(
            sandbox=sandbox,
            gate=CandidateGate.default(),
            variation=DeceptiveOnlyVariation(),
            selection=DeterministicComplexityPreference(),
        ).run_multi_defect(
            defective, defect_set, broken_artifact, broken_run,
            baseline_artifact, baseline_run,
            max_generations=3, population_size=4, seed=0,
            protected_invariants=(AwaitingSurfaceIntactInvariant(),),
            deceptive_operator_ids=("test_deletion",),
        )
        ok = state.deceptive_rejected and (
            state.termination_reason is TerminationReason.NO_FEASIBLE_CANDIDATES
        )
        return DimensionResult(
            dimension="boundary_compliance",
            status=CertificationStatus.PASS if ok else CertificationStatus.FAIL,
            mandatory=True,
            evidence={
                "deceptive_rejected": state.deceptive_rejected,
                "termination_reason": state.termination_reason.value,
            },
            notes=(
                "deceptive awaiting-surface strip is rejected at the R2.8 "
                "identity layer; no feasible candidate remains" if ok
                else "boundary failed to reject the deceptive candidate"
            ),
        )

    # -- 3. causal_validity ----------------------------------------------------

    def verify_causal(self) -> DimensionResult:
        defective = _isr(1, resolving=False)
        obs = _defect_set(1).observations[0]
        candidate = _restore_candidate(defective, obs)
        sandbox = FsmStubSandbox()
        candidate_artifact = sandbox.build(candidate.candidate_isr)
        candidate_run = sandbox.run_tests(candidate_artifact)
        indep_hash = hash_artifact(sandbox.build(candidate.candidate_isr).source_root)
        baseline_artifact = sandbox.build(_isr(1, resolving=True))
        baseline_run = sandbox.run_tests(baseline_artifact)
        broken_artifact = sandbox.build(defective)
        broken_run = sandbox.run_tests(broken_artifact)
        ctx = GateContext(
            candidate_isr=candidate.candidate_isr,
            candidate_artifact=candidate_artifact,
            candidate_run=candidate_run,
            baseline_artifact=baseline_artifact,
            baseline_run=baseline_run,
            observation=obs,
            mutation=candidate,
            parent_isr=candidate.parent_isr,
            broken_artifact=broken_artifact,
            broken_artifact_hash=hash_artifact(broken_artifact.source_root),
            independent_recompile_hash=indep_hash,
        )
        verdict = CandidateGate.default().evaluate(ctx)
        causal = next(
            (r for r in verdict.gate_results if r.gate_id == "causal"), None,
        )
        ok = verdict.accept and causal is not None and causal.passed
        return DimensionResult(
            dimension="causal_validity",
            status=CertificationStatus.PASS if ok else CertificationStatus.FAIL,
            mandatory=True,
            evidence={"causal_gate_passed": bool(causal is not None and causal.passed)},
            notes=(
                "honest candidate satisfies the CausalGate (ISR delta, closure, "
                "fresh recompile, changed artifact)" if ok
                else "CausalGate rejected the honest candidate"
            ),
        )

    # -- 4. regression_safety ---------------------------------------------------

    def verify_regression(self) -> DimensionResult:
        defective = _interacting_isr(2, resolving=False)
        defect_set = _defect_set(2)
        sandbox = FsmStubSandbox()
        baseline_artifact = sandbox.build(_interacting_isr(2, resolving=True))
        baseline_run = sandbox.run_tests(baseline_artifact)
        broken_artifact = sandbox.build(defective)
        broken_run = sandbox.run_tests(broken_artifact)
        state = MultiGenerationEvolutionCoordinator(
            sandbox=sandbox,
            gate=CandidateGate.default(),
            variation=StagedRepairVariation(gate=1, include_rewire=True),
            selection=DeterministicComplexityPreference(),
        ).run_multi_defect(
            defective, defect_set, broken_artifact, broken_run,
            baseline_artifact, baseline_run,
            max_generations=5, population_size=4, seed=0,
        )
        rejected = [
            (rid, reg) for gen in state.generations
            for rid, reg in gen.regression_rejections
        ]
        ok = state.succeeded and any(
            "rewire_vector" in rid for rid, _ in rejected
        )
        return DimensionResult(
            dimension="regression_safety",
            status=CertificationStatus.PASS if ok else CertificationStatus.FAIL,
            mandatory=True,
            evidence={
                "succeeded": state.succeeded,
                "regression_rejections": [
                    {"candidate": rid.split(":", 1)[0], "regressed": sorted(reg)}
                    for rid, reg in rejected
                ],
            },
            notes=(
                "rewire candidate (fixes B by dropping A) is hard-rejected as a "
                "regression by the cumulative tracker; A stays resolved" if ok
                else "regression protection failed"
            ),
        )

    # -- 5. diversity_preservation ------------------------------------------------

    def verify_diversity(self) -> DimensionResult:
        defective = _isr(1, resolving=False)
        obs = _defect_set(1).observations[0]
        detector = MonocultureDetector()
        collapsed = _metrics(entropy=0.0, dup_rate=1.0)
        detected = detector.is_monoculture(collapsed)
        diag = DiversityDiagnostics(detector).diagnose([
            _metrics(entropy=2.0, dup_rate=0.1),
            _metrics(entropy=0.0, dup_rate=1.0),
        ])
        policy = DeterministicDiversityInjection(injection_count=4)
        monoculture = [NullMutation().propose(defective, obs)] * 6
        metrics = _metrics(entropy=0.0, dup_rate=1 - 1 / 6, size=6)

        def generate_more(count, sub_seed):
            return RandomFSMExploration().generate(defective, obs, count, sub_seed)

        restored = list(policy.apply(monoculture, metrics, generate_more, seed=3))
        ok = detected and diag.monoculture_detected and len(restored) > 1
        return DimensionResult(
            dimension="diversity_preservation",
            status=CertificationStatus.PASS if ok else CertificationStatus.FAIL,
            mandatory=True,
            evidence={
                "monoculture_detected": detected,
                "diagnostic_first_generation": diag.first_monoculture_generation,
                "unique_candidates_after_injection": len(restored),
            },
            notes=(
                "MonocultureDetector flags the collapse and "
                "DeterministicDiversityInjection restores distinct candidates" if ok
                else "anti-monoculture machinery failed"
            ),
        )

    # -- 6. adaptive_scheduling --------------------------------------------------

    def verify_scheduling(self) -> DimensionResult:
        scheduler = EvidenceBasedScheduler(exploration_floor=0.2)
        stats = {
            n: OperatorStatistics(n, a, f, r)
            for n, (a, f, r) in {
                "transition_restoration": (40, 31, 28),
                "random_fsm_exploration": (40, 7, 3),
            }.items()
        }
        allocation = scheduler.schedule(stats, population_size=20, seed=1)
        ok = (
            allocation.allocations["transition_restoration"]
            > allocation.allocations["random_fsm_exploration"]
            and allocation.exploration_reserved > 0
        )
        return DimensionResult(
            dimension="adaptive_scheduling",
            status=CertificationStatus.PASS if ok else CertificationStatus.FAIL,
            mandatory=True,
            evidence={
                "allocations": dict(allocation.allocations),
                "exploration_reserved": allocation.exploration_reserved,
            },
            notes=(
                "EvidenceBasedScheduler shifts budget to the successful operator "
                "while reserving an exploration floor" if ok
                else "scheduler failed to adapt or preserve exploration"
            ),
        )

    # -- 7. multi_generation_lineage ----------------------------------------------

    def verify_lineage(self) -> DimensionResult:
        ok, trajectory = self._run_trajectory(3, seed=0)
        return DimensionResult(
            dimension="multi_generation_lineage",
            status=CertificationStatus.PASS if ok else CertificationStatus.FAIL,
            mandatory=True,
            evidence={"trajectory_nodes": len(trajectory)},
            notes=(
                "every generation binds parent_isr_hash exactly (gen 0 + 1) and "
                "the cumulative resolved-defect profile exactly" if ok
                else "lineage binding broke"
            ),
        )

    # -- 8. semantic_reproducibility ------------------------------------------------

    def verify_semantic_repro(self) -> DimensionResult:
        ok_a, traj_a = self._run_trajectory(3, seed=0)
        ok_b, traj_b = self._run_trajectory(3, seed=0)
        report = self.auditor.audit_cross_run(traj_a, traj_b)
        ok = ok_a and ok_b and report.semantic_reproducible
        return DimensionResult(
            dimension="semantic_reproducibility",
            status=CertificationStatus.PASS if ok else CertificationStatus.FAIL,
            mandatory=True,
            evidence={
                "generations_compared": report.generations_compared,
                "semantic_reproducible": report.semantic_reproducible,
                "content_reproducible": report.content_reproducible,
                "divergence_cause": report.divergence_cause,
            },
            notes=(
                "two independent trajectories reproduce semantically; the "
                "Phase-28 content divergence is the audited debt" if ok
                else "semantic reproducibility failed"
            ),
        )

    # -- 9. evidence_integrity -----------------------------------------------------

    def verify_evidence(self) -> DimensionResult:
        ledger = EvolutionLedger()
        self._run_multi_defect(3, seed=0, ledger=ledger)
        chain_ok = ledger.verify_event_chain() is True
        events = ledger.events()
        tamper_detected = False
        if events:
            forged = events[0].model_copy(
                update={"payload": {**events[0].payload, "forged": True}},
            )
            tamper_detected = forged.is_intact() is False
        ok = chain_ok and tamper_detected
        return DimensionResult(
            dimension="evidence_integrity",
            status=CertificationStatus.PASS if ok else CertificationStatus.FAIL,
            mandatory=True,
            evidence={
                "chain_valid": chain_ok,
                "tamper_detected": tamper_detected,
                "events": len(events),
            },
            notes=(
                "the hash-chained ledger validates and post-hoc tampering breaks "
                "is_intact()" if ok else "evidence integrity failed"
            ),
        )

    # -- 10. identity_separation -----------------------------------------------------

    def verify_identity_separation(self) -> DimensionResult:
        derived = _isr(1, resolving=False).with_system(
            _isr(1, resolving=False).system,
        )
        report = self.auditor.audit_identity_separation(derived)
        ok = report.semantic_is_stable_identity and report.phase28_tainted_by_provenance
        return DimensionResult(
            dimension="identity_separation",
            status=CertificationStatus.PASS if ok else CertificationStatus.FAIL,
            mandatory=True,
            evidence={
                "semantic_is_stable_identity": report.semantic_is_stable_identity,
                "phase28_tainted_by_provenance": report.phase28_tainted_by_provenance,
                "taint_fields": sorted(report.taint_fields),
            },
            notes=(
                "semantic identity is stable while the Phase-28 content_hash is "
                "tainted by provenance (the audited conflation)" if ok
                else "identity separation failed"
            ),
        )

    # -- recorded debt evidence -------------------------------------------------

    def provenance_debt_evidence(self) -> dict[str, object]:
        _, traj_a = self._run_trajectory(3, seed=0)
        _, traj_b = self._run_trajectory(3, seed=0)
        report = self.auditor.audit_cross_run(traj_a, traj_b)
        return {
            "semantic_reproducible": report.semantic_reproducible,
            "content_reproducible": report.content_reproducible,
            "divergence_cause": report.divergence_cause,
            "generations_compared": report.generations_compared,
            "source": "R2.9.7 three-identity reproducibility audit (cross-run evidence)",
        }

    # -- real-substrate (Docker) dimension ----------------------------------------

    def verify_real_substrate(self, workspace_root: Path) -> DimensionResult:
        from tiannara.application.compiler.fastapi_hexagonal_backend import (
            FastAPIHexagonalBackend,
        )
        from tiannara.application.evolution import RealBackendSandbox

        defective = _isr(1, resolving=False)
        real = RealBackendSandbox(backend=FastAPIHexagonalBackend())
        broken_candidate = real.build(defective, workspace=str(workspace_root / "broken"))
        broken_run = real.run_tests(broken_candidate)
        observation = real.classifier.classify(real.to_evidence(broken_run))
        if observation is None:
            return DimensionResult(
                dimension="real_substrate_execution",
                status=CertificationStatus.FAIL,
                mandatory=True,
                evidence={},
                notes="real substrate produced no failure observation",
            )
        baseline_candidate = real.build(
            _isr(1, resolving=True), workspace=str(workspace_root / "kg"),
        )
        baseline_run = real.run_tests(baseline_candidate)
        state = MultiGenerationEvolutionCoordinator(
            sandbox=real,
            gate=CandidateGate.default(),
            variation=_SingleRepairRealVariation(),
            selection=DeterministicComplexityPreference(),
        ).run(
            defective_isr=defective,
            observation=observation,
            broken_artifact=broken_candidate,
            broken_run=broken_run,
            baseline_artifact=baseline_candidate,
            baseline_run=baseline_run,
            max_generations=2, population_size=1, seed=0,
        )
        if state.succeeded:
            return DimensionResult(
                dimension="real_substrate_execution",
                status=CertificationStatus.PASS,
                mandatory=True,
                evidence={"termination_reason": state.termination_reason.value},
                notes="real Docker substrate converged to a working repair",
            )
        if state.termination_reason is TerminationReason.POPULATION_EXHAUSTION:
            return DimensionResult(
                dimension="real_substrate_execution",
                status=CertificationStatus.KNOWN_DEBT,
                mandatory=True,
                evidence={"termination_reason": state.termination_reason.value},
                notes=(
                    "real substrate exhausted its candidate population; recorded "
                    "as a QUALIFIED limitation, never a silent pass or block"
                ),
                remediation_target="r29.3_substrate_population_exhaustion",
            )
        return DimensionResult(
            dimension="real_substrate_execution",
            status=CertificationStatus.FAIL,
            mandatory=True,
            evidence={"termination_reason": state.termination_reason.value},
            notes="real substrate run failed on the merits",
        )


class _SingleRepairRealVariation:
    """Lean real-substrate variation: proposes ONLY the targeted repair."""

    def generate(self, current_isr, observation, population_size, seed):
        from tiannara.application.evolution import TransitionRestorationOperator
        repair = TransitionRestorationOperator().propose(current_isr, observation)
        return (repair,) if repair is not None else ()


# -- cert_harness fixture ----------------------------------------------------------

class _CertHarnessFactory:
    """Builds configured certifiers. ``all_passing`` uses only the ten
    behavioral dimensions; ``with_provenance_debt`` adds the two recorded debt
    dimensions; ``with_failing_dimension`` forces one mandatory FAIL;
    ``real_path`` adds the Docker real-substrate dimension."""

    def __init__(self):
        self.harness = CertificationHarness()

    def _certifier(self, verifiers) -> EvolutionCertifier:
        return EvolutionCertifier(
            ledger=EvolutionLedger(),
            anchors=dict(_ANCHORS),
            verifiers=verifiers,
        )

    def all_passing(self) -> EvolutionCertifier:
        return self._certifier(build_dimension_verifiers(self.harness))

    def with_provenance_debt(self) -> EvolutionCertifier:
        return self._certifier(build_all_dimension_verifiers(self.harness))

    def with_failing_dimension(self, name: str) -> EvolutionCertifier:
        verifiers = build_dimension_verifiers(self.harness)

        def failing() -> DimensionResult:
            return DimensionResult(
                dimension=name, status=CertificationStatus.FAIL,
                mandatory=True, notes="forced failure for verdict-rule test",
            )

        verifiers[name] = failing
        return self._certifier(verifiers)

    def real_path(self, workspace_root: Path) -> EvolutionCertifier:
        verifiers = build_all_dimension_verifiers(self.harness)
        verifiers["real_substrate_execution"] = (
            lambda: self.harness.verify_real_substrate(workspace_root)
        )
        return self._certifier(verifiers)


@pytest.fixture
def cert_harness() -> _CertHarnessFactory:
    return _CertHarnessFactory()


# -- 1. Behavioral pass -> CERTIFIED ---------------------------------------------

def test_engine_certified_when_behavioral_pass(cert_harness):
    artifact = cert_harness.all_passing().certify()
    assert artifact.engine_verdict is EngineVerdict.CERTIFIED
    assert artifact.mandatory_passed
    assert len(artifact.dimensions) == 10
    assert all(
        d.status is CertificationStatus.PASS for d in artifact.dimensions
    )


# -- 2. Recorded debt does not block ---------------------------------------------

def test_known_debt_does_not_block_certification(cert_harness):
    artifact = cert_harness.with_provenance_debt().certify()
    assert artifact.engine_verdict is EngineVerdict.CERTIFIED
    assert artifact.mandatory_passed
    statuses = {d.dimension: d.status for d in artifact.dimensions}
    assert statuses["provenance_content_identity"] is CertificationStatus.KNOWN_DEBT
    assert statuses["phase28_identity_migration"] is CertificationStatus.NOT_CERTIFIED
    assert len(artifact.dimensions) == 12


# -- 3. The KNOWN_DEBT is actionable ----------------------------------------------

def test_known_debt_is_actionable(cert_harness):
    artifact = cert_harness.with_provenance_debt().certify()
    debt = next(
        d for d in artifact.dimensions
        if d.dimension == "provenance_content_identity"
    )
    assert debt.remediation_target == "phase28_identity_migration"
    assert debt.evidence.get("divergence_cause") == "provenance_volatility"
    assert debt.evidence.get("semantic_reproducible") is True
    assert debt.evidence.get("content_reproducible") is False
    migration = next(
        d for d in artifact.dimensions
        if d.dimension == "phase28_identity_migration"
    )
    assert migration.status is CertificationStatus.NOT_CERTIFIED
    assert not migration.mandatory


# -- 4. Mandatory FAIL -> NOT_CERTIFIED -------------------------------------------

def test_mandatory_failure_blocks_certification(cert_harness):
    artifact = cert_harness.with_failing_dimension("boundary_compliance").certify()
    assert artifact.engine_verdict is EngineVerdict.NOT_CERTIFIED
    assert not artifact.mandatory_passed
    failed = next(d for d in artifact.dimensions if d.dimension == "boundary_compliance")
    assert failed.status is CertificationStatus.FAIL
    assert failed.mandatory


# -- 5. render_summary renders the matrix -------------------------------------------

def test_render_summary_renders_matrix(cert_harness):
    artifact = cert_harness.with_provenance_debt().certify()
    summary = artifact.render_summary()
    for d in artifact.dimensions:
        assert d.dimension in summary
        assert d.status.value in summary
    assert "engine_verdict" in summary
    assert EngineVerdict.CERTIFIED.value in summary


# -- 6. Tamper-evident content hash -------------------------------------------------

def test_artifact_content_hash_is_tamper_evident(cert_harness):
    artifact = cert_harness.all_passing().certify()
    original = artifact.content_hash()
    tampered = dataclasses.replace(
        artifact, engine_verdict=EngineVerdict.QUALIFIED,
    )
    assert tampered.content_hash() != original
    # any single dimension flip is also detectable
    dims = list(artifact.dimensions)
    flipped = dataclasses.replace(
        dims[0],
        status=CertificationStatus.FAIL,
    )
    reordered = dataclasses.replace(artifact, dimensions=tuple([flipped, *dims[1:]]))
    assert reordered.content_hash() != original


# -- 7. Chain-anchored as a CERTIFICATION event -------------------------------------

def test_artifact_anchored_as_certification_event(cert_harness):
    certifier = cert_harness.with_provenance_debt()
    artifact = certifier.certify()
    events = [e for e in certifier.ledger.events()
              if e.event_type.value == "certification"]
    assert len(events) == 1
    event = events[0]
    assert event.subject_id == artifact.certification_id
    assert event.payload["artifact_content_hash"] == artifact.content_hash()
    assert event.payload["engine_verdict"] == artifact.engine_verdict.value
    assert certifier.ledger.verify_event_chain() is True


# -- 8. Deterministic id + hash -----------------------------------------------------

def test_artifact_is_deterministic(cert_harness):
    certifier = cert_harness.all_passing()
    first = certifier.certify()
    second = certifier.certify()
    assert first.certification_id == second.certification_id
    assert first.content_hash() == second.content_hash()
    assert first.engine_verdict is second.engine_verdict
    # and independently-constructed certifiers over the same anchors agree
    other = cert_harness.all_passing().certify()
    assert other.certification_id == first.certification_id
    assert other.content_hash() == first.content_hash()


# -- 9. Real-substrate (Docker) certification ---------------------------------------

@pytest.mark.skipif(
    not docker_available(), reason="R2.9.8 real-substrate certification requires Docker",
)
def test_real_path_certifies_or_qualifies(cert_harness, tmp_path):
    artifact = cert_harness.real_path(tmp_path).certify()
    assert artifact.engine_verdict in (
        EngineVerdict.CERTIFIED, EngineVerdict.QUALIFIED,
    )
    real = next(
        d for d in artifact.dimensions if d.dimension == "real_substrate_execution"
    )
    assert real.mandatory
    if artifact.engine_verdict is EngineVerdict.QUALIFIED:
        assert real.status is CertificationStatus.KNOWN_DEBT
        assert real.remediation_target
