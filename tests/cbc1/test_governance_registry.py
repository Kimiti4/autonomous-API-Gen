"""Tests for the Certification Governance Registry (Phase 31 gap #5).

The registry is the cross-phase attempts/verdicts store:
  - Append-only hash-chained JSONL (separate from the wave ledger)
  - Records carry schema_id, phase_id, attempt_id, verdict, evidence_refs
  - Regressions detected: prior CERTIFIED -> current NOT_CERTIFIED

Design rules tested:
  - Default state: empty file is valid (genesis-only chain)
  - Append is hash-chained; verify() catches tampering
  - Regressions are detected for (phase, attempt) series
  - Honest missing data: no field is silently zeroed
  - Schema is stable (schema_id, schema_version)
"""
import json

import pytest

from certification.governance.registry import (
    AttemptRecord,
    CertificationGovernanceRegistry,
    GENESIS_HASH,
    SCHEMA_ID,
    SCHEMA_VERSION,
)


@pytest.fixture
def tmp_ledger(tmp_path):
    return str(tmp_path / "registry.jsonl")


def _record_kwargs(**overrides):
    base = dict(
        attempt_id="att-1",
        phase_id="phase_31_5_certification",
        recorded_at="2026-09-04T00:00:00Z",
        verdict="CERTIFIED",
        verdict_reason="all gates pass",
        evidence_refs=("cert-31-5",),
        metrics={"envelope": 500, "certified_pct": 0.85},
    )
    base.update(overrides)
    return base


def test_record_carries_schema_identity():
    r = AttemptRecord(**_record_kwargs())
    assert r.schema_id == SCHEMA_ID
    assert r.schema_version == SCHEMA_VERSION


def test_record_content_excludes_hash_chain_fields():
    """The `content()` method (used for hashing) must not include
    prev_hash or record_hash — those are derived, not source data."""
    r = AttemptRecord(**_record_kwargs())
    body = r.content()
    assert "prev_hash" not in body
    assert "record_hash" not in body


def test_envelope_contains_chain_fields():
    r = AttemptRecord(**_record_kwargs())
    env = r.to_envelope(GENESIS_HASH)
    assert env["schema_id"] == SCHEMA_ID
    assert env["prev_hash"] == GENESIS_HASH
    assert isinstance(env["record_hash"], str) and len(env["record_hash"]) == 64
    assert env["record"]["attempt_id"] == "att-1"


def test_envelope_is_content_addressable():
    r1 = AttemptRecord(**_record_kwargs(attempt_id="att-A"))
    r2 = AttemptRecord(**_record_kwargs(attempt_id="att-B"))
    env_a = r1.to_envelope(GENESIS_HASH)
    env_b = r2.to_envelope(GENESIS_HASH)
    assert env_a["record_hash"] != env_b["record_hash"]


def test_ledger_appends_hash_chain(tmp_ledger):
    reg = CertificationGovernanceRegistry(tmp_ledger)
    h1 = reg.record(**_record_kwargs(attempt_id="att-1"))
    h2 = reg.record(**_record_kwargs(attempt_id="att-2"))
    h3 = reg.record(**_record_kwargs(attempt_id="att-3"))
    assert h1 != h2 != h3
    assert reg.prev_hash == h3
    assert CertificationGovernanceRegistry.verify(tmp_ledger) is True


def test_ledger_tails_prior_chain_on_resume(tmp_path):
    """Resuming into a prior registry must continue the chain, not reset."""
    p = tmp_path / "registry.jsonl"
    reg1 = CertificationGovernanceRegistry(str(p))
    h1 = reg1.record(**_record_kwargs(attempt_id="a"))
    reg1.record(**_record_kwargs(attempt_id="b"))
    assert CertificationGovernanceRegistry.verify(str(p)) is True

    reg2 = CertificationGovernanceRegistry(str(p))
    h3 = reg2.record(**_record_kwargs(attempt_id="c"))
    assert h3 != h1
    assert reg2.prev_hash == h3
    assert CertificationGovernanceRegistry.verify(str(p)) is True


def test_verify_detects_tampering(tmp_ledger):
    reg = CertificationGovernanceRegistry(tmp_ledger)
    reg.record(**_record_kwargs(attempt_id="a"))
    reg.record(**_record_kwargs(attempt_id="b"))
    reg.record(**_record_kwargs(attempt_id="c"))
    assert CertificationGovernanceRegistry.verify(tmp_ledger) is True

    with open(tmp_ledger, encoding="utf-8") as f:
        lines = f.readlines()
    middle = json.loads(lines[1])
    middle["record"]["verdict"] = "NOT_CERTIFIED"  # attempt to flip a verdict
    lines[1] = json.dumps(middle) + "\n"
    with open(tmp_ledger, "w", encoding="utf-8") as f:
        f.writelines(lines)

    assert CertificationGovernanceRegistry.verify(tmp_ledger) is False


def test_verify_handles_missing_file(tmp_path):
    p = tmp_path / "nope.jsonl"
    assert CertificationGovernanceRegistry.verify(str(p)) is True


def test_verify_handles_malformed_json(tmp_ledger):
    with open(tmp_ledger, "w", encoding="utf-8") as f:
        f.write("not json\n")
    assert CertificationGovernanceRegistry.verify(tmp_ledger) is False


def test_read_all_returns_envelopes(tmp_ledger):
    reg = CertificationGovernanceRegistry(tmp_ledger)
    reg.record(**_record_kwargs(attempt_id="x", verdict="CERTIFIED"))
    reg.record(**_record_kwargs(attempt_id="y", verdict="NOT_CERTIFIED"))
    envelopes = CertificationGovernanceRegistry.read_all(tmp_ledger)
    assert len(envelopes) == 2
    assert envelopes[0]["record"]["attempt_id"] == "x"
    assert envelopes[1]["record"]["attempt_id"] == "y"


def test_summary_aggregates(tmp_ledger):
    reg = CertificationGovernanceRegistry(tmp_ledger)
    reg.record(**_record_kwargs(attempt_id="x", phase_id="p1", verdict="CERTIFIED"))
    reg.record(**_record_kwargs(attempt_id="y", phase_id="p1", verdict="NOT_CERTIFIED"))
    reg.record(**_record_kwargs(attempt_id="z", phase_id="p2", verdict="CERTIFIED"))
    s = reg.summary()
    assert s["record_count"] == 3
    assert s["by_phase"]["p1"] == 2
    assert s["by_phase"]["p2"] == 1
    assert s["by_verdict"]["CERTIFIED"] == 2
    assert s["by_verdict"]["NOT_CERTIFIED"] == 1
    assert s["chain_verified"] is True


# ---- Regression detection ----


def test_regression_detected_when_certified_then_not(tmp_ledger):
    reg = CertificationGovernanceRegistry(tmp_ledger)
    reg.record(**_record_kwargs(attempt_id="x", verdict="CERTIFIED", verdict_reason="pass"))
    reg.record(**_record_kwargs(attempt_id="x", verdict="NOT_CERTIFIED", verdict_reason="regress"))
    regressions = CertificationGovernanceRegistry.detect_regressions(tmp_ledger)
    assert len(regressions) == 1
    r = regressions[0]
    assert r["phase_id"] == "phase_31_5_certification"
    assert r["attempt_id"] == "x"
    assert r["before"]["verdict"] == "CERTIFIED"
    assert r["after"]["verdict"] == "NOT_CERTIFIED"
    assert r["before"]["verdict_reason"] == "pass"
    assert r["after"]["verdict_reason"] == "regress"


def test_regression_includes_metric_delta(tmp_ledger):
    reg = CertificationGovernanceRegistry(tmp_ledger)
    reg.record(**_record_kwargs(
        attempt_id="x", verdict="CERTIFIED",
        metrics={"certified_pct": 0.95, "envelope": 500},
    ))
    reg.record(**_record_kwargs(
        attempt_id="x", verdict="NOT_CERTIFIED",
        metrics={"certified_pct": 0.80, "envelope": 500},
    ))
    regressions = CertificationGovernanceRegistry.detect_regressions(tmp_ledger)
    assert len(regressions) == 1
    delta = regressions[0]["delta_metrics"]
    assert delta["certified_pct"] == pytest.approx(-0.15)


def test_no_regression_when_still_certified(tmp_ledger):
    reg = CertificationGovernanceRegistry(tmp_ledger)
    reg.record(**_record_kwargs(attempt_id="x", verdict="CERTIFIED"))
    reg.record(**_record_kwargs(attempt_id="x", verdict="CERTIFIED"))
    regressions = CertificationGovernanceRegistry.detect_regressions(tmp_ledger)
    assert regressions == []


def test_no_regression_when_first_attempt_fails(tmp_ledger):
    """A FAIL right out of the gate is not a regression; the regression
    is specifically CERTIFIED -> later-NOT_CERTIFIED."""
    reg = CertificationGovernanceRegistry(tmp_ledger)
    reg.record(**_record_kwargs(attempt_id="x", verdict="NOT_CERTIFIED"))
    reg.record(**_record_kwargs(attempt_id="x", verdict="NOT_CERTIFIED"))
    regressions = CertificationGovernanceRegistry.detect_regressions(tmp_ledger)
    assert regressions == []


def test_qualified_partial_after_certified_is_regression(tmp_ledger):
    """A QUALIFIED_PARTIAL verdict after a CERTIFIED one is a regression
    (the system lost the full certification)."""
    reg = CertificationGovernanceRegistry(tmp_ledger)
    reg.record(**_record_kwargs(attempt_id="x", verdict="CERTIFIED"))
    reg.record(**_record_kwargs(attempt_id="x", verdict="QUALIFIED_PARTIAL"))
    regressions = CertificationGovernanceRegistry.detect_regressions(tmp_ledger)
    assert len(regressions) == 1


def test_regression_per_phase_attempt_pair(tmp_ledger):
    """Regressions are scoped to (phase, attempt) pairs; one pair
    regressing does not affect another."""
    reg = CertificationGovernanceRegistry(tmp_ledger)
    reg.record(**_record_kwargs(attempt_id="a", phase_id="p1", verdict="CERTIFIED"))
    reg.record(**_record_kwargs(attempt_id="a", phase_id="p1", verdict="NOT_CERTIFIED"))
    reg.record(**_record_kwargs(attempt_id="b", phase_id="p1", verdict="CERTIFIED"))
    reg.record(**_record_kwargs(attempt_id="a", phase_id="p2", verdict="CERTIFIED"))
    reg.record(**_record_kwargs(attempt_id="a", phase_id="p2", verdict="CERTIFIED"))
    regressions = CertificationGovernanceRegistry.detect_regressions(tmp_ledger)
    # Only (p1, a) regressed
    keys = {(r["phase_id"], r["attempt_id"]) for r in regressions}
    assert keys == {("p1", "a")}


def test_regression_empty_registry(tmp_ledger):
    """Empty registry has no regressions."""
    reg = CertificationGovernanceRegistry(tmp_ledger)
    # (no records appended)
    regressions = CertificationGovernanceRegistry.detect_regressions(tmp_ledger)
    assert regressions == []


def test_evidence_refs_preserved_in_regression(tmp_ledger):
    """The regression finding includes the evidence_refs from both
    before and after so an auditor can trace the chain."""
    reg = CertificationGovernanceRegistry(tmp_ledger)
    reg.record(**_record_kwargs(
        attempt_id="x", verdict="CERTIFIED",
        evidence_refs=("cert-31-5-v1",),
    ))
    reg.record(**_record_kwargs(
        attempt_id="x", verdict="NOT_CERTIFIED",
        evidence_refs=("cert-31-5-v2", "canary-fail"),
    ))
    regressions = CertificationGovernanceRegistry.detect_regressions(tmp_ledger)
    assert regressions[0]["before"]["evidence_refs"] == ["cert-31-5-v1"]
    assert regressions[0]["after"]["evidence_refs"] == ["cert-31-5-v2", "canary-fail"]
