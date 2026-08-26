"""Campaign B gates — mode enforcement, wave config, execution detail, three-valued verdict."""
from __future__ import annotations
import asyncio
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
    Wave,
    WaveId,
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

    se2 = stages.run_tests("test-image", ["pytest"])
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
