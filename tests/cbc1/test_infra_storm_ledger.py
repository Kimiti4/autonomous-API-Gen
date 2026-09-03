"""Tests for the infra-storm ledger (LEARN-ONLY side-channel for
infrastructure-classified failures)."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from certification.evidence.infra_storm import (
    GENESIS_HASH,
    SCHEMA_ID,
    SCHEMA_VERSION,
    InfraStormLedger,
    InfraStormRecord,
)


@pytest.fixture
def tmp_ledger(tmp_path):
    return str(tmp_path / "infra-storm.jsonl")


def _record_kwargs(**overrides):
    base = dict(
        source_wave="B3",
        trial_id="trial-001",
        intent="billing-01",
        backend="rust-axum",
        stage="build",
        cause="infrastructure",
        feedback_domain="infrastructure",
        cause_mark="connection",
        detail_excerpt="connection error fetching crates",
        retry_signatures=("connection", "timeout"),
        repair_eligible=False,
    )
    base.update(overrides)
    return base


def test_record_carries_required_fields():
    r = InfraStormRecord.build(**_record_kwargs())
    assert r.schema_id == SCHEMA_ID
    assert r.schema_version == SCHEMA_VERSION
    assert r.cause == "infrastructure"
    assert r.feedback_domain == "infrastructure"
    assert r.repair_eligible is False
    assert "connection" in r.detail_excerpt
    assert "connection" in r.retry_signatures


def test_envelope_contains_record_and_chain_fields():
    r = InfraStormRecord.build(**_record_kwargs())
    env = r.to_envelope(GENESIS_HASH)
    assert env["schema_id"] == SCHEMA_ID
    assert env["schema_version"] == SCHEMA_VERSION
    assert env["prev_hash"] == GENESIS_HASH
    assert isinstance(env["record_hash"], str) and len(env["record_hash"]) == 64
    assert "record" in env
    assert env["record"]["trial_id"] == "trial-001"
    assert env["record"]["backend"] == "rust-axum"


def test_envelope_is_content_addressable():
    r1 = InfraStormRecord.build(**_record_kwargs(trial_id="trial-A"))
    r2 = InfraStormRecord.build(**_record_kwargs(trial_id="trial-B"))
    env_a = r1.to_envelope(GENESIS_HASH)
    env_b = r2.to_envelope(GENESIS_HASH)
    assert env_a["record_hash"] != env_b["record_hash"]


def test_ledger_appends_hash_chain(tmp_ledger):
    led = InfraStormLedger(tmp_ledger)
    h1 = led.record(**_record_kwargs(trial_id="t1"))
    h2 = led.record(**_record_kwargs(trial_id="t2"))
    h3 = led.record(**_record_kwargs(trial_id="t3"))
    assert h1 != h2 != h3
    assert led.prev_hash == h3
    assert InfraStormLedger.verify(tmp_ledger) is True


def test_ledger_tails_prior_chain_on_resume(tmp_path):
    """Resuming into a prior ledger must continue the chain, not reset it."""
    p = tmp_path / "infra.jsonl"
    led1 = InfraStormLedger(str(p))
    h1 = led1.record(**_record_kwargs(trial_id="t1"))
    led1.record(**_record_kwargs(trial_id="t2"))
    assert InfraStormLedger.verify(str(p)) is True

    led2 = InfraStormLedger(str(p))
    h3 = led2.record(**_record_kwargs(trial_id="t3"))
    assert h3 != h1
    assert led2.prev_hash == h3
    assert InfraStormLedger.verify(str(p)) is True

    with open(p, encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    assert len(lines) == 3
    third = json.loads(lines[-1])
    assert third["record"]["trial_id"] == "t3"
    assert third["prev_hash"] == json.loads(lines[1])["record_hash"]


def test_verify_detects_tampering(tmp_ledger):
    led = InfraStormLedger(tmp_ledger)
    led.record(**_record_kwargs(trial_id="t1"))
    led.record(**_record_kwargs(trial_id="t2"))
    led.record(**_record_kwargs(trial_id="t3"))
    assert InfraStormLedger.verify(tmp_ledger) is True

    # Tamper with the middle record's cause
    with open(tmp_ledger, encoding="utf-8") as f:
        lines = f.readlines()
    middle = json.loads(lines[1])
    middle["record"]["cause"] = "compiler"  # attempt to make it look causally actionable
    lines[1] = json.dumps(middle) + "\n"
    with open(tmp_ledger, "w", encoding="utf-8") as f:
        f.writelines(lines)

    assert InfraStormLedger.verify(tmp_ledger) is False


def test_summary_aggregates_by_cause_stage_backend(tmp_ledger):
    led = InfraStormLedger(tmp_ledger)
    led.record(**_record_kwargs(trial_id="t1", stage="build", backend="rust-axum", cause="infrastructure"))
    led.record(**_record_kwargs(trial_id="t2", stage="build", backend="rust-axum", cause="infrastructure"))
    led.record(**_record_kwargs(trial_id="t3", stage="test", backend="rust-axum", cause="infrastructure"))
    led.record(**_record_kwargs(trial_id="t4", stage="build", backend="python-fastapi", cause="infrastructure"))
    s = led.summary()
    assert s["record_count"] == 4
    assert s["by_cause"] == {"infrastructure": 4}
    assert s["by_stage"] == {"build": 3, "test": 1}
    assert s["by_backend"] == {"rust-axum": 3, "python-fastapi": 1}
    assert s["chain_verified"] is True


def test_verify_handles_missing_file(tmp_path):
    p = tmp_path / "nope.jsonl"
    assert InfraStormLedger.verify(str(p)) is True  # no file == empty == valid


def test_verify_handles_malformed_json(tmp_ledger):
    with open(tmp_ledger, "w", encoding="utf-8") as f:
        f.write("not json\n")
    assert InfraStormLedger.verify(tmp_ledger) is False


def test_independent_from_verdict_ledger(tmp_path):
    """The infra-storm ledger is in its own file. The verdict ledger
    is never written to. The infra-storm ledger is not coupled to any
    other ledger file."""
    infra_p = tmp_path / "infra.jsonl"
    verdict_p = tmp_path / "verdict.jsonl"
    led = InfraStormLedger(str(infra_p))
    led.record(**_record_kwargs(trial_id="t1"))
    # Write something to verdict to make sure they do not interfere
    verdict_p.write_text(
        json.dumps(
            {"schema_id": "verdict", "record_hash": "0" * 64, "trial": {}}
        )
        + "\n"
    )
    assert InfraStormLedger.verify(str(infra_p)) is True
    assert os.path.exists(verdict_p)
    # The infra-storm file is independent (no reference to verdict)
    with open(infra_p, encoding="utf-8") as f:
        env = json.loads(f.readline())
    assert "verdict" not in env.get("record", {})


def test_record_excerpt_is_truncated(tmp_ledger):
    long_detail = "x" * 5000
    led = InfraStormLedger(tmp_ledger)
    led.record(**_record_kwargs(trial_id="t1", detail_excerpt=long_detail))
    with open(tmp_ledger, encoding="utf-8") as f:
        env = json.loads(f.readline())
    assert len(env["record"]["detail_excerpt"]) == 512


def test_record_never_contains_evidence_refs_to_verdict_chain(tmp_ledger):
    """Records carry only a `trial_id` for ONE-WAY correlation to the
    verdict ledger. They do not contain `evidence_refs` or any other
    reverse-edge that would couple the two chains."""
    led = InfraStormLedger(tmp_ledger)
    led.record(**_record_kwargs(trial_id="trial-X"))
    with open(tmp_ledger, encoding="utf-8") as f:
        env = json.loads(f.readline())
    forbidden = (
        "evidence_refs",
        "verdict_ledger_ref",
        "certification_event_ref",
    )
    for field in forbidden:
        assert field not in env["record"], (
            f"infra-storm record must not contain {field!r}"
        )
