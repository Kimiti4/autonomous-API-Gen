"""Regression tests for conservative cross-pipeline obligation adapters."""
from types import SimpleNamespace

import pytest

from tiannara.application.compiler.obligation_adapters import (
    adapt_legacy_gate,
    adapt_project_outcome,
)
from tiannara.domain.models.compiler_obligation import Disposition

SOURCE_HASH = "a" * 64


def test_legacy_held_gate_is_unknown_until_evidence_is_independently_bound():
    gate = SimpleNamespace(
        gate_id="H_evidence_binding",
        held=True,
        evidence="ledger recorded event range",
    )
    record = adapt_legacy_gate(
        gate,
        source_graph_id="legacy-isr-1",
        source_graph_hash=SOURCE_HASH,
        consumer_binding="legacy-backend@1",
    )
    assert record.disposition is Disposition.UNKNOWN
    assert not record.acceptance_scenarios
    assert any("not independently verified" in note for note in record.limitations)


def test_legacy_failed_gate_remains_fail():
    gate = SimpleNamespace(gate_id="D_semantic_coverage", held=False, evidence="missing semantics")
    record = adapt_legacy_gate(
        gate,
        source_graph_id="legacy-isr-1",
        source_graph_hash=SOURCE_HASH,
        consumer_binding="legacy-backend@1",
    )
    assert record.disposition is Disposition.FAIL


def test_legacy_gate_without_consumer_is_blocked():
    gate = SimpleNamespace(gate_id="A_read_only", held=True, evidence="unchanged")
    record = adapt_legacy_gate(
        gate,
        source_graph_id="legacy-isr-1",
        source_graph_hash=SOURCE_HASH,
    )
    assert record.disposition is Disposition.BLOCKED_NO_CONSUMER


def test_cap_c_generation_success_and_static_verification_are_not_pass():
    outcome = SimpleNamespace(
        planned=SimpleNamespace(backend_id="fastapi_hexagonal"),
        status="success",
        verification_report=SimpleNamespace(ok=True),
        verification_reason="static checks passed",
        error=None,
    )
    record = adapt_project_outcome(
        outcome,
        source_graph_id="cap-c-isr-1",
        source_graph_hash=SOURCE_HASH,
    )
    assert record.disposition is Disposition.UNKNOWN
    assert not record.acceptance_scenarios


def test_cap_c_failed_generation_maps_to_fail():
    outcome = SimpleNamespace(
        planned=SimpleNamespace(backend_id="fastapi_hexagonal"),
        status="failed",
        verification_report=None,
        verification_reason="backend execution failed",
        error="compiler error",
    )
    record = adapt_project_outcome(
        outcome,
        source_graph_id="cap-c-isr-1",
        source_graph_hash=SOURCE_HASH,
    )
    assert record.disposition is Disposition.FAIL


def test_cap_c_missing_consumer_is_blocked():
    outcome = SimpleNamespace(
        planned=None,
        status="success",
        verification_report=SimpleNamespace(ok=True),
        verification_reason="static checks passed",
        error=None,
    )
    record = adapt_project_outcome(
        outcome,
        source_graph_id="cap-c-isr-1",
        source_graph_hash=SOURCE_HASH,
    )
    assert record.disposition is Disposition.BLOCKED_NO_CONSUMER


@pytest.mark.parametrize("bad_hash", ["", "z" * 64, "A" * 64])
def test_adapter_rejects_invalid_source_hash(bad_hash):
    gate = SimpleNamespace(gate_id="A_read_only", held=True, evidence="unchanged")
    with pytest.raises(ValueError, match="source_graph_hash"):
        adapt_legacy_gate(
            gate,
            source_graph_id="legacy-isr-1",
            source_graph_hash=bad_hash,
            consumer_binding="legacy-backend@1",
        )
