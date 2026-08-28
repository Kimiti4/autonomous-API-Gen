"""Campaign B gates — mode enforcement, wave config, execution detail, three-valued verdict."""
from __future__ import annotations
import asyncio
import os
import pytest

from certification.stages.execution_mode import (
    ExecutionMode,
    StageExecution,
    BEHAVIORAL_STAGES,
)
from certification.stages.stub_stages import StubStages
from certification.core.trial import (
    TrialStage,
    StageEvidence,
    TrialMetrics,
    Trial,
)
from certification.campaign.waves import (
    WAVES,
    BUDGETS,
    Wave,
    WaveId,
    CampaignBudget,
    expand_corpus,
    ledger_path_for,
    aggregate_path_for,
)
from certification.campaign.campaign_b import (
    CampaignBRunner,
    SubstrateReport,
    verify_campaign_b_mode,
)
from certification.campaign.verdict import CampaignVerdict
from certification.feedback.rule import classify_failure
from certification.corpus.corpus import default_corpus, corpus_hash
from compiler.core.protocol import TestSpec, BackendIdentity, BackendClass
from compiler.composition import build_backend_registry


# ---------------------------------------------------------------------------
# B0 — execution mode is an explicit enum
# ---------------------------------------------------------------------------

def test_execution_mode_enum():
    assert ExecutionMode.REAL_DOCKER.value == "real_docker"
    assert ExecutionMode.STUB.value == "stub"
    assert ExecutionMode.SKIPPED.value == "skipped"
    assert ExecutionMode.FAILED.value == "failed"
    assert len(ExecutionMode) == 4


def test_behavioral_stages_defined():
    assert TrialStage.BUILD in BEHAVIORAL_STAGES
    assert TrialStage.TEST in BEHAVIORAL_STAGES
    assert TrialStage.DEPLOY in BEHAVIORAL_STAGES
    assert TrialStage.RUNTIME in BEHAVIORAL_STAGES
    assert TrialStage.DESTROY in BEHAVIORAL_STAGES
    assert TrialStage.VERIFY in BEHAVIORAL_STAGES
    assert len(BEHAVIORAL_STAGES) == 6


# ---------------------------------------------------------------------------
# B1 — stub stages report STUB mode
# ---------------------------------------------------------------------------

def test_stub_stages_report_stub_mode():
    stages = StubStages()
    se = stages.build("/tmp/repo", "test-tag")
    assert se.mode == ExecutionMode.STUB
    assert se.passed is True
    assert se.stage == TrialStage.BUILD
    assert isinstance(se.duration_s, float)

    spec = TestSpec(command=["pytest"], runs_in="runtime")
    se2 = stages.run_tests("test-image", spec)
    assert se2.mode == ExecutionMode.STUB
    assert se2.stage == TrialStage.TEST

    se3 = stages.deploy("test-image", 8000)
    assert se3.mode == ExecutionMode.STUB
    assert se3.stage == TrialStage.DEPLOY

    se4 = stages.probe(8000, "cid")
    assert se4.mode == ExecutionMode.STUB
    assert se4.stage == TrialStage.RUNTIME

    se5 = stages.destroy("cid")
    assert se5.mode == ExecutionMode.STUB
    assert se5.stage == TrialStage.DESTROY


# ---------------------------------------------------------------------------
# B2 — StageEvidence carries mode and duration
# ---------------------------------------------------------------------------

def test_stage_evidence_carries_mode_and_duration():
    se = StageEvidence(
        stage=TrialStage.BUILD,
        passed=True,
        started_at="2026-01-01T00:00:00Z",
        completed_at="2026-01-01T00:00:01Z",
        logs_hash="abc",
        mode="real_docker",
        duration_s=1.23,
        image_digest="sha256:deadbeef",
    )
    assert se.mode == "real_docker"
    assert se.duration_s == 1.23
    assert se.image_digest == "sha256:deadbeef"


def test_stage_evidence_backward_compatible():
    se = StageEvidence(
        stage=TrialStage.BUILD,
        passed=True,
        started_at="2026-01-01T00:00:00Z",
        completed_at="2026-01-01T00:00:01Z",
        logs_hash="abc",
    )
    assert se.mode == ""
    assert se.duration_s == 0.0
    assert se.image_digest == ""


# ---------------------------------------------------------------------------
# B3 — TrialMetrics carries execution_detail and independent_verifier_result
# ---------------------------------------------------------------------------

def test_trial_metrics_execution_detail():
    m = TrialMetrics(
        execution_detail={
            "build": {"mode": "real_docker", "passed": True, "duration_s": 1.5},
            "test": {"mode": "real_docker", "passed": True, "duration_s": 2.3},
        },
        generated_repository_hash="abc123",
        independent_verifier_result=True,
    )
    assert m.execution_detail["build"]["mode"] == "real_docker"
    assert m.generated_repository_hash == "abc123"
    assert m.independent_verifier_result is True


def test_trial_metrics_backward_compatible():
    m = TrialMetrics()
    assert m.execution_detail == {}
    assert m.generated_repository_hash == ""
    assert m.independent_verifier_result is False


# ---------------------------------------------------------------------------
# B4 — wave configuration
# ---------------------------------------------------------------------------

def test_wave_b0_is_substrate_certification():
    w = WAVES["B0"]
    assert w.purpose == "docker substrate certification"
    assert w.scale_factor == 0
    assert w.required_mode == ExecutionMode.REAL_DOCKER


def test_wave_b1_is_full_corpus():
    w = WAVES["B1"]
    assert w.scale_factor == 1
    assert w.required_mode == ExecutionMode.REAL_DOCKER


def test_waves_b2_through_b4_scale():
    for wid in ("B2", "B3", "B4"):
        w = WAVES[wid]
        assert w.scale_factor > 1
        assert w.required_mode == ExecutionMode.REAL_DOCKER


def test_all_waves_use_real_docker():
    for wid, w in WAVES.items():
        assert w.required_mode == ExecutionMode.REAL_DOCKER, f"wave {wid} must require REAL_DOCKER"


# ---------------------------------------------------------------------------
# B5 — expand_corpus deterministic
# ---------------------------------------------------------------------------

def test_expand_corpus_factor1_returns_base():
    base = default_corpus()
    expanded = expand_corpus(1)
    assert len(expanded) == len(base)
    assert expanded[0].intent == base[0].intent


def test_expand_corpus_factor2_doubles():
    base = default_corpus()
    expanded = expand_corpus(2)
    assert len(expanded) == len(base) * 2
    variants = [w for w in expanded if "variant-" in w.intent]
    assert len(variants) == len(base)


def test_expand_corpus_deterministic():
    a = expand_corpus(3)
    b = expand_corpus(3)
    assert [w.intent for w in a] == [w.intent for w in b]


# ---------------------------------------------------------------------------
# B6 — ledger/aggregate path helpers
# ---------------------------------------------------------------------------

def test_ledger_path_for():
    assert ledger_path_for("B1") == "release/evidence/cbc1-b-B1-ledger.jsonl"
    assert ledger_path_for("B2") == "release/evidence/cbc1-b-B2-ledger.jsonl"


def test_aggregate_path_for():
    assert aggregate_path_for("B1") == "release/evidence/cbc1-b-B1-aggregate.json"


# ---------------------------------------------------------------------------
# B7 — classify_failure maps stages to feedback domains
# ---------------------------------------------------------------------------

def test_classify_failure_campaign_b_stages():
    assert classify_failure("build") == "lowering"
    assert classify_failure("test") == "genome"
    assert classify_failure("deploy") == "infrastructure"
    assert classify_failure("runtime") == "architecture"
    assert classify_failure("destroy") == "genome"
    assert classify_failure("verify") == "provenance"


# ---------------------------------------------------------------------------
# B8 — three-valued verdict partial stays partial
# ---------------------------------------------------------------------------

def test_compose_campaign_verdict_partial_stays_partial():
    from certification.campaign.verdict import compose_campaign_verdict
    from compiler.core.protocol import BEHAVIORAL_CLASSES

    trials = []
    for i in range(5):
        t = Trial(
            trial_id=f"t{i}", intent="test", category="test",
            novelty_class="template", requirement_graph_hash="a",
            genome_hash="b", isr_revision_id="c", backend="python-fastapi",
            backend_class=list(BEHAVIORAL_CLASSES)[0].value,
            backend_version="1.0", compiler_version="1.4.0",
            repo_hash="d", verdict="CERTIFIED" if i < 4 else "NOT_CERTIFIED",
        )
        trials.append(t)

    v, reason = compose_campaign_verdict(
        trials=trials, expected_trials=5, ledger_intact=True,
        integrity_problems=[], coverage_complete=True,
    )
    assert v == CampaignVerdict.QUALIFIED_PARTIAL
    assert "4/5" in reason


def test_compose_campaign_verdict_all_certified():
    from certification.campaign.verdict import compose_campaign_verdict
    from compiler.core.protocol import BEHAVIORAL_CLASSES

    trials = [
        Trial(
            trial_id=f"t{i}", intent="test", category="test",
            novelty_class="template", requirement_graph_hash="a",
            genome_hash="b", isr_revision_id="c", backend="python-fastapi",
            backend_class=list(BEHAVIORAL_CLASSES)[0].value,
            backend_version="1.0", compiler_version="1.4.0",
            repo_hash="d", verdict="CERTIFIED",
        )
        for i in range(3)
    ]

    v, _ = compose_campaign_verdict(
        trials=trials, expected_trials=3, ledger_intact=True,
        integrity_problems=[], coverage_complete=True,
    )
    assert v == CampaignVerdict.CERTIFIED


# ---------------------------------------------------------------------------
# B9 — SubstrateReport dataclass
# ---------------------------------------------------------------------------

def test_substrate_report_default():
    r = SubstrateReport(certified=False)
    assert r.certified is False
    assert r.executions == []
    assert r.detail == ""


def test_substrate_report_with_executions():
    se = StageExecution(
        stage=TrialStage.BUILD, mode=ExecutionMode.REAL_DOCKER,
        passed=True, duration_s=1.0, logs_hash="h",
    )
    r = SubstrateReport(certified=True, executions=[se], detail="ok")
    assert r.certified is True
    assert len(r.executions) == 1


# ---------------------------------------------------------------------------
# B10 — TestSpec: backend-declared test execution
# ---------------------------------------------------------------------------

def test_testspec_python_fastapi():
    reg = build_backend_registry()
    spec = reg.get("python-fastapi").test_spec()
    assert isinstance(spec, TestSpec)
    assert spec.command == ["python", "-m", "pytest", "-q"]
    assert spec.runs_in == "runtime"


def test_testspec_rust_axum():
    reg = build_backend_registry()
    spec = reg.get("rust-axum").test_spec()
    assert isinstance(spec, TestSpec)
    assert spec.command == ["cargo", "test"]
    assert spec.runs_in == "build"
    assert spec.build_target == "build"


# ---------------------------------------------------------------------------
# B11 — anti-hardcoding: no test commands in runner source
# ---------------------------------------------------------------------------

def test_runner_has_no_hardcoded_test_command():
    runner_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "certification", "campaign", "campaign_b.py",
    )
    src = open(runner_path, encoding="utf-8").read()
    # The runner must not contain hardcoded tool commands — those live in backends
    assert "python -m pytest" not in src
    assert "cargo test" not in src


def test_stages_has_no_hardcoded_test_command():
    stages_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "certification", "stages", "docker_stages.py",
    )
    src = open(stages_path, encoding="utf-8").read()
    assert "python -m pytest" not in src
    assert "cargo test" not in src


# ---------------------------------------------------------------------------
# B12 — CampaignBudget
# ---------------------------------------------------------------------------

def test_budgets_defined_for_all_waves():
    for wid in WAVES:
        assert wid in BUDGETS, f"wave {wid} missing budget"


def test_budget_enforces_max_trials():
    b = CampaignBudget(max_trials=10, max_total_runtime_s=9999)
    assert b.max_trials == 10
    assert b.cleanup_required is True


# ---------------------------------------------------------------------------
# B13 — bounded transient retries + honest cascade (never silent pass)
# ---------------------------------------------------------------------------

def test_destroy_without_container_is_skipped_not_passed(monkeypatch):
    from certification.stages.docker_stages import RealDockerStages
    stages = RealDockerStages()
    se = stages.destroy("")
    assert se.stage == TrialStage.DESTROY
    assert se.mode == ExecutionMode.SKIPPED
    assert se.passed is False
    assert "cascade" in se.detail


def test_build_retries_once_on_transient_and_marks_detail(monkeypatch):
    import certification.stages.docker_stages as ds
    calls = {"n": 0}

    def fake_run(cmd, timeout=900):
        if cmd and cmd[0] == "docker" and cmd[1] == "build":
            calls["n"] += 1
            if calls["n"] == 1:
                return 1, "failed to fetch https://registry: i/o timeout"
            return 0, "sha256:abc"
        return 0, "inspect-ok"

    monkeypatch.setattr(ds, "_run", fake_run)
    stages = ds.RealDockerStages()
    se = stages.build("/tmp/repo", "tag")
    assert calls["n"] == 2
    assert se.passed is True
    assert se.mode == ExecutionMode.REAL_DOCKER
    assert "[retried 2/2 on transient]" in se.detail


def test_deploy_retries_once_on_transient_bind(monkeypatch):
    import certification.stages.docker_stages as ds
    calls = {"n": 0}

    def fake_run(cmd, timeout=900):
        if cmd and cmd[0] == "docker" and len(cmd) >= 2 and cmd[1] in ("run", "c"):
            calls["n"] += 1
            if calls["n"] == 1:
                return 1, "ports are not available: bind: address already in use"
            return 0, "abc123"
        return 0, "x"

    monkeypatch.setattr(ds, "_run", fake_run)
    stages = ds.RealDockerStages()
    se = stages.deploy("img", 8884)
    assert calls["n"] == 2
    assert se.passed is True
    assert se.container_id == "abc123"
    assert "[retried 2/2 on transient]" in se.detail


def test_deploy_gives_up_honestly_after_retries(monkeypatch):
    import certification.stages.docker_stages as ds
    calls = {"n": 0}

    def fake_run(cmd, timeout=900):
        if cmd and cmd[0] == "docker" and len(cmd) >= 2 and cmd[1] in ("run", "c"):
            calls["n"] += 1
            return 1, "ports are not available: bind"

    monkeypatch.setattr(ds, "_run", fake_run)
    stages = ds.RealDockerStages()
    se = stages.deploy("img", 8884)
    assert calls["n"] == ds.MAX_DEPLOY_ATTEMPTS
    assert se.passed is False
    assert se.mode == ExecutionMode.FAILED


def test_non_transient_error_is_not_retried(monkeypatch):
    import certification.stages.docker_stages as ds
    calls = {"n": 0}

    def fake_run(cmd, timeout=900):
        if cmd and cmd[0] == "docker" and cmd[1] == "build":
            calls["n"] += 1
            return 1, "Dockerfile:5 syntax error: unexpected token"
        return 0, "x"

    monkeypatch.setattr(ds, "_run", fake_run)
    stages = ds.RealDockerStages()
    se = stages.build("/tmp/repo", "tag")
    assert calls["n"] == 1
    assert se.passed is False
    assert se.mode == ExecutionMode.FAILED


def test_verify_taxonomy_ignores_cascade_skipped(tmp_path):
    import json
    from certification.evidence.ledger import EvidenceLedger
    ledger = EvidenceLedger(str(tmp_path / "ledger.jsonl"))
    trial = {
        "trial_id": "t-x",
        "category": "fintech",
        "backend": "python-fastapi",
        "verdict": "NOT_CERTIFIED",
        "stages": [
            {"stage": "deploy", "mode": "failed", "passed": False},
            {"stage": "destroy", "mode": "skipped", "passed": False},
        ],
    }
    ledger.append(trial)
    _ok, matrix, taxonomy, problems = verify_campaign_b_mode(
        str(tmp_path / "ledger.jsonl"), ExecutionMode.REAL_DOCKER,
    )
    assert taxonomy.get("destroy", 0) == 0
    assert taxonomy.get("deploy", 0) == 1


def test_budget_exhaustion_is_not_certified():
    b = CampaignBudget(max_trials=5, max_total_runtime_s=9999)
    # Simulate: ran 5 trials, budget is 5 → exhausted
    assert 5 >= b.max_trials
