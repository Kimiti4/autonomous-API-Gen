"""Tests for fail-closed TaskFlow cross-compiler parity preflight."""
import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "taskflow_input_parity.py"
spec = importlib.util.spec_from_file_location("taskflow_input_parity", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)
evaluate_input_parity = module.evaluate_input_parity


def valid_manifest():
    fields = {
        path: {
            "status": "RESOLVED",
            "semantic_value_sha256": "a" * 64,
            "consumer_binding": "reviewed-consumer:" + path,
        }
        for path in module.TASKFLOW_MANDATORY_FIELDS
    }
    return {
        "source_hashes": {
            "problem_sha256": "1" * 64,
            "acceptance_sha256": "2" * 64,
            "resolution_record_sha256": "3" * 64,
        },
        "compilers": [
            {"compiler_id": "A", "implementation_id": "impl-A", "fields": fields},
            {"compiler_id": "B", "implementation_id": "impl-B", "fields": fields.copy()},
        ],
    }


def test_matching_declarations_never_claim_qualification():
    report = evaluate_input_parity(valid_manifest())
    assert report["status"] == "PARITY_CLAIMS_MATCHED_REQUIRES_INDEPENDENT_VERIFICATION"
    assert report["mandatory_fields"] == 15
    assert report["generation_authorized"] is False
    assert report["compiler_pair_qualified"] is False


@pytest.mark.parametrize("hash_name", ["problem_sha256", "acceptance_sha256", "resolution_record_sha256"])
def test_missing_canonical_hash_blocks(hash_name):
    manifest = valid_manifest()
    manifest["source_hashes"][hash_name] = None
    report = evaluate_input_parity(manifest)
    assert report["status"] == "BLOCKED"
    assert any(hash_name in blocker for blocker in report["blockers"])


def test_missing_mandatory_semantic_blocks():
    manifest = valid_manifest()
    del manifest["compilers"][0]["fields"][module.TASKFLOW_MANDATORY_FIELDS[0]]
    report = evaluate_input_parity(manifest)
    assert report["status"] == "BLOCKED"
    assert any("missing mandatory field" in blocker for blocker in report["blockers"])


def test_unresolved_field_blocks_even_if_both_compilers_agree():
    manifest = valid_manifest()
    path = module.TASKFLOW_MANDATORY_FIELDS[1]
    for compiler in manifest["compilers"]:
        compiler["fields"][path]["status"] = "UNRESOLVED"
    report = evaluate_input_parity(manifest)
    assert report["status"] == "BLOCKED"
    assert any("field is not resolved" in blocker for blocker in report["blockers"])


def test_semantic_value_digest_mismatch_blocks():
    manifest = valid_manifest()
    path = module.TASKFLOW_MANDATORY_FIELDS[2]
    manifest["compilers"][1]["fields"][path]["semantic_value_sha256"] = "b" * 64
    report = evaluate_input_parity(manifest)
    assert report["status"] == "BLOCKED"
    assert any("semantic value digest mismatch" in blocker for blocker in report["blockers"])


def test_same_implementation_is_not_two_compilers():
    manifest = valid_manifest()
    manifest["compilers"][1]["implementation_id"] = manifest["compilers"][0]["implementation_id"]
    report = evaluate_input_parity(manifest)
    assert report["status"] == "BLOCKED"
    assert any("distinct implementations" in blocker for blocker in report["blockers"])


def test_missing_consumer_binding_blocks():
    manifest = valid_manifest()
    manifest["compilers"][0]["fields"][module.TASKFLOW_MANDATORY_FIELDS[3]]["consumer_binding"] = ""
    report = evaluate_input_parity(manifest)
    assert report["status"] == "BLOCKED"
    assert any("lacks downstream consumer binding" in blocker for blocker in report["blockers"])