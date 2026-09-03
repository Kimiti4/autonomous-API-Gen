"""CBC-1 Governed Repair — causal classification, learning, and backend-variant
evolution (no ISR mutation, no generated-code repair, no fabrication).
"""
from __future__ import annotations

import pytest

from certification.campaign.plan_builder import build_artifacts_for
from certification.corpus.corpus import default_corpus
from certification.feedback.rule import (
    classify_failure,
    analyze_failure,
    FailureClassification,
    DOMAIN_INFRASTRUCTURE,
    DOMAIN_LOWERING,
    DOMAIN_GENOME,
)
from certification.feedback.candidate import EvolutionCandidate
from certification.feedback.policy import BackendSwapPolicy, make_candidate
from certification.feedback.repair import GovernedRepair

from learning.engine import ContinuousLearningEngine
from learning.models import LearningSignalType


# ---------------------------------------------------------------------------
# D1 — causal classification (stage != cause)
# ---------------------------------------------------------------------------

def test_classify_failure_legacy_string_contract():
    # Keep the existing stage→domain string contract intact.
    assert classify_failure("build") == "lowering"
    assert classify_failure("test") == "genome"
    assert classify_failure("deploy") == "infrastructure"
    assert classify_failure("runtime") == "architecture"
    assert classify_failure("unknown_stage") == "genome"


def test_build_registry_failure_is_infrastructure_not_lowering():
    # A build failing from registry/network is INFRASTRUCTURE, not lowering.
    cls = analyze_failure(
        stage="build",
        failure_class="infrastructure",
        detail="failed to solve: rust:1.78-slim: registry",
    )
    assert isinstance(cls, FailureClassification)
    assert cls.stage == "build"           # observed stage
    assert cls.cause == "infrastructure"  # causal class != stage
    assert cls.feedback_domain == DOMAIN_INFRASTRUCTURE
    assert cls.repair_eligible is False


def test_build_compiler_failure_is_lowering_eligible():
    # A genuine toolchain/Dockerfile defect (compiler cause) is lowering domain
    # and repair-eligible (policy-dependent).
    cls = analyze_failure(stage="build", failure_class="compiler", detail="")
    assert cls.cause == "compiler"
    assert cls.feedback_domain == DOMAIN_LOWERING
    assert cls.repair_eligible is True


def test_behavioral_product_failure_is_genome_eligible():
    cls = analyze_failure(stage="runtime", failure_class="product", detail="")
    assert cls.cause == "product"
    assert cls.feedback_domain == DOMAIN_GENOME
    assert cls.repair_eligible is True


def test_port_exhaustion_cause_mark_detected():
    cls = analyze_failure(
        stage="deploy",
        failure_class="infrastructure",
        detail="driver failed programming external connectivity: "
               "Bind for 0.0.0.0:8000 failed: port is already allocated",
    )
    assert cls.cause == "infrastructure"
    assert cls.feedback_domain == DOMAIN_INFRASTRUCTURE
    assert cls.repair_eligible is False


# ---------------------------------------------------------------------------
# D2 — learning consumption
# ---------------------------------------------------------------------------

def test_learning_signal_reaches_continuous_learning_engine():
    engine = ContinuousLearningEngine()
    r = GovernedRepair(learning_engine=engine)

    f = r.evaluate_failure(
        trial_id="t1",
        intent=default_corpus()[0].intent,
        backend="rust-axum",
        stage="build",
        failure_class="infrastructure",
        detail="failed to solve: rust:1.78-slim",
        isr_hash="h",
        genome_hash="g",
        eligible_backend_ids=["python-fastapi", "rust-axum"],
    )
    assert f.signal is not None
    assert f.signal.signal_type == LearningSignalType.INCIDENT
    assert f.signal.labels["cause"] == "infrastructure"
    assert f.signal.evidence_refs == ["t1"]
    assert engine.report()["signal_count"] == 1


def test_learning_signal_preserves_full_context():
    r = GovernedRepair()
    f = r.evaluate_failure(
        trial_id="tid",
        intent="customer relationship SaaS",
        backend="rust-axum",
        stage="build",
        failure_class="infrastructure",
        detail="no such host",
        isr_hash="i-hash",
        genome_hash="g-hash",
        eligible_backend_ids=["python-fastapi"],
    )
    labels = f.signal.labels
    assert labels["trial_id"] == "tid"
    assert labels["intent_id"] == "customer relationship SaaS"
    assert labels["backend"] == "rust-axum"
    assert labels["stage"] == "build"
    assert labels["feedback_domain"] == "infrastructure"
    assert labels["repair_eligible"] == "False"


# ---------------------------------------------------------------------------
# D4 — governed backend-swap policy
# ---------------------------------------------------------------------------

def test_infrastructure_failure_never_evolves():
    policy = BackendSwapPolicy()
    cls = analyze_failure(stage="build", failure_class="infrastructure", detail="")
    d = policy.should_evolve(
        classification=cls,
        failed_backend_id="rust-axum",
        eligible_backend_ids=["python-fastapi", "rust-axum"],
    )
    assert d.accepted is False
    assert "LEARN-ONLY" in d.reason or "not repair-eligible" in d.reason


def test_eligible_behavioral_failure_evolves_to_alternate():
    policy = BackendSwapPolicy()
    cls = analyze_failure(stage="runtime", failure_class="product", detail="")
    d = policy.should_evolve(
        classification=cls,
        failed_backend_id="rust-axum",
        eligible_backend_ids=["python-fastapi", "rust-axum"],
    )
    assert d.accepted is True
    assert d.alternate_backend_id == "python-fastapi"
    assert d.alternate_backend_id != "rust-axum"


def test_alternate_backend_must_be_eligible_and_differ():
    policy = BackendSwapPolicy()
    cls = analyze_failure(stage="runtime", failure_class="product", detail="")
    # Only the failed backend is eligible → no alternate.
    d = policy.should_evolve(
        classification=cls,
        failed_backend_id="rust-axum",
        eligible_backend_ids=["rust-axum"],
    )
    assert d.accepted is False


def test_already_attempted_backend_not_duplicated():
    policy = BackendSwapPolicy()
    cls = analyze_failure(stage="runtime", failure_class="product", detail="")
    # python-fastapi already attempted for this parent → no alternate left.
    d = policy.should_evolve(
        classification=cls,
        failed_backend_id="rust-axum",
        eligible_backend_ids=["python-fastapi", "rust-axum"],
        attempted_backend_ids={"python-fastapi"},
    )
    assert d.accepted is False


def test_workload_compatibility_filters_alternate():
    policy = BackendSwapPolicy()
    cls = analyze_failure(stage="runtime", failure_class="product", detail="")
    # python-fastapi does NOT support this workload.
    d = policy.should_evolve(
        classification=cls,
        failed_backend_id="rust-axum",
        eligible_backend_ids=["python-fastapi", "rust-axum"],
        supports_workload={"rust-axum"},
    )
    assert d.accepted is False


def test_startup_polling_does_not_evolve():
    # Startup readiness waits are infrastructure-neutral — never repair.
    policy = BackendSwapPolicy()
    cls = analyze_failure(stage="runtime", failure_class="", detail="")
    d = policy.should_evolve(
        classification=cls,
        failed_backend_id="python-fastapi",
        eligible_backend_ids=["python-fastapi"],
    )
    # No causal signal → repair_eligible False → not accepted.
    assert d.accepted is False


def test_make_candidate_requires_accepted_decision():
    policy = BackendSwapPolicy()
    cls = analyze_failure(stage="runtime", failure_class="product", detail="")
    bad = policy.should_evolve(
        classification=cls,
        failed_backend_id="rust-axum",
        eligible_backend_ids=["rust-axum"],
    )
    assert make_candidate(
        decision=bad, parent_trial_id="p", intent_id="i",
        isr_hash="h", genome_hash="g",
    ) is None

    good = policy.should_evolve(
        classification=cls,
        failed_backend_id="rust-axum",
        eligible_backend_ids=["python-fastapi", "rust-axum"],
    )
    cand = make_candidate(
        decision=good, parent_trial_id="p", intent_id="i",
        isr_hash="h", genome_hash="g",
    )
    assert isinstance(cand, EvolutionCandidate)
    assert cand.parent_trial_id == "p"
    assert cand.backend_id == "python-fastapi"
    assert cand.origin == "evolved"
    assert cand.variant_kind == "backend_swap"


# ---------------------------------------------------------------------------
# D3 — candidate lineage / ISR immutability
# ---------------------------------------------------------------------------

def test_candidate_retains_isr_hash():
    base = build_artifacts_for(default_corpus()[0])
    policy = BackendSwapPolicy()
    cls = analyze_failure(stage="runtime", failure_class="product", detail="")
    d = policy.should_evolve(
        classification=cls,
        failed_backend_id="rust-axum",
        eligible_backend_ids=["python-fastapi", "rust-axum"],
    )
    cand = make_candidate(
        decision=d, parent_trial_id="p", intent_id=default_corpus()[0].intent,
        isr_hash=base.revision.content_hash, genome_hash=base.genome_hash,
    )
    # Backend evolution must NOT change the constitutional identity.
    assert cand.isr_hash == base.revision.content_hash
    assert cand.genome_hash == base.genome_hash


# ---------------------------------------------------------------------------
# Full orchestration — evaluate_failure ties everything together
# ---------------------------------------------------------------------------

def test_evaluate_failure_infra_learns_but_does_not_evolve():
    engine = ContinuousLearningEngine()
    r = GovernedRepair(learning_engine=engine)
    f = r.evaluate_failure(
        trial_id="t1", intent="project management SaaS", backend="rust-axum",
        stage="build", failure_class="infrastructure",
        detail="failed to solve: rust:1.78-slim",
        isr_hash="i", genome_hash="g",
        eligible_backend_ids=["python-fastapi", "rust-axum"],
    )
    assert f.decision.accepted is False
    assert f.candidate is None          # no candidate
    assert engine.report()["signal_count"] == 1  # but it learned


def test_evaluate_failure_behavioral_evolves_and_learns():
    engine = ContinuousLearningEngine()
    r = GovernedRepair(learning_engine=engine)
    f = r.evaluate_failure(
        trial_id="t1", intent="project management SaaS", backend="rust-axum",
        stage="runtime", failure_class="product",
        detail="assertion failed in /health",
        isr_hash="i", genome_hash="g",
        eligible_backend_ids=["python-fastapi", "rust-axum"],
    )
    assert f.decision.accepted is True
    assert f.candidate is not None
    assert f.candidate.backend_id == "python-fastapi"
    assert f.candidate.parent_trial_id == "t1"
    assert engine.report()["signal_count"] == 1


# ---------------------------------------------------------------------------
# D6 — anti-vacuity: backend swap must be a REAL compilation variant
# ---------------------------------------------------------------------------

def test_artifact_novelty_real_backends_are_distinct():
    from compiler.composition import build_backend_registry
    from compiler.core.protocol import eligible_for_behavioral_certification

    base = build_artifacts_for(default_corpus()[0])
    reg = build_backend_registry()
    be = [reg.get(n) for n in reg.list_names()
          if reg.get(n) and eligible_for_behavioral_certification(reg.get(n).identity())]
    byid = {b.identity().name: b for b in be}

    py = byid["python-fastapi"]
    rust = byid["rust-axum"]
    py_repo = py.compile(base.plan)
    rust_repo = rust.compile(base.plan)
    # The two behavioral backends must emit DIFFERENT artifacts — otherwise a
    # "backend swap" would be a metadata-only no-op and must be rejected.
    assert py_repo.content_hash != rust_repo.content_hash


def test_prepare_evolved_trial_rejects_noop_evolution():
    from certification.feedback.execution import (
        prepare_evolved_trial,
        BackendArtifactCheck,
        NO_OP_EVOLUTION,
    )
    from certification.feedback.candidate import EvolutionCandidate
    from compiler.composition import build_backend_registry
    from compiler.core.protocol import eligible_for_behavioral_certification

    base = build_artifacts_for(default_corpus()[0])
    reg = build_backend_registry()
    be = [reg.get(n) for n in reg.list_names()
          if reg.get(n) and eligible_for_behavioral_certification(reg.get(n).identity())]
    byid = {b.identity().name: b for b in be}

    cand = EvolutionCandidate(
        parent_trial_id="parent1",
        intent_id=default_corpus()[0].intent,
        isr_hash=base.revision.content_hash,
        genome_hash=base.genome_hash,
        backend_id="python-fastapi",
    )
    check, alternate = prepare_evolved_trial(
        candidate=cand,
        runner=None,
        base_artifacts=base,
        backend_map=byid,
        failed_backend_id="rust-axum",
    )
    assert isinstance(check, BackendArtifactCheck)
    assert check.distinct is True          # real novelty
    assert check.reason != NO_OP_EVOLUTION
    assert alternate is not None


def test_prepare_evolved_trial_rejects_missing_backend():
    from certification.feedback.execution import prepare_evolved_trial
    from certification.feedback.candidate import EvolutionCandidate

    base = build_artifacts_for(default_corpus()[0])
    cand = EvolutionCandidate(
        parent_trial_id="p", intent_id="i",
        isr_hash="h", genome_hash="g", backend_id="does-not-exist",
    )
    check, alternate = prepare_evolved_trial(
        candidate=cand, runner=None, base_artifacts=base,
        backend_map={}, failed_backend_id="rust-axum",
    )
    assert check.distinct is False
    assert alternate is None


# ---------------------------------------------------------------------------
# Trial model — evolved lineage fields
# ---------------------------------------------------------------------------

def test_trial_model_defaults_to_reference_origin():
    from certification.core.trial import Trial
    from certification.core.trial import TrialMetrics

    t = Trial(
        trial_id="t", intent="i", category="c", novelty_class="template",
        requirement_graph_hash="r", genome_hash="g", isr_revision_id="rev",
        backend="python-fastapi", compiler_version="1.4.0", repo_hash="repo",
        metrics=TrialMetrics(),
    )
    # Reference (congenital) trials default to origin=reference, no parent.
    assert t.origin == "reference"
    assert t.parent_trial_id == ""


# ---------------------------------------------------------------------------
# D3 expanded contract — parent_backend_id, provenance, created_at
# ---------------------------------------------------------------------------

def test_candidate_contract_full_lineage():
    from certification.feedback.policy import BackendSwapPolicy, make_candidate
    base = build_artifacts_for(default_corpus()[0])
    cls = analyze_failure(stage="runtime", failure_class="product", detail="")
    d = BackendSwapPolicy().should_evolve(
        classification=cls,
        failed_backend_id="rust-axum",
        eligible_backend_ids=["python-fastapi", "rust-axum"],
    )
    cand = make_candidate(
        decision=d, parent_trial_id="p1", intent_id=default_corpus()[0].intent,
        isr_hash=base.revision.content_hash, genome_hash=base.genome_hash,
        parent_candidate_id="c0", parent_backend_id="rust-axum",
    )
    lin = cand.lineage()
    assert lin["parent_backend_id"] == "rust-axum"
    assert lin["parent_candidate_id"] == "c0"
    assert lin["provenance"] == "campaign_b.governed_repair"
    assert "created_at" in lin and lin["created_at"]
    # ISR immutability at materialization time.
    assert cand.isr_hash == base.revision.content_hash
    assert cand.genome_hash == base.genome_hash


# ---------------------------------------------------------------------------
# D5 — BackendSwapStrategy operator
# ---------------------------------------------------------------------------

def test_backend_swap_strategy_proposes_on_behavioral_failure():
    from certification.feedback.policy import BackendSwapStrategy
    from certification.feedback.candidate import EvolutionCandidate
    strategy = BackendSwapStrategy()
    cls = analyze_failure(stage="runtime", failure_class="product", detail="")
    decision, cand = strategy.propose(
        classification=cls,
        parent_trial_id="p1", intent_id="i",
        isr_hash="ISR", genome_hash="G",
        failed_backend_id="rust-axum",
        eligible_backend_ids=["python-fastapi", "rust-axum"],
    )
    assert decision.accepted is True
    assert isinstance(cand, EvolutionCandidate)
    assert cand.backend_id == "python-fastapi"
    assert cand.parent_backend_id == "rust-axum"


def test_backend_swap_strategy_rejects_infrastructure():
    from certification.feedback.policy import BackendSwapStrategy
    strategy = BackendSwapStrategy()
    cls = analyze_failure(
        stage="build", failure_class="infrastructure",
        detail="failed to solve: rust:1.78-slim",
    )
    decision, cand = strategy.propose(
        classification=cls,
        parent_trial_id="p1", intent_id="i",
        isr_hash="ISR", genome_hash="G",
        failed_backend_id="rust-axum",
        eligible_backend_ids=["python-fastapi", "rust-axum"],
    )
    assert decision.accepted is False
    assert cand is None


# ---------------------------------------------------------------------------
# D7 — artifact-novelty baseline contract (deterministic reality check)
# ---------------------------------------------------------------------------

def test_d7_baseline_artifact_contract():
    """Baseline: python-fastapi and rust-axum compile the same workload into
    two DIFFERENT repositories — the anti-vacuity floor for backend evolution."""
    from compiler.composition import build_backend_registry
    from compiler.core.protocol import eligible_for_behavioral_certification

    base = build_artifacts_for(default_corpus()[0])
    reg = build_backend_registry()
    be = [reg.get(n) for n in reg.list_names()
          if reg.get(n) and eligible_for_behavioral_certification(reg.get(n).identity())]
    byid = {b.identity().name: b for b in be}

    py = byid["python-fastapi"].compile(base.plan)
    rust = byid["rust-axum"].compile(base.plan)

    py_no = {p for p in py.files if p.endswith((".py", "requirements.txt", "Dockerfile"))}
    # Both emit a heterogeneous artifact set for the same ISR.
    assert py.content_hash != rust.content_hash
    assert py.files != rust.files
    # The two backends both target real behavioral certification (D7 floor).
    assert len(py.files) > 0 and len(rust.files) > 0
    assert py_no  # python backend emits python runtime files


# ---------------------------------------------------------------------------
# Mirror-gate: the canonical gate set (D9) passes inside the unit suite
# ---------------------------------------------------------------------------

def test_release_self_repair_gates_all_pass():
    import os
    import sys

    gates_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "release", "gates", "cbc1",
    )
    if gates_dir not in sys.path:
        sys.path.insert(0, gates_dir)
    import check_self_repair_gates as gates

    results = gates.run_all()
    assert len(results) == len(gates.GATE_NAMES)
    failed = {n: r for n, r in results.items() if not r[0]}
    assert not failed, f"gates failed: {failed}"


# ---------------------------------------------------------------------------
# CANONICAL CONTROLLED INTEGRATION SCENARIO
#   T1 (rust) FAILED behaviorally  -> learn -> candidate -> T2 (python) CERTIFIED
#   Parent immutable, ISR preserved, independent identity, NO infra flakiness.
# ---------------------------------------------------------------------------

def test_controlled_integration_t1_failed_to_t2_certified():
    from certification.feedback.repair import GovernedRepair
    from certification.feedback.execution import prepare_evolved_trial, run_evolved_trial
    from certification.core.trial import Trial, TrialMetrics, TrialStage, StageEvidence
    from learning.engine import ContinuousLearningEngine
    from compiler.composition import build_backend_registry
    from compiler.core.protocol import eligible_for_behavioral_certification

    workload = default_corpus()[0]
    artifacts = build_artifacts_for(workload)
    reg = build_backend_registry()
    be = [reg.get(n) for n in reg.list_names()
          if reg.get(n) and eligible_for_behavioral_certification(reg.get(n).identity())]
    byid = {b.identity().name: b for b in be}

    engine = ContinuousLearningEngine()
    repair = GovernedRepair(learning_engine=engine)

    def _notes(stage):
        return StageEvidence(
            stage=stage, passed=False, started_at="t", completed_at="t",
            logs_hash="h", detail="GET /items empty while /live 200",
            mode="REAL_DOCKER", failure_class="product",
        )

    t1 = Trial(
        trial_id="T1", intent=workload.intent, category=workload.category.value,
        novelty_class="template",
        requirement_graph_hash=artifacts.revision.content_hash,
        genome_hash=artifacts.genome_hash, isr_revision_id="rev",
        backend="rust-axum", compiler_version="1.4.0",
        repo_hash=byid["rust-axum"].compile(artifacts.plan).content_hash,
        metrics=TrialMetrics(), verdict="NOT_CERTIFIED",
        stages=[
            StageEvidence(stage=TrialStage.STRUCTURAL, passed=True, started_at="t",
                          completed_at="t", logs_hash="h", mode="REAL_DOCKER"),
            StageEvidence(stage=TrialStage.SEMANTIC, passed=True, started_at="t",
                          completed_at="t", logs_hash="h", mode="REAL_DOCKER"),
            StageEvidence(stage=TrialStage.BUILD, passed=True, started_at="t",
                          completed_at="t", logs_hash="h", mode="REAL_DOCKER"),
            StageEvidence(stage=TrialStage.TEST, passed=True, started_at="t",
                          completed_at="t", logs_hash="h", mode="REAL_DOCKER"),
            StageEvidence(stage=TrialStage.DEPLOY, passed=True, started_at="t",
                          completed_at="t", logs_hash="h", mode="REAL_DOCKER"),
            _notes(TrialStage.RUNTIME),
        ],
    )
    import json
    parent_snapshot = json.dumps(t1.model_dump(), sort_keys=True)

    # Controlled behavioral failure: classify, learn, decide — no infra noise.
    feedback = repair.evaluate_failure(
        trial_id=t1.trial_id, intent=workload.intent, backend=t1.backend,
        stage="runtime", failure_class="product",
        detail="GET /items returned empty list while /live was 200",
        isr_hash=t1.requirement_graph_hash, genome_hash=t1.genome_hash,
        eligible_backend_ids=list(byid.keys()),
    )
    assert feedback.classification.repair_eligible is True
    assert feedback.classification.cause == "product"
    assert engine.report()["signal_count"] == 1  # D2: signal consumed
    assert feedback.decision.accepted is True
    candidate = feedback.candidate
    assert candidate is not None
    assert candidate.backend_id == "python-fastapi"
    assert candidate.parent_backend_id == "rust-axum"
    assert candidate.isr_hash == t1.requirement_graph_hash
    assert candidate.genome_hash == t1.genome_hash

    # Anti-vacuity: distinct artifact for the SAME workload.
    novelty, alternate = prepare_evolved_trial(
        candidate=candidate, runner=None, base_artifacts=artifacts,
        backend_map=byid, failed_backend_id=t1.backend,
    )
    assert novelty.distinct is True

    # Independent execution through the NORMAL pipeline as a NEW trial.
    class _Probe:
        def __init__(self, backend):
            self.backend = backend

        def run_trial(self, **kwargs):
            assert kwargs.get("origin") == "evolved"
            assert kwargs.get("parent_trial_id") == "T1"
            t = byid[self.backend.identity().name].compile(kwargs["plan"])
            return Trial(
                trial_id="T2", intent=kwargs["intent"],
                category=kwargs["category"], novelty_class="template",
                requirement_graph_hash=t1.requirement_graph_hash,
                genome_hash=t1.genome_hash, isr_revision_id="rev",
                backend=self.backend.identity().name, compiler_version="1.4.0",
                repo_hash=t.content_hash, metrics=TrialMetrics(),
                verdict="CERTIFIED", origin="evolved",
                parent_trial_id="T1",
            )

    probe = _Probe(alternate)
    t2 = run_evolved_trial(
        runner=probe, candidate=candidate, base_artifacts=artifacts,
        alternate=alternate, workload=workload,
    )

    # Independent certification + lineage.
    assert t2.trial_id != t1.trial_id
    assert t2.origin == "evolved"
    assert t2.parent_trial_id == "T1"
    assert t2.backend != t1.backend
    assert t2.requirement_graph_hash == t1.requirement_graph_hash
    assert t2.genome_hash == t1.genome_hash
    assert t2.verdict == "CERTIFIED"

    # PARENT IMMUTABILITY: evaluate_failure/execution never rewrote T1.
    assert json.dumps(t1.model_dump(), sort_keys=True) == parent_snapshot
    assert t1.verdict == "NOT_CERTIFIED"
    # NO DIRECT REPAIR: the parent's compiled artifact is untouched.
    assert byid["rust-axum"].compile(artifacts.plan).content_hash == t1.repo_hash


