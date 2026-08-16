"""Phase-28 identity migration compatibility gates (ADR adr-phase28-identity-migration).

The ADR's before/after compatibility evidence, made executable. Each gate
runs the real machinery:

* Governance change-detection gates (the gates a narrow FSM-only projection
  would FAIL): entity-only, deployment-only, and module-policy-only edits must
  move ``content_hash``.
* Provenance/version isolation: ``created_at``/``parent_hash``/``version``
  never taint the hash.
* Identity unification: ``content_hash == semantic_hash`` and
  ``stable_isr_hash`` collapsed onto the projection.
* Reproducibility: ``content_reproducible`` flips to ``true``; the gen >= 1
  parent-binding compounding is gone.
* Lineage / causal / regression: the R2.8/R2.9.x guarantees hold.
"""
from __future__ import annotations

import dataclasses
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from constitutional_architecture.isr.model import (
    Deployment,
    Entity,
    EnvironmentTier,
    ISR,
    Module,
    Policy,
    PolicyType,
    ScalingConfig,
    StateType,
    System,
    SystemMetadata,
    Workflow,
    WorkflowState,
    WorkflowTransition,
)
from tiannara.application.evolution import (
    CandidateGate,
    DeterministicComplexityPreference,
    EvolutionLedger,
    MultiGenerationEvolutionCoordinator,
    TransitionRestoration,
    apply_restoration,
    stable_isr_hash,
)
from tiannara.application.evolution.candidate_gate import GateContext
from tiannara.application.evolution.candidate_sandbox import CompiledCandidate
from tiannara.application.evolution.compiler_sandbox import hash_artifact
from tiannara.application.evolution.identity import IdentityExtractor
from tiannara.application.evolution.multi_defect import DefectSet
from tiannara.application.evolution.mutation_operators import ISRDelta, MutationCandidate
from tiannara.application.evolution.reproducibility_audit import ReproducibilityAuditor
from tiannara.domain.models.evidence import TestRunResult
from tiannara.domain.models.observation import (
    FailureCategory,
    FailureObservation,
    FailurePhase,
)

COROUTINES = tuple(f"op{i}" for i in range(12))


# -- FSM substrate helpers (faithful to R2.9.6/R2.9.7) ------------------------

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


def _has_resolution(isr: ISR, coroutine: str | None = None) -> bool:
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


def _restore_candidate(current_isr: ISR, obs: FailureObservation):
    coroutine = TransitionRestoration.extract_coroutine_name(obs)
    located = _awaiting_target(current_isr, coroutine)
    if located is None:
        return None
    workflow_id, state_id, final_id = located
    import json as _json
    entry = _json.dumps({
        "workflow_id": workflow_id,
        "from_state_id": state_id,
        "to_state_id": final_id,
        "trigger": coroutine,
    }, sort_keys=True)
    candidate_isr = apply_restoration(current_isr, (entry,))
    return MutationCandidate(
        candidate_id=f"transition_restoration:{stable_isr_hash(candidate_isr)[:12]}",
        operator_id="transition_restoration",
        candidate_isr=candidate_isr,
        parent_isr=current_isr,
        mutation_delta=ISRDelta((entry,)),
        hypothesis=f"restore required async resolution of '{coroutine}'",
    )


class LongHorizonVariation:
    """Staged repair: generation ``seed`` repairs defect ``seed % n``."""

    @property
    def operator_ids(self):
        return ("transition_restoration",)

    def generate(self, current_isr, defect_set, population_size, seed):
        obs = defect_set.observations[seed % len(defect_set)]
        proposed = _restore_candidate(current_isr, obs)
        return (proposed,) if proposed is not None else ()


class FsmStubSandbox:
    """Hermetic FSM substrate (observation-aware execution oracle)."""

    def __init__(self):
        self._artifact_isr: dict[str, ISR] = {}

    def build(self, isr: ISR, workspace: str | None = None) -> CompiledCandidate:
        root = Path(workspace) if workspace else Path(tempfile.mkdtemp(prefix="mig-"))
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


# -- migration harness ----------------------------------------------------------

class MigrationHarness:
    """The before/after harness: real machinery on both the FSM substrate and
    a governance-rich ISR (entities, deployment, policies)."""

    def __init__(self):
        self.extractor = IdentityExtractor()
        self.auditor = ReproducibilityAuditor(self.extractor)

    # -- governance-rich ISR -------------------------------------------------

    def known_good_isr(self) -> ISR:
        awaited = _awaiting_state("order-await", COROUTINES[0])
        final = WorkflowState(id="order-final", name="final", state_type=StateType.FINAL)
        order = Workflow(
            id="order", name="order",
            states=(awaited, final),
            transitions=(_edge(awaited, final, COROUTINES[0]),),
        )
        module = Module(
            id="m", name="M", workflows=(order,),
            entities=(
                Entity(id="e1", name="Order", description="a purchase order"),
            ),
            policies=(
                Policy(id="p1", name="auth", policy_type=PolicyType.AUTHENTICATION,
                       strategy="jwt"),
            ),
        )
        return ISR(system=System(
            id="sys", name="OrderSystem",
            modules=(module,),
            deployment=Deployment(
                id="dep1", name="prod", environment=EnvironmentTier.PRODUCTION,
                scaling=ScalingConfig(min_instances=1, max_instances=10),
            ),
            metadata=SystemMetadata(version="1.0", tags=("billing",)),
            global_policies=("audit_all",),
        ))

    @staticmethod
    def modify_entity_only(isr: ISR) -> ISR:
        module = isr.system.modules[0]
        module = dataclasses.replace(
            module, entities=(
                dataclasses.replace(module.entities[0], name="OrderV2"),
            ),
        )
        return dataclasses.replace(
            isr, system=dataclasses.replace(isr.system, modules=(module,)),
        )

    @staticmethod
    def modify_deployment_only(isr: ISR) -> ISR:
        deployment = dataclasses.replace(
            isr.system.deployment,
            scaling=dataclasses.replace(isr.system.deployment.scaling, min_instances=4),
        )
        return dataclasses.replace(
            isr, system=dataclasses.replace(isr.system, deployment=deployment),
        )

    @staticmethod
    def modify_module_policy_only(isr: ISR) -> ISR:
        module = isr.system.modules[0]
        module = dataclasses.replace(
            module, policies=(
                dataclasses.replace(module.policies[0], strategy="oauth2"),
            ),
        )
        return dataclasses.replace(
            isr, system=dataclasses.replace(isr.system, modules=(module,)),
        )

    # -- evolution runs ------------------------------------------------------

    def _run(self, n_defects: int, seed: int, generations: int, ledger=None):
        defective = _isr(n_defects, resolving=False)
        defect_set = _defect_set(n_defects)
        sandbox = FsmStubSandbox()
        baseline_artifact = sandbox.build(_isr(n_defects, resolving=True))
        baseline_run = sandbox.run_tests(baseline_artifact)
        broken_artifact = sandbox.build(defective)
        broken_run = sandbox.run_tests(broken_artifact)
        return MultiGenerationEvolutionCoordinator(
            sandbox=sandbox,
            gate=CandidateGate.default(),
            variation=LongHorizonVariation(),
            selection=DeterministicComplexityPreference(),
            ledger=ledger,
        ).run_multi_defect(
            defective, defect_set, broken_artifact, broken_run,
            baseline_artifact, baseline_run,
            max_generations=generations, population_size=1, seed=seed,
        )

    def run_evolution(self, seed: int, generations: int = 3):
        """Deterministic trajectory reconstruction bound to the run's own
        reported hashes. ``n`` defects with the staged variation converge at
        generation ``n - 1`` (n + 1 trajectory nodes), so gen >= 1 parent
        bindings are exercised (same recipe as the R2.9.7 harness)."""
        n = generations
        result = self._run(n, seed, n)
        if not result.succeeded:
            return [_isr(n, resolving=False)]
        defective = _isr(n, resolving=False)
        defect_set = _defect_set(n)
        variation = LongHorizonVariation()
        current = defective
        trajectory = [defective]
        for index, gen in enumerate(result.generations):
            candidates = variation.generate(current, defect_set, 1, seed + index)
            if len(candidates) != 1:
                break
            if gen.selected_operator_id != "transition_restoration":
                break
            current = candidates[0].candidate_isr
            trajectory.append(current)
        return trajectory

    def run_evolution_ledger(self, seed: int) -> EvolutionLedger:
        ledger = EvolutionLedger()
        self._run(3, seed, 3, ledger=ledger)
        return ledger

    def causal_evidence(self):
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
        return verdict.accept, bool(causal is not None and causal.passed)


@pytest.fixture
def migration_harness() -> MigrationHarness:
    return MigrationHarness()


# -- Governance change-detection (gates a narrow projection would FAIL) --------

def test_entity_only_change_detected(migration_harness):
    a = migration_harness.known_good_isr()
    b = migration_harness.modify_entity_only(a)
    assert a.content_hash != b.content_hash


def test_deployment_only_change_detected(migration_harness):
    a = migration_harness.known_good_isr()
    b = migration_harness.modify_deployment_only(a)
    assert a.content_hash != b.content_hash


def test_module_policy_change_detected(migration_harness):
    a = migration_harness.known_good_isr()
    b = migration_harness.modify_module_policy_only(a)
    assert a.content_hash != b.content_hash


# -- Provenance / version isolation --------------------------------------------

def test_created_at_and_version_isolated(migration_harness):
    from datetime import datetime, timezone
    from constitutional_architecture.isr.model import ISRProvenance

    base = migration_harness.known_good_isr()
    a = dataclasses.replace(
        base,
        version=1,
        provenance=ISRProvenance(
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc), parent_hash=None,
        ),
    )
    b = dataclasses.replace(
        base,
        version=2,
        provenance=ISRProvenance(
            created_at=datetime(2025, 12, 31, tzinfo=timezone.utc), parent_hash="h",
        ),
    )
    assert a.content_hash == b.content_hash
    assert a.content_hash == base.content_hash


# -- Identity unification -------------------------------------------------------

def test_content_hash_equals_semantic_hash(migration_harness):
    isr = migration_harness.known_good_isr()
    assert isr.content_hash == migration_harness.extractor.semantic_hash(isr)


def test_stable_isr_hash_collapsed_onto_projection(migration_harness):
    isr = migration_harness.known_good_isr()
    assert stable_isr_hash(isr) == isr.content_hash


def test_projection_is_full_architectural_tree(migration_harness):
    projection = migration_harness.extractor.projector.project(
        migration_harness.known_good_isr()
    )
    assert projection["modules"][0]["entities"][0]["name"] == "Order"
    assert projection["modules"][0]["policies"][0]["strategy"] == "jwt"
    assert projection["deployment"]["scaling"]["min_instances"] == 1
    assert "provenance" not in projection
    assert "created_at" not in projection


# -- Reproducibility flips ------------------------------------------------------

def test_content_reproducible_post_migration(migration_harness):
    traj_a = migration_harness.run_evolution(seed=42)
    traj_b = migration_harness.run_evolution(seed=42)
    report = migration_harness.auditor.audit_cross_run(traj_a, traj_b)
    assert report.semantic_reproducible is True
    assert report.content_reproducible is True
    assert report.divergence_cause is None


def test_gen_ge1_parent_binding_stable(migration_harness):
    traj_a = migration_harness.run_evolution(seed=7, generations=4)
    traj_b = migration_harness.run_evolution(seed=7, generations=4)
    assert len(traj_a) == len(traj_b) == 5
    for a, b in zip(traj_a, traj_b):
        assert a.provenance.parent_hash == b.provenance.parent_hash


def test_audit_taint_is_evidence_based_and_clear(migration_harness):
    isr = migration_harness.known_good_isr()
    report = migration_harness.auditor.audit_identity_separation(isr)
    assert report.semantic_is_stable_identity
    assert report.phase28_tainted_by_provenance is False
    assert report.taint_fields == ()
    assert report.semantic_hash == report.phase28_content_hash


# -- Lineage / causal / regression (the ADR's original gates) ------------------

def test_lineage_chain_valid_post_migration(migration_harness):
    ledger = migration_harness.run_evolution_ledger(seed=0)
    assert ledger.verify_event_chain() is True


def test_causal_integrity_preserved(migration_harness):
    accepted, causal_passed = migration_harness.causal_evidence()
    assert accepted is True
    assert causal_passed is True


def test_r28_r29_regression_post_migration(migration_harness):
    """The ADR gate: R2.8/R2.9.x hermetic suites remain green post-migration.

    Runs the three R2.9.x evolution suites hermetically (Docker-gated tests
    deselected -- they are exercised by the canonical full run).
    """
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", "-q",
            "tests/test_r29_6_multi_defect.py",
            "tests/test_r29_7_reproducibility_audit.py",
            "tests/test_r29_8_evolution_certification.py",
            "--deselect",
            "tests/test_r29_7_reproducibility_audit.py::test_semantic_reproducibility_under_real_execution",
            "--deselect",
            "tests/test_r29_8_evolution_certification.py::test_real_path_certifies_or_qualifies",
        ],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]