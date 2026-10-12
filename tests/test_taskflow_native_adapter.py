import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
TRIAL_DIR = ROOT / "experiments" / "taskflow-native"
sys.path.insert(0, str(TRIAL_DIR))

from provider_free.native_adapter import adapt_taskflow_snapshot  # noqa: E402

PROBLEM = (TRIAL_DIR / "PROBLEM.md").read_text(encoding="utf-8")
ACCEPTANCE = json.loads((ROOT / "golden-projects/taskflow/ACCEPTANCE.json").read_text(encoding="utf-8"))


def test_native_adapter_builds_traceable_graph_but_blocks_generation():
    result = adapt_taskflow_snapshot(PROBLEM, ACCEPTANCE)
    report = result.as_dict()

    assert report["schema"] == "tiannara.taskflow.native-adapter.v1"
    assert report["network_calls"] == 0
    assert report["provider_required"] is False
    assert report["generation_allowed"] is False
    assert report["certified"] is False
    assert report["system_model"] is None
    assert report["typed_isr"] is None
    assert len(report["traceability"]["capabilities"]) == 11
    assert len(report["traceability"]["problem_obligations"]) == 15
    assert len(report["traceability"]["quality_gates"]) == 12
    assert len(report["traceability"]["negative_cases"]) == 8
    assert all(item["status"] == "UNKNOWN" for item in report["traceability"]["quality_gates"])
    assert all(item["status"] == "UNKNOWN" for item in report["traceability"]["negative_cases"])
    assert any("defaults" in blocker for blocker in report["blockers"])


def test_native_graph_has_stable_ids_hashes_and_source_provenance():
    first = adapt_taskflow_snapshot(PROBLEM, ACCEPTANCE)
    second = adapt_taskflow_snapshot(PROBLEM, ACCEPTANCE)

    assert first.graph.graph_id == second.graph.graph_id
    assert first.graph.content_hash() == second.graph.content_hash()
    assert [node.id for node in first.graph.nodes] == [node.id for node in second.graph.nodes]
    assert all(node.provenance.source != "unknown" for node in first.graph.nodes)
    assert all("Source:" in node.rationale for node in first.graph.nodes)


def test_explicit_obligation_mappings_create_graph_edges_not_pass_evidence():
    result = adapt_taskflow_snapshot(PROBLEM, ACCEPTANCE)
    mapped = [item for item in result.traceability["problem_obligations"] if item["mapping_status"] == "MAPPED"]

    assert len(mapped) == 15
    assert len(result.graph.edges) > 0
    assert all(item["verification_status"] == "UNKNOWN" for item in result.traceability["problem_obligations"])


def test_adapter_rejects_duplicate_capabilities():
    acceptance = dict(ACCEPTANCE)
    acceptance["required_capabilities"] = list(ACCEPTANCE["required_capabilities"]) + [ACCEPTANCE["required_capabilities"][0]]
    with pytest.raises(ValueError, match="duplicates"):
        adapt_taskflow_snapshot(PROBLEM, acceptance)


def test_adapter_rejects_malformed_quality_gate_contract():
    acceptance = dict(ACCEPTANCE)
    acceptance["quality_gates"] = {"security": "yes"}
    with pytest.raises(ValueError, match="boolean"):
        adapt_taskflow_snapshot(PROBLEM, acceptance)


def test_adapter_carries_authoritative_unresolved_semantic_ledger():
    result = adapt_taskflow_snapshot(PROBLEM, ACCEPTANCE)
    report = result.as_dict()
    ledger = report["semantic_resolution_record"]

    assert ledger["graph_id"] == report["requirement_graph"]["graph_id"]
    assert ledger["graph_hash"] == report["requirement_graph_sha256"]
    assert len(ledger["required_fields"]) == 15
    assert report["unresolved_mandatory_semantics"] == ledger["required_fields"]
    assert all(item["kind"] == "unresolved" for item in ledger["resolutions"])
    assert report["generation_allowed"] is False
