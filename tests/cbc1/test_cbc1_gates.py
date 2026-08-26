"""CBC-1 behavioral certification gates B0-B9."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile

import pytest

from certification.core.trial import (
    Trial,
    TrialStage,
    StageEvidence,
    TrialMetrics,
    compose_verdict,
    REQUIRED_STAGES,
)
from certification.core.metrics import compute
from certification.stages.protocols import (
    Builder,
    StageTestRunner,
    Deployer,
    RuntimeProber,
    Destroyer,
    IndependentVerifier,
)
from certification.corpus.corpus import (
    Category,
    Workload,
    NoveltyClass,
    classify_novelty,
    default_corpus,
    ALL_CATEGORIES,
)
from certification.campaign.runner import CampaignRunner, CampaignAggregator
from compiler.core.lowering import isr_to_plan
from compiler.core.conformance import CHECKER, plan_element_ids
from compiler.core.repository import build_repository
from compiler.composition import build_backend_registry
from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _revision() -> ISRRevision:
    g = ISRGraph(
        nodes={
            "service:a": Node(id="service:a", type=NodeType.SERVICE, properties={"label": "orders"}),
            "dm:core": Node(id="dm:core", type=NodeType.DATA_MODEL, properties={"label": "Order"}),
            "event:e": Node(id="event:e", type=NodeType.EVENT, properties={"label": "OrderCreated"}),
            "sec:p": Node(id="sec:p", type=NodeType.SECURITY_POLICY),
        },
        edges={
            "pers": Edge(id="pers", type=EdgeType.PERSISTS, source_id="service:a", target_id="dm:core"),
            "pub": Edge(id="pub", type=EdgeType.PUBLISHES, source_id="service:a", target_id="event:e"),
            "sec": Edge(id="sec", type=EdgeType.SECURED_BY, source_id="service:a", target_id="sec:p"),
        },
    )
    return ISRRevision.create("cbc1-sys", "cbc1-rev", "1.0", g, Provenance(created_by="cbc1-test", created_at="2025-01-01T00:00:00Z"))


def _plan():
    return isr_to_plan(_revision())


def _backend():
    return build_backend_registry().get("python-fastapi")


# ---------------------------------------------------------------------------
# B0 — inventory
# ---------------------------------------------------------------------------

def test_b0_inventory():
    import certification.core
    import certification.core.trial
    import certification.core.metrics
    import certification.stages
    import certification.stages.protocols
    import certification.stages.docker_stages
    import certification.corpus
    import certification.corpus.corpus
    import certification.campaign
    import certification.campaign.runner


# ---------------------------------------------------------------------------
# B1 — Trial model + verdict composition
# ---------------------------------------------------------------------------

def test_b1_trial_model_and_verdict():
    all_pass = {s: True for s in TrialStage}
    assert compose_verdict(all_pass, evidence_present=True) == "CERTIFIED"
    assert compose_verdict(all_pass, evidence_present=False) == "NOT_CERTIFIED"
    fail_build = dict(all_pass)
    fail_build[TrialStage.BUILD] = False
    assert compose_verdict(fail_build, evidence_present=True) == "NOT_CERTIFIED"

    trial = Trial(
        trial_id="t1", intent="test", category="api", novelty_class="template",
        requirement_graph_hash="", genome_hash="", isr_revision_id="r1",
        backend="python-fastapi", compiler_version="1.4.0", repo_hash="abc",
        stages=[], metrics=TrialMetrics(), verdict="CERTIFIED",
    )
    assert trial.verdict == "CERTIFIED"
    assert trial.backend == "python-fastapi"


def test_b1_required_stages_count():
    assert len(REQUIRED_STAGES) == 8


# ---------------------------------------------------------------------------
# B7 — full verdict = all 9 conditions
# ---------------------------------------------------------------------------

def test_b7_full_verdict_all_conditions():
    stages = {s: True for s in TrialStage}
    assert compose_verdict(stages, evidence_present=True) == "CERTIFIED"
    for s in TrialStage:
        partial = dict(stages)
        partial[s] = False
        assert compose_verdict(partial, evidence_present=True) == "NOT_CERTIFIED"


# ---------------------------------------------------------------------------
# B8 — metrics four-class present; ISR semantic conformance headline
# ---------------------------------------------------------------------------

def test_b8_metrics_four_classes():
    stages = {s: True for s in TrialStage}
    m = compute(
        repo_files_count=10,
        stages=stages,
        structural_passed=True,
        test_passed=True,
        runtime_passed=True,
        repo_content_hash="abc123",
    )
    assert "structural_conformance" in m.compiler_correctness
    assert "tests_passed" in m.functional_correctness
    assert "deterministic_output" in m.engineering_quality
    assert "runtime_healthy" in m.operational_correctness
    assert m.isr_semantic_conformance == 1.0


def test_b8_metrics_isr_semantic_conformance_zero():
    m = compute(
        repo_files_count=5,
        stages={s: True for s in TrialStage},
        structural_passed=False,
        test_passed=True,
        runtime_passed=True,
    )
    assert m.isr_semantic_conformance == 0.0


# ---------------------------------------------------------------------------
# B2/B3/B4/B5/B6 — stage protocols exist and are enforceable
# ---------------------------------------------------------------------------

def test_b2_stage_protocols_enforceable():
    assert hasattr(Builder, "build")
    assert hasattr(StageTestRunner, "run_tests")
    assert hasattr(Deployer, "deploy")
    assert hasattr(RuntimeProber, "probe")
    assert hasattr(Destroyer, "destroy")
    assert hasattr(IndependentVerifier, "verify")


# ---------------------------------------------------------------------------
# B9 — campaign aggregation (success matrix + failure taxonomy)
# ---------------------------------------------------------------------------

def test_b9_campaign_aggregation():
    agg = CampaignAggregator()
    for i in range(5):
        t = Trial(
            trial_id=f"t{i}", intent=f"intent-{i}", category="api",
            novelty_class="template", requirement_graph_hash="", genome_hash="",
            isr_revision_id="r1", backend="python-fastapi", compiler_version="1.4.0",
            repo_hash="h", stages=[StageEvidence(
                stage=TrialStage.BUILD, passed=(i < 3),
                started_at="", completed_at="", logs_hash="",
            )], metrics=TrialMetrics(), verdict="CERTIFIED" if i < 3 else "NOT_CERTIFIED",
        )
        agg.add(t)
    s = agg.summary()
    assert s["total"] == 5
    assert s["certified"] == 3
    assert s["not_certified"] == 2
    assert s["success_rate"] == 0.6
    assert "api" in s["success_matrix"]
    ft = s["failure_taxonomy"]
    assert ft.get("build", 0) == 2


# ---------------------------------------------------------------------------
# Corpus classification
# ---------------------------------------------------------------------------

def test_corpus_classify_novelty():
    w = Workload(intent="test-intent", category=Category.API)
    assert classify_novelty(w, set(), set()) == NoveltyClass.NOVEL_INTENT
    assert classify_novelty(w, {"test-intent"}, set()) == NoveltyClass.ARCHITECTURAL


def test_default_corpus_covers_all_categories():
    corpus = default_corpus()
    cats = {w.category for w in corpus}
    assert len(cats) == 13
    assert len(ALL_CATEGORIES) == 13


# ---------------------------------------------------------------------------
# Full stub trial (compile → all stub stages → CERTIFIED)
# ---------------------------------------------------------------------------

def test_full_stub_trial_certified():
    runner = CampaignRunner()
    plan = _plan()
    backend = _backend()
    trial = runner.run_trial(
        intent="test-intent",
        category="api",
        novelty_class="template",
        plan=plan,
        revision_id="rev1",
        backend=backend,
    )
    assert trial.verdict == "CERTIFIED"
    assert len(trial.stages) == 8
    assert all(se.passed for se in trial.stages)
    assert trial.metrics.isr_semantic_conformance == 1.0
    assert trial.backend == "python-fastapi"


# ---------------------------------------------------------------------------
# Independent verify (subprocess)
# ---------------------------------------------------------------------------

def test_independent_verify_separate_process():
    plan = _plan()
    backend = _backend()
    repo = backend.compile(plan)

    d = tempfile.mkdtemp(prefix="cbc1-verify-")
    for p, c in repo.files.items():
        full = os.path.join(d, p)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(c)

    ep = backend.element_paths(plan)
    plan_hash = hashlib.sha256(
        json.dumps(sorted(ep.values())).encode("utf-8")
    ).hexdigest()
    plan_path = os.path.join(d, ".plan.json")
    with open(plan_path, "w") as f:
        json.dump({"expected_paths": sorted(ep.values())}, f)

    result = subprocess.run(
        [sys.executable, "-m", "certification.stages.independent_verify", d, plan_hash, plan_path],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["independent"] is True
    assert data["plan_match"] is True


import subprocess
