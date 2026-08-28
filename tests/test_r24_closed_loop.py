"""R2.4.0b Step 2 -- closed-loop acceptance: the Evolution Engine repairs reality.

Proves the end-to-end causal chain against REAL generated code + REAL pytest in
``python:3.12-slim``:

    known-good ISR -> [drop edge] -> broken ISR -> REAL compile -> broken artifact
      -> real pytest -W error::RuntimeWarning -> real RuntimeWarning (A1)
      -> TransitionRestoration.try_repair -> repaired ISR (A4)
      -> REAL recompile -> repaired artifact -> real pytest -> PASS (A2)
      -> known-good re-run, pass-count equality (A3)
      -> hash invariants: broken tree untouched (5a), fresh recompile matches (5b),
         repaired differs (5c) (no source-patch bypass)
      -> EvolutionRecord with the full hash chain -> causal ledger verifies

Skipped when Docker is absent (use test_r24_async_resolution_codegen.py for
Docker-free coverage of the codegen + operator primitives).
"""
from __future__ import annotations

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
    BrokenTreeIntactInvariant,
    CandidateGate,
    CandidateVerdict,
    EvolutionLedger,
    EvolutionRecord,
    GateContext,
    RealBackendSandbox,
    TransitionRestoration,
    docker_available,
    hash_artifact,
    hash_run,
    stable_isr_hash,
)
from tiannara.application.evolution.mutation_operators import (
    ISRDelta,
    MutationCandidate,
)
from tiannara.application.compiler.fastapi_hexagonal_backend import FastAPIHexagonalBackend

pytestmark = [
    pytest.mark.skipif(
        not docker_available(), reason="R2.4.0b closed-loop gate requires Docker"
    ),
    pytest.mark.docker_integration,
]

COROUTINE = "process_payment"


# -- ISR fixtures (seed defect = dropped resolution edge) -------------------


def _workflow(resolving: bool) -> Workflow:
    awaited = WorkflowState(
        id="order-await", name="awaiting",
        state_type=StateType.INTERMEDIATE, metadata={"awaits": COROUTINE},
    )
    final = WorkflowState(id="order-final", name="final", state_type=StateType.FINAL)
    transitions = ()
    if resolving:
        transitions = (
            WorkflowTransition(
                id="resolve-payment", name="resolve payment",
                from_state_id=awaited.id, to_state_id=final.id, trigger=COROUTINE,
            ),
        )
    return Workflow(id="order", name="order", states=(awaited, final), transitions=transitions)


def _isr(resolving: bool) -> ISR:
    return ISR(system=System(
        id="sys", name="OrderSystem",
        modules=(Module(id="m", name="M", workflows=(_workflow(resolving),)),),
    ))


def _drop_resolution_edge(isr: ISR) -> ISR:
    """Seed defect: strip the resolving transition (no operator, no speculation)."""
    module = isr.system.modules[0]
    wf = module.workflows[0]
    broken_wf = Workflow(
        id=wf.id, name=wf.name, description=wf.description,
        states=wf.states, transitions=(), metadata=wf.metadata,
    )
    broken_module = Module(
        id=module.id, name=module.name, description=module.description,
        entities=module.entities, services=module.services, workflows=(broken_wf,),
        policies=module.policies, interfaces=module.interfaces, events=module.events,
        dependencies=module.dependencies, metadata=module.metadata,
    )
    return isr.with_system(System(
        id=isr.system.id, name=isr.system.name, description=isr.system.description,
        modules=(broken_module,), deployment=isr.system.deployment,
        metadata=isr.system.metadata, global_policies=isr.system.global_policies,
        constraints=isr.system.constraints,
    ))


# -- the gate ----------------------------------------------------------------


def test_r24_closed_loop_real_codegen_repair(tmp_path):
    known_good_isr = _isr(resolving=True)
    broken_isr = _drop_resolution_edge(known_good_isr)

    sandbox = RealBackendSandbox(backend=FastAPIHexagonalBackend())
    classifier = sandbox.classifier
    operator = TransitionRestoration()

    # --- REAL compile of the broken ISR -----------------------------------
    broken_candidate = sandbox.build(broken_isr, workspace=str(tmp_path / "broken"))
    broken_hash_before = broken_candidate.artifact_hash
    # A5a: broken artifact is content-addressable and must not move during repair.
    assert broken_candidate.artifact_hash == hash_artifact(broken_candidate.source_root)

    # --- REAL pytest -W error::RuntimeWarning on the broken artifact (A1) ---
    broken_run = sandbox.run_tests(broken_candidate)
    observation = classifier.classify(sandbox.to_evidence(broken_run))
    assert observation is not None, f"expected a failure, got clean run: {broken_run}"
    assert "was never awaited" in observation.stderr_excerpt
    coroutine_name = operator.extract_coroutine_name(observation)
    assert coroutine_name == COROUTINE

    # --- R2.5: drive the candidate through the validation frontier -------------
    # Preconditions (not gates): well-formed ISR mutation.
    repaired = operator.try_repair(broken_isr, coroutine_name)
    assert repaired is not None
    assert isinstance(repaired.repaired_isr, ISR)
    # mutation semantics: new version, provenance anchored to broken ISR.
    assert repaired.repaired_isr.version == broken_isr.version + 1
    # (ISR-28-HASH-001 deferred: provenance.parent_hash is content_hash; stable
    #  linkage is used for ledger broken_hash/repaired_hash below.)
    assert repaired.repaired_isr.provenance.parent_hash == broken_isr.content_hash
    assert len(repaired.repaired_diff) == 1

    # R2.6 candidate contract (MutationCandidate) for the gate:
    mutation = MutationCandidate(
        candidate_id=f"transition_restoration:{stable_isr_hash(repaired.repaired_isr)[:12]}",
        operator_id="transition_restoration",
        candidate_isr=repaired.repaired_isr,
        parent_isr=broken_isr,
        mutation_delta=ISRDelta(tuple(repaired.repaired_diff)),
        hypothesis=repaired.hypothesis,
    )

    # --- REAL recompile of the repaired ISR (A2 preconditions + A5b foothold) --
    # An independent, fresh recompilation of the SAME repaired ISR -- byte-identical
    # to the primary artifact proves the repair changed ISR semantics, not source.
    independent_recompile_hash = hash_artifact(
        sandbox.build(repaired.repaired_isr,
                      workspace=str(tmp_path / "repaired2")).source_root
    )
    repaired_candidate = sandbox.build(
        repaired.repaired_isr, workspace=str(tmp_path / "repaired"))
    assert repaired_candidate.artifact_hash == independent_recompile_hash

    repaired_run = sandbox.run_tests(repaired_candidate)

    # --- regression baseline (known-good) for the regression gate -------------
    known_good_candidate = sandbox.build(known_good_isr, workspace=str(tmp_path / "kg"))
    known_good_run = sandbox.run_tests(known_good_candidate)
    assert known_good_run.exit_code == 0

    # The R2.4.0b acceptance assertions (A2 target resolved, A3 no regression,
    # A4 closure, A5a broken-tree intact, A5b/5c fresh-recompile & changed-source)
    # are now expressed as one gate each; CandidateGate only inspects already-
    # produced artifacts/runs/evidence, keeping the compiler pure.
    gate = CandidateGate.default()
    ctx = GateContext(
        candidate_isr=mutation.candidate_isr,
        candidate_artifact=repaired_candidate,
        candidate_run=repaired_run,
        baseline_artifact=known_good_candidate,
        baseline_run=known_good_run,
        observation=observation,
        mutation=mutation,
        parent_isr=mutation.parent_isr,
        protected_invariants=(BrokenTreeIntactInvariant(broken_hash_before),),
        broken_artifact=broken_candidate,
        broken_artifact_hash=hash_artifact(broken_candidate.source_root),
        independent_recompile_hash=independent_recompile_hash,
    )
    verdict: CandidateVerdict = gate.evaluate(ctx)
    failed = [r for r in verdict.gate_results if not r.passed]
    assert verdict.accept, f"candidate rejected by frontier: {failed}"
    # every gate must independently pass (the frontier is a conjunction):
    assert all(r.passed for r in verdict.gate_results)

    # --- causal ledger (full chain) ---------------------------------------
    ledger = EvolutionLedger()
    record = ledger.append(EvolutionRecord(
        observation_hash=observation.evidence_hash,
        broken_hash=stable_isr_hash(broken_isr),
        operator="transition_restoration",
        hypothesis=repaired.hypothesis,
        repaired_hash=stable_isr_hash(repaired.repaired_isr),
        repaired_diff=repaired.repaired_diff,
        repaired_artifact_hash=hash_artifact(repaired_candidate.source_root),
        runtime_evidence_hash=hash_run(repaired_run),
        validation=(("build", "pass"), ("test", "pass")),
        fitness_delta=1.0,
        decision="accept",
    ))
    assert ledger.verify_chain()

    chain = ledger.get(record)
    assert chain is not None
    assert (chain.observation_hash, chain.broken_hash, chain.repaired_hash,
            chain.repaired_artifact_hash, chain.runtime_evidence_hash) == (
        observation.evidence_hash,
        stable_isr_hash(broken_isr),
        stable_isr_hash(repaired.repaired_isr),
        hash_artifact(repaired_candidate.source_root),
        hash_run(repaired_run),
    )
    # links distinct where causally required:
    assert chain.observation_hash != chain.broken_hash
    assert chain.broken_hash != chain.repaired_hash
    assert chain.repaired_hash != chain.repaired_artifact_hash
