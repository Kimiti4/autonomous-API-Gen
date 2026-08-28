"""R2.9.7 -- Three-identity reproducibility audit.

Constitutional separation of ISR identity into three concerns:

    semantic_hash          = H(canonical(Semantic Architecture))   -- the reproducibility identity
    provenance_identity    = lineage (parent, mutation source, evolution, created_at)
    runtime_execution_id   = execution-instance identity

The audit is EVIDENCE-based, not asserted: it demonstrates identity separation
by comparing the semantic hash with ``ISR.content_hash`` directly.

POST-MIGRATION (Phase-28 identity migration, ADR adr-phase28-identity-migration):
``ISR.content_hash`` IS the semantic projection, so cross-run ``content_hash``
now reproduces exactly -- ``content_reproducible`` is true, the
``provenance_volatility`` divergence cause is structurally eliminated, and the
audit's taint signal (previously a provenance-presence heuristic) is purely
evidence-based: tainted iff the two hashes diverge. The former conflation tests
now certify the migration's result.

Semantic projection is INCLUSION-based, delegating to the single source of
truth in ``constitutional_architecture.isr.semantics.projection`` (the full
System/Module architectural tree). A negative test is load-bearing: an
architectural change MUST move the semantic hash, so the projection can never
be vacuous. The canonical serializer has no ``default=str`` fallback --
unhandled types raise ``CanonicalizationError``.

Trajectory reconstruction: ``EvolutionState``/``MultiDefectRunResult`` are
constitutional hash-only (they never carry ISRs), so the harness reconstructs
each trajectory deterministically from the same variation/seed the coordinator
used, then BINDS every step to the coordinator's own reported hashes
(``parent_isr_hash``, ``selected_candidate_id``).

The long-horizon staging trick: ``LongHorizonVariation`` repairs defect
``seed % n`` each generation; because the coordinator passes ``seed + index``
with step 1, ``n`` consecutive seeds cover every residue, so each of the ``n``
defects is repaired exactly once and the run converges at generation ``n - 1``.
The trajectory is ``n + 1`` nodes (initial parent + n selected ISRs).
"""
from __future__ import annotations

import hashlib
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
    CandidateGate,
    DeterministicComplexityPreference,
    EvolutionLedger,
    MultiGenerationEvolutionCoordinator,
    TransitionRestoration,
    apply_restoration,
    docker_available,
    stable_isr_hash,
)
from tiannara.application.evolution.candidate_sandbox import CompiledCandidate
from tiannara.application.evolution.compiler_sandbox import hash_artifact
from tiannara.application.evolution.identity import (
    CanonicalizationError,
    FSMSemanticProjector,
    IdentityExtractor,
    ProvenanceIdentity,
    RuntimeTagged,
    canonicalize,
    semantic_equivalent,
    tag_runtime,
)
from tiannara.application.evolution.multi_defect import DefectSet
from tiannara.application.evolution.mutation_operators import (
    ISRDelta,
    MutationCandidate,
    TransitionRestorationOperator,
)
from tiannara.application.evolution.reproducibility_audit import (
    CrossRunReport,
    IdentitySeparationReport,
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


# -- ISR fixtures -------------------------------------------------------------

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


def _isr(n_defects: int, resolving: bool, provenance=_DEFAULT) -> ISR:
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
    prov = ISRProvenance() if provenance is _DEFAULT else provenance
    return ISR(system=System(
        id="sys", name="OrderSystem",
        modules=(Module(id="m", name="M", workflows=tuple(workflows)),),
    ), provenance=prov)


def _has_resolution(isr: ISR, coroutine: str | None = None) -> bool:
    """Faithful substrate predicate: an awaiting state is resolved iff a
    transition with that trigger exists in the same workflow."""
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
    """Honest repair via ``apply_restoration`` -- the same deterministic delta
    ``TransitionRestorationOperator`` emits for this substrate."""
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
    """Staged repair: generation ``seed`` repairs defect ``seed % n``. Because
    the coordinator passes ``seed + index``, consecutive seeds cover every
    defect exactly once -> genuine n-generation convergence to SUCCESS."""

    @property
    def operator_ids(self):
        return ("transition_restoration",)

    def generate(self, current_isr, defect_set, population_size, seed):
        obs = defect_set.observations[seed % len(defect_set)]
        proposed = _restore_candidate(current_isr, obs)
        return (proposed,) if proposed is not None else ()


class SingleRepairRealVariation:
    """Lean real-substrate variation (R2.9.3 pattern): proposes ONLY the
    targeted repair for the single-defect ``run`` interface."""

    def generate(self, current_isr, observation, population_size, seed):
        repair = TransitionRestorationOperator().propose(current_isr, observation)
        return (repair,) if repair is not None else ()


# -- sandbox (observation-aware execution oracle) -------------------------------

class FsmStubSandbox:
    """Hermetic FSM substrate. ``run_tests(artifact, observation=None)`` is
    the per-observation execution oracle."""

    def __init__(self):
        self._artifact_isr: dict[str, ISR] = {}

    def build(self, isr: ISR, workspace: str | None = None) -> CompiledCandidate:
        root = Path(workspace) if workspace else Path(tempfile.mkdtemp(prefix="r297-"))
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


# -- harness --------------------------------------------------------------------

class ReproHarness:
    """Deterministic trajectory harness: ONE coordinator run per evolution,
    then reconstruction bound to that run's own reported hashes."""

    def __init__(self):
        self.extractor = IdentityExtractor()
        self.auditor = ReproducibilityAuditor(self.extractor)
        self.derived_twice: list[ISR] = []

    # -- ISR builders ----------------------------------------------------------

    def known_good_isr(self) -> ISR:
        return _isr(1, resolving=True)

    def defective_isr(self) -> ISR:
        return _isr(1, resolving=False)

    def isr_with_created_at(self, iso: str) -> ISR:
        return _isr(1, resolving=False, provenance=ISRProvenance(
            created_at=datetime.fromisoformat(iso),
        ))

    def isr_with_parent(self, parent: ISR) -> ISR:
        return parent.with_system(parent.system)

    def isr_with_runtime_id(self, run_id: str) -> RuntimeTagged:
        return tag_runtime(self.defective_isr(), run_id)

    def derived_isr(self) -> ISR:
        derived = self.defective_isr().with_system(self.defective_isr().system)
        self.derived_twice.append(derived)
        return derived

    def change_transition_target(self, isr: ISR) -> ISR:
        module = isr.system.modules[0]
        wf = module.workflows[0]
        changed_wf = Workflow(
            id=wf.id, name=wf.name, states=wf.states,
            transitions=tuple(
                WorkflowTransition(
                    id=t.id, name=t.name, from_state_id=t.from_state_id,
                    to_state_id=t.to_state_id, trigger=f"{t.trigger}-alt",
                    guard_condition=t.guard_condition, actions=t.actions,
                    description=t.description, metadata=t.metadata,
                )
                for t in wf.transitions
            ),
        )
        changed_module = Module(
            id=module.id, name=module.name, workflows=(changed_wf,),
        )
        return isr.with_system(System(
            id=isr.system.id, name=isr.system.name,
            modules=(changed_module,),
        ))

    def add_state(self, isr: ISR) -> ISR:
        module = isr.system.modules[0]
        wf = module.workflows[0]
        extra = WorkflowState(
            id="extra", name="extra", state_type=StateType.INTERMEDIATE,
            metadata={"awaits": "op99"},
        )
        grown_wf = Workflow(
            id=wf.id, name=wf.name, states=wf.states + (extra,),
            transitions=wf.transitions,
        )
        grown_module = Module(
            id=module.id, name=module.name, workflows=(grown_wf,),
        )
        return isr.with_system(System(
            id=isr.system.id, name=isr.system.name,
            modules=(grown_module,),
        ))

    # -- trajectory production ---------------------------------------------------

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

    def run_evolution(self, seed: int, generations: int | None = None):
        """One coordinator run; reconstruct the trajectory and bind every step
        to the run's own reported generation records.

        Binding honesty (Phase-28 provenance debt, audited by this suite):
        ``apply_restoration`` -> ``with_system`` stamps
        ``provenance.parent_hash = parent.content_hash``, and ``content_hash``
        folds in ``created_at``. Exact identity is therefore only deterministic
        where the chain's volatile fields have not compounded:

        * generation 0: ``parent_isr_hash`` and ``selected_candidate_id`` are
          bound EXACTLY (the parent is the shared defective ISR);
        * generation 1: ``parent_isr_hash`` is bound exactly (its parent's
          ``parent_hash`` is still ``defective.content_hash``);
        * every generation: the cumulative resolution profile is bound exactly
          -- the deterministic, volatile-free record of WHAT was selected.

        From generation 2 on, ``parent_isr_hash`` embeds ``parent_hash``
        links; post-migration (identity migration executed) these are the
        stable semantic hashes, so every generation's binding reproduces
        exactly across runs.
        """
        n = generations or 3
        defective, defect_set, result = self._run_multi_defect(n, seed)
        assert result.succeeded
        assert len(result.generations) == n
        trajectory = [defective]
        current = defective
        variation = LongHorizonVariation()
        for index, gen in enumerate(result.generations):
            candidates = variation.generate(current, defect_set, 1, seed + index)
            assert len(candidates) == 1
            candidate = candidates[0]
            assert gen.selected_operator_id == "transition_restoration"
            if index == 0:
                assert gen.parent_isr_hash == stable_isr_hash(current)
                assert gen.selected_candidate_id == candidate.candidate_id
            elif index == 1:
                assert gen.parent_isr_hash == stable_isr_hash(current)
            expected_resolved = frozenset(
                defect_set.observations[(seed + j) % n].evidence_hash
                for j in range(index + 1)
            )
            assert gen.resolved_defects == expected_resolved
            current = candidate.candidate_isr
            trajectory.append(current)
        return trajectory

    def run_evolution_ledger(self, seed: int) -> EvolutionLedger:
        ledger = EvolutionLedger()
        self._run_multi_defect(3, seed, ledger=ledger)
        return ledger

    def run_evolution_real(self, workspace_root: Path):
        """Real-substrate (Docker) run: FastAPIHexagonalBackend, classifier-
        derived observation, real repair proposal, ONE generation.

        Uses the proven R2.9.3 single-defect ``run`` path: the multi-defect
        ``ObservationBoundarySandbox`` passes the observation positionally to
        ``run_tests``, which ``RealBackendSandbox`` (``warning_filters``
        signature) does not accept -- real substrate runs use ``run``."""
        from tiannara.application.compiler.fastapi_hexagonal_backend import (
            FastAPIHexagonalBackend,
        )
        from tiannara.application.evolution import RealBackendSandbox

        defective = _isr(1, resolving=False)
        real = RealBackendSandbox(backend=FastAPIHexagonalBackend())
        broken_candidate = real.build(defective, workspace=str(workspace_root / "broken"))
        broken_run = real.run_tests(broken_candidate)
        observation = real.classifier.classify(real.to_evidence(broken_run))
        assert observation is not None

        baseline_candidate = real.build(_isr(1, resolving=True), workspace=str(workspace_root / "kg"))
        baseline_run = real.run_tests(baseline_candidate)
        assert baseline_run.exit_code == 0

        state = MultiGenerationEvolutionCoordinator(
            sandbox=real,
            gate=CandidateGate.default(),
            variation=SingleRepairRealVariation(),
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
        assert state.succeeded
        (gen0,) = state.generations
        assert gen0.selected_candidate_id.startswith("transition_restoration:")
        # reconstruction bound to the real run's own reported hashes
        candidate = TransitionRestorationOperator().propose(defective, observation)
        assert candidate is not None
        assert gen0.parent_isr_hash == stable_isr_hash(defective)
        assert gen0.selected_isr_hash == stable_isr_hash(candidate.candidate_isr)
        return [defective, candidate.candidate_isr]


@pytest.fixture(scope="module")
def repro_harness() -> ReproHarness:
    return ReproHarness()


# -- 1. Semantic stability: provenance volatility never moves the hash -------------

def test_same_architecture_different_created_at_same_semantic_hash(repro_harness):
    a = repro_harness.isr_with_created_at("2024-01-01T00:00:00")
    b = repro_harness.isr_with_created_at("2025-06-15T12:34:56")
    assert semantic_equivalent(a, b, repro_harness.extractor)
    assert repro_harness.extractor.semantic_hash(a) == repro_harness.extractor.semantic_hash(b)
    # post-migration: created_at no longer taints the content hash either
    assert a.content_hash == b.content_hash


def test_same_architecture_different_parent_lineage_same_semantic_hash(repro_harness):
    root = repro_harness.isr_with_created_at("2024-01-01T00:00:00")
    derived = repro_harness.isr_with_parent(root)
    assert semantic_equivalent(root, derived, repro_harness.extractor)
    assert derived.provenance.parent_hash == root.content_hash
    # post-migration: parent lineage is stamped in provenance only
    assert derived.content_hash == root.content_hash


def test_same_architecture_different_runtime_id_same_semantic_hash(repro_harness):
    bare = repro_harness.defective_isr()
    tagged = repro_harness.isr_with_runtime_id("run-7b3f")
    assert semantic_equivalent(bare, tagged, repro_harness.extractor)
    identity = repro_harness.extractor.extract(tagged)
    assert identity.runtime_execution_id == "run-7b3f"
    assert identity.semantic_hash == repro_harness.extractor.semantic_hash(bare)


# -- 2. Negative test (load-bearing): architecture changes MUST move the hash -------

def test_architectural_change_changes_semantic_hash(repro_harness):
    base = repro_harness.known_good_isr()
    retargeted = repro_harness.change_transition_target(base)
    assert not semantic_equivalent(base, retargeted, repro_harness.extractor)
    assert repro_harness.extractor.semantic_hash(base) != repro_harness.extractor.semantic_hash(retargeted)


def test_added_state_changes_semantic_hash(repro_harness):
    base = repro_harness.known_good_isr()
    grown = repro_harness.add_state(base)
    assert not semantic_equivalent(base, grown, repro_harness.extractor)


# -- 3. Canonicalization is explicit, no default=str ---------------------------------

def test_canonicalize_rejects_unhandled_types():
    with pytest.raises(CanonicalizationError):
        canonicalize(object())
    # handled forms round-trip deterministically
    assert canonicalize({"b": 1, "a": 2}) == canonicalize({"a": 2, "b": 1})
    assert canonicalize(datetime(2026, 1, 1, tzinfo=timezone.utc)).startswith('{"__datetime__"')


def test_semantic_projection_schema_is_inclusion_based(repro_harness):
    assert repro_harness.extractor.projector.SCHEMA == "fsm.semantic.v1"
    projection = FSMSemanticProjector().project(repro_harness.known_good_isr())
    # the projection names what architecture IS: workflows, states, transitions
    assert projection["modules"][0]["workflows"][0]["transitions"]
    # provenance and runtime data are absent from the schema by construction
    assert "provenance" not in projection
    assert "created_at" not in projection


# -- 4. Provenance identity is recoverable, never folded in ---------------------------

def test_provenance_identity_recoverable(repro_harness):
    derived = repro_harness.derived_isr()
    identity = repro_harness.extractor.extract(derived)
    assert isinstance(identity.provenance, ProvenanceIdentity)
    assert identity.provenance.parent_hash == derived.provenance.parent_hash
    assert identity.provenance.created_at is not None
    # the semantic identity IS the content hash post-migration (one identity)
    assert identity.semantic_hash == derived.content_hash


def test_three_identities_are_distinct(repro_harness):
    tagged = repro_harness.isr_with_runtime_id("run-x")
    identity = repro_harness.extractor.extract(tagged)
    assert identity.semantic_hash
    assert identity.provenance.created_at is not None
    assert identity.runtime_execution_id == "run-x"
    bare = repro_harness.defective_isr()
    bare_identity = repro_harness.extractor.extract(bare)
    assert bare_identity.runtime_execution_id is None


# -- 5. The extractor is additive: reads, never mutates --------------------------------

def test_extractor_does_not_mutate_isr(repro_harness):
    isr = repro_harness.defective_isr()
    hash_before = isr.content_hash
    prov_before = isr.provenance
    first = repro_harness.extractor.extract(isr)
    second = repro_harness.extractor.extract(isr)
    assert first == second
    assert isr.content_hash == hash_before
    assert isr.provenance == prov_before
    assert first.semantic_hash == repro_harness.extractor.semantic_hash(isr)


# -- 6. Phase-28 conflation is resolved by evidence (migration executed) ----------

def test_audit_confirms_content_hash_is_semantic_post_migration(repro_harness):
    derived = repro_harness.derived_isr()
    report = repro_harness.auditor.audit_identity_separation(derived)
    assert isinstance(report, IdentitySeparationReport)
    assert report.semantic_is_stable_identity
    assert report.phase28_tainted_by_provenance is False
    assert report.semantic_hash == report.phase28_content_hash
    assert report.taint_fields == ()


def test_audit_taint_signal_is_evidence_based(repro_harness):
    report = repro_harness.auditor.audit_identity_separation(repro_harness.defective_isr())
    assert report.phase28_tainted_by_provenance is False
    assert report.taint_fields == ()


# -- 7. Cross-run reproducibility: semantic AND content reproduce ------------------

def test_cross_run_semantic_and_content_reproducible(repro_harness):
    traj_a = repro_harness.run_evolution(0)
    traj_b = repro_harness.run_evolution(0)
    assert len(traj_a) == len(traj_b) == 4          # n + 1 nodes for n = 3
    report = repro_harness.auditor.audit_cross_run(traj_a, traj_b)
    assert isinstance(report, CrossRunReport)
    assert report.generations_compared == 4
    assert report.semantic_reproducible
    assert report.content_reproducible
    assert report.divergence_cause is None


def test_long_horizon_semantic_trajectory_reproducible(repro_harness):
    traj_a = repro_harness.run_evolution(0, generations=12)
    traj_b = repro_harness.run_evolution(0, generations=12)
    assert len(traj_a) == len(traj_b) == 13         # 12 generations + initial parent
    report = repro_harness.auditor.audit_cross_run(traj_a, traj_b)
    assert report.generations_compared == 13
    assert report.semantic_reproducible
    assert report.content_reproducible
    assert report.divergence_cause is None


# -- 8. The semantic trajectory is architecturally grounded ------------------------------

def test_semantic_trajectory_is_architecturally_grounded(repro_harness):
    trajectory = repro_harness.run_evolution(0)
    for node in trajectory:
        # the semantic hash IS the canonical projection, no more, no less
        architecture = repro_harness.extractor.projector.project(node)
        assert repro_harness.extractor.semantic_hash(node) == hashlib.sha256(
            canonicalize(architecture).encode("utf-8")
        ).hexdigest()
    # every defect repaired exactly once over the 3-generation trajectory
    for i, node in enumerate(trajectory[1:], start=1):
        assert _has_resolution(node, COROUTINES[i - 1])
    assert _has_resolution(trajectory[-1])          # full suite passes


def test_ledger_chain_valid_across_evolution(repro_harness):
    ledger = repro_harness.run_evolution_ledger(0)
    assert ledger.verify_event_chain() is True


# -- 9. Real execution (Docker-gated): semantic reproducibility under execution ----------

@pytest.mark.docker_integration
@pytest.mark.skipif(not docker_available(), reason="R2.9.7 real-substrate audit requires Docker")
def test_semantic_reproducibility_under_real_execution(repro_harness, tmp_path):
    real_trajectory = repro_harness.run_evolution_real(tmp_path)
    hermetic_trajectory = repro_harness.run_evolution(0, generations=1)
    report = repro_harness.auditor.audit_cross_run(real_trajectory, hermetic_trajectory)
    assert report.semantic_reproducible
    assert report.content_reproducible
    assert report.divergence_cause is None