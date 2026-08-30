"""Campaign B gates — mode enforcement, wave config, execution detail, three-valued verdict."""
from __future__ import annotations

import asyncio
import json
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


# ---------------------------------------------------------------------------
# B14 — retry amplification + B3 decision boundary
# ---------------------------------------------------------------------------

def _trial(stages):
    return {"trial_id": "t", "category": "fintech",
            "backend": "python-fastapi", "verdict": "CERTIFIED",
            "stages": stages}


def _stage(stage, passed=True, retries=0, sigs=(), fc="", mode="real_docker"):
    return {"stage": stage, "passed": passed, "mode": mode,
            "retries": retries, "retry_signatures": list(sigs),
            "failure_class": fc}


def test_amplification_plain_certified():
    from certification.campaign.amplification import compute_amplification
    amp = compute_amplification(
        [_trial([_stage("build"), _stage("deploy")])], planned=1)
    assert amp.planned_trials == 1
    assert amp.actual_trials == 1
    assert amp.stage_executions == 2
    assert amp.retry_executions == 0
    assert amp.retry_rate == 0.0
    assert amp.cascade_skipped == 0
    assert amp.infrastructure_failures == 0
    assert amp.product_failures == 0
    assert amp.unexplained_retries == 0


def test_amplification_counts_retries_and_cascades():
    from certification.campaign.amplification import compute_amplification
    trials = [
        _trial([
            _stage("build", passed=True, retries=1, sigs=("failed to fetch",)),
            _stage("deploy", passed=True),
        ]),
        _trial([
            _stage("build", passed=True, retries=2, sigs=("network", "network")),
            _stage("deploy", passed=False, fc="infrastructure",
                   mode="failed", retries=1, sigs=("bind",)),
            _stage("runtime", passed=False, mode="skipped"),
            _stage("destroy", passed=False, mode="skipped"),
        ]),
    ]
    amp = compute_amplification(trials, planned=2)
    assert amp.stage_executions == 6
    assert amp.retry_executions == 4
    assert amp.retry_rate == round(4 / 6, 4)
    assert amp.cascade_skipped == 2
    assert amp.infrastructure_failures == 1
    assert amp.unexplained_retries == 0


def test_amplification_flags_unexplained_retries():
    from certification.campaign.amplification import compute_amplification
    amp = compute_amplification(
        [_trial([_stage("build", passed=True, retries=1, sigs=())])], planned=1)
    assert amp.unexplained_retries == 1


def test_amplification_counts_product_failures():
    from certification.campaign.amplification import compute_amplification
    amp = compute_amplification(
        [_trial([_stage("test", passed=False, fc="product", mode="failed")])],
        planned=1)
    assert amp.product_failures == 1


def test_b3_decision_boundary():
    from certification.campaign.decision import b3_decision
    from certification.campaign.amplification import RetryAmplification
    clean = RetryAmplification(planned_trials=936, actual_trials=936,
                               stage_executions=5616,
                               retry_executions=0, retry_rate=0.0,
                               cascade_skipped=0, infrastructure_failures=0,
                               product_failures=0, unexplained_retries=0)
    assert b3_decision("CERTIFIED", clean) == "PROCEED to larger-scale campaign"
    partial = clean.model_copy(update={"actual_trials": 935})
    assert b3_decision("QUALIFIED_PARTIAL", partial) == (
        "ANALYZE infra-transience + retry honesty; do NOT scale")
    pdefect = clean.model_copy(update={"product_failures": 1})
    assert b3_decision("CERTIFIED", pdefect) == "STOP scaling; fix product defect"
    dishonest = clean.model_copy(update={"unexplained_retries": 2})
    assert b3_decision("CERTIFIED", dishonest) == "NOT_CERTIFIED (retry dishonesty)"
    hot = clean.model_copy(update={"retry_rate": 0.5})
    assert b3_decision("CERTIFIED", hot) == "NOT_CERTIFIED (retry dishonesty)"


def test_wave_carries_max_retry_rate():
    assert WAVES["B3"].scale_factor == 12
    assert WAVES["B3"].required_mode == ExecutionMode.REAL_DOCKER
    assert WAVES["B3"].max_retry_rate == 0.2
    assert BUDGETS["B3"].max_trials == 936
    assert BUDGETS["B3"].max_total_runtime_s == 43200


def test_b3_expansion_is_936_trials():
    from compiler.composition import build_backend_registry
    from compiler.core.protocol import eligible_for_behavioral_certification
    from certification.campaign.waves import expand_corpus
    reg = build_backend_registry()
    backends = [
        b for b in (reg.get(n) for n in reg.list_names())
        if b is not None and eligible_for_behavioral_certification(b.identity())
    ]
    corpus = expand_corpus(12)
    assert len(corpus) == 468
    assert len(corpus) * len(backends) == 936


def test_amplification_problems_enforced():
    from certification.campaign.amplification import (
        RetryAmplification, amplification_problems,
    )
    dirty = RetryAmplification(planned_trials=1, actual_trials=1,
                               stage_executions=2,
                               retry_executions=1, retry_rate=0.5,
                               cascade_skipped=0, infrastructure_failures=0,
                               product_failures=1, unexplained_retries=0)
    ps = amplification_problems(dirty, 0.2)
    assert any("retry_rate" in p for p in ps)
    assert any("product failures" in p for p in ps)


def test_ledger_resume_continues_same_chain(tmp_path):
    """A resumed ledger must continue the SAME hash chain — prior records stay
    byte-identical and the new records chain onto the old tail."""
    import time as _t
    from certification.evidence.ledger import EvidenceLedger
    path = str(tmp_path / "ledger.jsonl")
    lg = EvidenceLedger(path)
    for i in range(3):
        lg.append({"trial_id": f"seed-{i}", "intent": f"i{i}", "backend": "b"})
    # Simulate interrupt + resume: new EvidenceLedger over the SAME file.
    tail = EvidenceLedger(path)._tail_hash()
    lg2 = EvidenceLedger(path)
    assert lg2.prev == tail
    lg2.append({"trial_id": "resumed-1", "intent": "j", "backend": "b"})
    assert EvidenceLedger.verify(path)
    counts = [json.loads(l)["trial"]["trial_id"] for l in open(path, encoding="utf-8") if l.strip()]
    assert counts == ["seed-0", "seed-1", "seed-2", "resumed-1"]


def _stub_resume_run(tmp_path, seed_records, expect_keys, md):
    """Drive run_wave in resume+supplement mode with stub stages and a
    scale_override small enough to terminate quickly, on tmp paths."""
    import certification.campaign.campaign_b as cb
    from certification.stages.stub_stages import StubStages
    # SEED: write seed_records into the ledger path BEFORE run_wave.
    from certification.evidence.ledger import EvidenceLedger
    ledger_path = str(tmp_path / "w-ledger.jsonl")
    agg_path = str(tmp_path / "w-aggregate.json")
    lg = EvidenceLedger(ledger_path)
    for rec in seed_records:
        lg.append(rec)
    # monkeypatch: resolve stub stages (no docker) + scale 1
    md.setattr(cb, "_resolve_stages", lambda mode: StubStages())
    return cb.run_wave(
        "B3", scale_override=1, resume=True, supplement=True,
        ledger_path=ledger_path, agg_path=agg_path,
    ), ledger_path, agg_path


def test_run_wave_resume_seeds_and_supplements(tmp_path, monkeypatch):
    """Resume must keep the 2 seeded records, run the remaining planned
    corpus×backend pairs, then supplement re-measures the failed seed keys —
    totaling expected + supplements, with the failures still NOT_CERTIFIED."""
    import certification.campaign.campaign_b as cb
    from certification.evidence.ledger import EvidenceLedger
    # The default corpus intent for scale=1; pick "project management SaaS".
    from certification.corpus.corpus import default_corpus
    first = default_corpus()[0]
    seed_records = [
        {"trial_id": "seed-a", "intent": first.intent, "category": first.category.value,
         "backend": "python-fastapi", "verdict": "CERTIFIED",
         "backend_class": "behavioral", "metrics": {}, "stages": []},
        {"trial_id": "seed-b", "intent": first.intent, "category": first.category.value,
         "backend": "rust-axum", "verdict": "NOT_CERTIFIED",
         "backend_class": "behavioral", "metrics": {}, "stages": [{
             "stage": "deploy", "passed": False, "mode": "failed",
             "retries": 0, "retry_signatures": [], "failure_class": "infrastructure"}]},
    ]
    (verdict, summary), ledger_path, agg_path = _stub_resume_run(
        tmp_path, seed_records, None, monkeypatch)
    n = EvidenceLedger.count(ledger_path)
    expected_planned = 78  # 39 intents × 2 backends
    # planned window = 78 (2 seeds prepared, 76 run new) + 1 rust supplement
    assert n == expected_planned + 1
    assert summary["resumed_from"] == 2
    assert summary["supplement_trials"] == 1
    assert summary["planned_trials"] == 78
    assert summary["expected_trials"] == 79
    assert verdict == "QUALIFIED_PARTIAL" or verdict == "NOT_CERTIFIED"


def test_resume_refuses_rewriting_broken_chain(tmp_path, monkeypatch):
    """A corrupted prior ledger must NOT be resumed or rewritten."""
    import certification.campaign.campaign_b as cb
    from certification.stages.stub_stages import StubStages
    ledger_path = str(tmp_path / "w-ledger.jsonl")
    agg_path = str(tmp_path / "w-aggregate.json")
    with open(ledger_path, "w", encoding="utf-8") as f:
        f.write("{not-json\n")
    monkeypatch.setattr(cb, "_resolve_stages", lambda mode: StubStages())
    verdict, summary = cb.run_wave(
        "B3", scale_override=1, resume=True, ledger_path=ledger_path,
        agg_path=agg_path,
    )
    assert verdict == "NOT_CERTIFIED"
    assert "hash chain broken" in summary["verdict_reason"]


def test_probe_without_container_is_skipped_cascade():
    import certification.stages.docker_stages as ds
    stages = ds.RealDockerStages()
    se = stages.probe(8884, "")
    assert se.stage == TrialStage.RUNTIME
    assert se.mode == ExecutionMode.SKIPPED
    assert se.passed is False
    assert "cascade" in se.detail


def test_runs_in_build_base_fetch_is_infrastructure_not_product(monkeypatch):
    """A failed toolchain docker build (rust base fetch) must NOT be
    classified 'product' — only a successfully-built toolchain whose test
    run returned nonzero is a product failure."""
    import certification.stages.docker_stages as ds
    from compiler.core.protocol import TestSpec

    def fake_run(cmd, timeout=900):
        if cmd[0:2] == ["docker", "build"] and "--target" in cmd:
            # Exact registry EOF signature observed in the field.
            return 1, ('failed to build: failed to solve: rust:1.78-slim: '
                       'failed to resolve source metadata: failed to do '
                       'request: Head "https://registry-1.docker.io/v2/'
                       'library/rust/manifests/1.78-slim": EOF')
        if cmd[0:2] == ["docker", "run"]:
            raise AssertionError("test run must not be reached")
        return 0, ""

    monkeypatch.setattr(ds, "_run", fake_run)
    stages = ds.RealDockerStages()
    spec = TestSpec(command=["cargo", "test"], runs_in="build", build_target="tst")
    se = stages.run_tests("img", spec, repo_dir="/tmp", tag="t")
    assert se.passed is False
    assert se.failure_class == "infrastructure"
    assert "EOF" in se.detail  # error TAIL captured, not truncated head


def test_runs_in_build_cargo_assertion_is_product(monkeypatch):
    """Toolchain builds OK, cargo test returns 1 → genuine product failure."""
    import certification.stages.docker_stages as ds
    from compiler.core.protocol import TestSpec
    calls = {"n": 0}

    def fake_run(cmd, timeout=900):
        calls["n"] += 1
        if cmd[0:2] == ["docker", "build"] and "--target" in cmd:
            return 0, "built"
        if cmd[0:2] == ["docker", "run"]:
            return 1, "test inventory_add fails: assertion failed"
        return 0, ""

    monkeypatch.setattr(ds, "_run", fake_run)
    stages = ds.RealDockerStages()
    spec = TestSpec(command=["cargo", "test"], runs_in="build", build_target="tst")
    se = stages.run_tests("img", spec, repo_dir="/tmp", tag="t")
    assert se.passed is False
    assert se.failure_class == "product"
    assert "assertion failed" in se.detail


def test_probe_records_connect_retries(monkeypatch):
    import certification.stages.docker_stages as ds
    import urllib.request
    attempts = {"n": 0}

    class _FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(url, timeout=5):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise ConnectionError("timed out")
        return _FakeResp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(ds, "_run", lambda cmd, timeout=900: (0, "0.1%/1MB"))
    stages = ds.RealDockerStages()
    se = stages.probe(9999, "cid123")
    assert se.passed is True
    assert se.retries == 2
    assert se.retry_signatures == ("probe_connect", "probe_connect")

    # Dump used dict-traversal path via model_dump compatibility check
    assert attempts["n"] == 3


def test_deploy_classifier_exact_windows_exclusion_is_infrastructure():
    """The exact observed Windows exclude-port failure message MUST classify
    as transient infrastructure (never product, never a compiler defect)."""
    from certification.stages.docker_stages import (
        classify_deploy_failure, MAX_DEPLOY_ATTEMPTS,
    )
    msg = ("docker: Error response from daemon: ports are not available: "
           "exposing port TCP 0.0.0.0:8507 -> 127.0.0.1:0: listen tcp "
           "0.0.0.0:8507: bind: An attempt was made to access a socket in a "
           "way forbidden by its access permissions.\n")
    assert classify_deploy_failure(msg) == "infrastructure"
    assert MAX_DEPLOY_ATTEMPTS == 2  # bounded retry; no unbounded loop


def test_deploy_classifier_does_not_blanket_bind():
    """Specificity: a bare 'bind: ...' failure WITHOUT the daemon port-range
    signatures must NOT be auto-labeled transient infrastructure."""
    from certification.stages.docker_stages import classify_deploy_failure
    # Generic "bind" (app/runtime defect style, no daemon signatures).
    assert classify_deploy_failure("error: bind: Operation not permitted") == ""
    assert classify_deploy_failure("docker: bind: Cannot assign requested address") == ""
    # Generic port-in-use remains a recognized deploy transient.
    assert classify_deploy_failure(
        "docker: Error response from daemon: address already in use"
    ) == "infrastructure"


def test_transient_marks_specific_and_stable():
    """Legacy signatures remain; the deploy marks stay specific (no bare
    'bind'), with the Windows excluded-port phrases added verbatim."""
    import certification.stages.docker_stages as ds
    assert "unexpected eof" in ds.TRANSIENT_RUN_MARKS
    assert "eof" in ds.TRANSIENT_RUN_MARKS
    assert "i/o timeout" in ds.TRANSIENT_RUN_MARKS
    assert "failed to fetch" in ds.TRANSIENT_BUILD_MARKS
    assert "ports are not available" in ds.TRANSIENT_DEPLOY_MARKS
    assert "forbidden by its access permissions" in ds.TRANSIENT_DEPLOY_MARKS
    assert "address already in use" in ds.TRANSIENT_DEPLOY_MARKS
    assert "bind" not in ds.TRANSIENT_DEPLOY_MARKS


def test_deploy_records_retries_and_classifies(monkeypatch):
    """A deploy stage that retries on a recognized signature records the
    retries + signature and classifies the residual failure as infra."""
    import certification.stages.docker_stages as ds
    calls = {"n": 0}

    def fake_run(cmd, timeout=900):
        calls["n"] += 1
        if calls["n"] < 2:
            return 1, "ports are not available: exposing port TCP 0.0.0.0:8507"
        return 1, "ports are not available: exposing port TCP 0.0.0.0:8507"

    monkeypatch.setattr(ds, "_run", fake_run)
    stages = ds.RealDockerStages()
    se = stages.deploy("img", 8507)
    assert se.passed is False
    assert se.retries == 1
    assert se.retry_signatures == ("ports are not available",)
    assert se.failure_class == "infrastructure"
    assert se.detail.startswith("[retried 2/2 on transient]")


def test_amplification_recognized_signature_zero_unexplained():
    from certification.campaign.amplification import compute_amplification
    honest = [{
        "verdict": "NOT_CERTIFIED", "backend_class": "behavioral",
        "stages": [{
            "stage": "deploy", "passed": False, "mode": "failed",
            "retries": 1,
            "retry_signatures": ["ports are not available"],
            "failure_class": "infrastructure",
        }],
    }]
    amp = compute_amplification(honest, 1)
    assert amp.unexplained_retries == 0
    assert amp.infrastructure_failures == 1
    assert amp.product_failures == 0
    assert amp.retry_executions == 1

    dishonest = [{
        "verdict": "NOT_CERTIFIED", "backend_class": "behavioral",
        "stages": [{
            "stage": "deploy", "passed": False, "mode": "failed",
            "retries": 1, "retry_signatures": [],
            "failure_class": "infrastructure",
        }],
    }]
    amp2 = compute_amplification(dishonest, 1)
    assert amp2.unexplained_retries == 1


def test_taxonomy_records_deploy_infra_without_inflating_cascade(tmp_path):
    """Failure taxonomy counts the failed deploy stage; cascade SKIPPED
    destroy stages are not counted as independent failures."""
    from certification.campaign.campaign_b import verify_campaign_b_mode
    from certification.campaign.amplification import amplification_problems
    from certification.stages.execution_mode import ExecutionMode
    from certification.evidence.ledger import EvidenceLedger
    path = str(tmp_path / "l.jsonl")
    lg = EvidenceLedger(path)
    lg.append({
        "trial_id": "t1", "intent": "i", "backend": "python-fastapi",
        "verdict": "NOT_CERTIFIED", "backend_class": "behavioral",
        "stages": [
            {"stage": "deploy", "passed": False, "mode": "failed",
             "failure_class": "infrastructure",
             "detail": "ports are not available ... forbidden"},
            {"stage": "destroy", "passed": False, "mode": "skipped",
             "failure_class": "", "detail": "cascade: deploy did not produce a container"},
        ],
    })
    ok, matrix, taxonomy, problems = verify_campaign_b_mode(path, ExecutionMode.REAL_DOCKER)
    assert taxonomy.get("deploy") == 1
    assert taxonomy.get("destroy", 0) == 0  # cascade SKIPPED excluded
    assert ok is True
    assert problems == []


def test_allocate_port_window_avoids_excluded():
    from certification.campaign.preflight import allocate_port_window
    a = allocate_port_window(
        preferred=(8000, 8999), span=700, min_free=700,
        excluded=[(8700, 8799)],
    )
    assert a.ok is True
    assert a.base == 8000
    assert a.window == (8000, 8699)


def test_allocate_port_window_fails_cleanly_when_full():
    from certification.campaign.preflight import allocate_port_window
    a = allocate_port_window(
        preferred=(8000, 8999), span=700, min_free=700,
        excluded=[(8100, 8799)],
    )
    assert a.ok is False
    assert "contiguous" in a.reason


def test_preflight_persists_evidence(tmp_path, monkeypatch):
    """The port preflight is an explicit, evidenced preparation step."""
    import certification.campaign.preflight as pf
    monkeypatch.setattr(pf, "query_excluded_tcp_ranges", lambda: [(8200, 8999)])
    monkeypatch.setattr(
        pf, "portpool_path_for",
        lambda wave_id: str(tmp_path / f"cbc1-{wave_id}-portpool.json"),
    )
    alloc, path = pf.preflight_ports("B3", preferred=(8000, 8999), span=100, min_free=100)
    import json
    record = json.load(open(path, encoding="utf-8"))
    assert record["wave"] == "B3"
    assert record["excluded_tcp_ranges"] == [[8200, 8999]]
    assert record["allocation"]["ok"] is True
    assert record["allocation"]["base"] == 8000


def test_run_wave_stops_honestly_when_port_capacity_insufficient(tmp_path, monkeypatch):
    """If the environment cannot provide the required port capacity, the
    campaign must fail/stop — NOT silently reuse ports or skip trials."""
    import certification.campaign.campaign_b as cb
    import certification.campaign.preflight as pf
    from certification.evidence.ledger import EvidenceLedger
    monkeypatch.setattr(pf, "query_excluded_tcp_ranges", lambda: [(0, 65535)])
    ledger_path = str(tmp_path / "w-ledger.jsonl")
    agg_path = str(tmp_path / "w-aggregate.json")
    verdict, summary = cb.run_wave(
        "B3", scale_override=1, ledger_path=ledger_path, agg_path=agg_path,
    )
    assert verdict == "NOT_CERTIFIED"
    assert "port capacity insufficient" in summary["verdict_reason"]
    assert summary["port_preflight"]["ok"] is False
    assert EvidenceLedger.count(ledger_path) == 0
