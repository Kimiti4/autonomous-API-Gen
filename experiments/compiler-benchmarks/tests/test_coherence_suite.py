"""Structural integrity tests for the ten-domain coherence benchmark suite."""
import json
from pathlib import Path

SUITE_PATH = Path(__file__).parents[1] / "coherence_suite.v1.json"
EXPECTED_IDS = {
    "taskflow", "booking", "commerce", "wallet-ledger", "telemetry-fleet",
    "realtime-collaboration", "legacy-repair", "production-incident",
    "multi-stack-equivalence", "enterprise-capstone",
}


def test_suite_has_exactly_the_ten_declared_domains():
    suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
    assert suite["schema_version"] == "tiannara.coherence-suite.v1"
    assert {app["application_id"] for app in suite["applications"]} == EXPECTED_IDS
    assert len(suite["applications"]) == 10


def test_every_domain_has_invariants_negative_cases_and_explicit_status():
    suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
    for app in suite["applications"]:
        assert app["focus"], app["application_id"]
        assert len(app["critical_invariants"]) >= 3, app["application_id"]
        assert len(app["negative_cases"]) >= 4, app["application_id"]
        assert app["status"], app["application_id"]


def test_protocol_forbids_fake_compiler_comparisons_and_simulated_certification():
    suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
    policy = suite["policy"]
    assert policy["iterations_per_application"] == 2
    assert policy["requires_two_distinct_end_to_end_compilers"] is True
    assert policy["same_frozen_input_for_both_compilers"] is True
    assert policy["independent_acceptance_evaluator"] is True
    assert policy["simulated_evidence_can_certify"] is False
    assert "UNKNOWN" in suite["status_vocabulary"]
    assert "BLOCKED" in suite["status_vocabulary"]


def test_unwritten_specs_are_not_misrepresented_as_generation_ready():
    suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
    by_id = {app["application_id"]: app for app in suite["applications"]}
    assert by_id["taskflow"]["canonical_problem"]
    assert by_id["taskflow"]["acceptance_criteria"]
    for app_id in EXPECTED_IDS - {"taskflow"}:
        app = by_id[app_id]
        assert app["canonical_problem"] is None
        assert app["acceptance_criteria"] is None
        assert app["status"] == "SPECIFICATION_REQUIRED"
    assert suite["execution_record"]["iterations"] == "NOT_RUN"
    assert suite["execution_record"]["certification"] == "NONE"
