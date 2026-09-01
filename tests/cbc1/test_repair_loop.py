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


