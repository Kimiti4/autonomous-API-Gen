"""ESAP-SECOND-SPEC-001 (ExpenseLedger) second-spec trial contract tests.

Covers the second blind trial's binding contract, its held-out acceptance
oracle, the interpretation contract of its PROBLEM.md against the generic
rule layer, and per-trial hook resolution -- without running the heavyweight
pipeline (the canonical run is ``run_trial.py --trial-dir
experiments/spec2-expensel``). Proves the pipeline generalizes beyond the
first specification with no trial-specific extraction logic.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

from tiannara.application.intent import normalize
from tiannara.application.intent.interpretation import (
    interpret_elicitation,
    interpret_extraction,
)

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
TRIAL1_DIR = REPO_ROOT / "experiments" / "taskflow-native"
TRIAL2_DIR = REPO_ROOT / "experiments" / "spec2-expensel"
PROBLEM_PATH = TRIAL2_DIR / "PROBLEM.md"
CONTRACT_PATH = TRIAL2_DIR / "TRIAL_CONTRACT.json"
ACCEPTANCE_PATH = TRIAL2_DIR / "ACCEPTANCE.json"
HOOKS_PATH = TRIAL2_DIR / "trial_hooks.py"

EVIDENCE_SCHEMA = "taskflow.trial.evidence.v1"
REQUIRED_BACKENDS = [
    "fastapi_hexagonal",
    "static_spa_frontend",
    "sql_migrations",
    "container_stack",
    "rolling_deploy",
    "traceability_docs",
]


def _load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_trial = _load_script("spec2_run_trial_for_tests", TRIAL1_DIR / "run_trial.py")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _acceptance() -> dict:
    return json.loads(ACCEPTANCE_PATH.read_text(encoding="utf-8"))


def _extraction():
    text = PROBLEM_PATH.read_text(encoding="utf-8")
    normalized = normalize(text)
    return interpret_extraction(normalized, interpret_elicitation(normalized))


# -- contract -----------------------------------------------------------------


def test_contract_pins_match_pinned_inputs():
    contract = _contract()
    assert contract["schema_id"] == "tiannara.trial.contract"
    assert contract["task_id"] == "ESAP-SECOND-SPEC-001"
    assert contract["mode"] == "blind-generation"
    assert contract["evidence_schema"] == EVIDENCE_SCHEMA
    assert contract["exit_codes"] == {"PASS": 0, "FAILED": 1, "BLOCKED": 2}
    assert contract["required_backends"] == REQUIRED_BACKENDS
    assert contract["max_repair_attempts"] == 3
    for spec in contract["inputs"].values():
        path = (TRIAL2_DIR / spec["path"]).resolve()
        assert path.is_file(), spec["path"]
        assert _sha256(path) == spec["sha256"], spec["path"]
    assert contract["inputs"]["acceptance"]["path"] == "ACCEPTANCE.json"


def test_problem_statement_is_technology_free():
    text = PROBLEM_PATH.read_text(encoding="utf-8")
    assert run_trial.scan_text_tokens(text) == []


def test_problem_statement_is_distinct_from_first_specification():
    trial1 = (TRIAL1_DIR / "PROBLEM.md").read_text(encoding="utf-8").lower()
    trial2 = PROBLEM_PATH.read_text(encoding="utf-8").lower()
    assert trial1 != trial2
    words1 = set(re.findall(r"[A-Za-z]{5,}", trial1))
    words2 = set(re.findall(r"[A-Za-z]{5,}", trial2))
    assert not {"task", "tasks", "priority", "priorities"} & words2
    assert not {"claim", "claims", "vendor", "vendors", "amount"} & words1
    assert "named lists" in trial1 and "named lists" not in trial2
    assert "named vendors" in trial2 and "named vendors" not in trial1


# -- interpretation contract ---------------------------------------------------


def test_interpretation_yields_expensel_models_from_generic_rules():
    extraction = _extraction()
    models = {model.name: model for model in extraction.data_models}
    assert set(models) == {"claim", "claim_vendor"}

    fields = {field.name: field for field in models["claim"].fields}
    assert set(fields) == {
        "vendor_id",
        "status",
        "category",
        "title",
        "notes",
        "amount",
        "expense_date",
    }
    assert fields["vendor_id"].type == "reference"
    assert not fields["vendor_id"].required
    assert fields["status"].type == "enumeration"
    assert fields["status"].enumeration_values == [
        "draft",
        "submitted",
        "approved",
        "rejected",
    ]
    assert fields["category"].type == "enumeration"
    assert fields["category"].enumeration_values == [
        "meals",
        "travel",
        "lodging",
        "supplies",
    ]
    assert fields["title"].type == "text" and fields["title"].required
    assert fields["notes"].type == "text" and not fields["notes"].required
    assert fields["amount"].type == "decimal" and fields["amount"].required
    assert fields["expense_date"].type == "timestamp"
    assert not fields["expense_date"].required
    assert "id" not in fields

    vendor_fields = {field.name: field for field in models["claim_vendor"].fields}
    assert set(vendor_fields) == {"name"}
    assert vendor_fields["name"].type == "text"
    assert vendor_fields["name"].required

    kinds = [node.kind for node in extraction.nodes]
    assert kinds.count("functional") >= 3
    assert kinds.count("constraint") >= 2
    assert kinds.count("data") >= 2
    assert all(node.acceptance_criteria == [] for node in extraction.nodes)
    assert all(
        node.rationale.startswith("derived from source text")
        for node in extraction.nodes
    )
    assert all(edge.rationale for edge in extraction.edges)
    assert models["claim"].owning_service_ref is not None
    assert models["claim"].requirement_refs


# -- held-out acceptance oracle ------------------------------------------------


def test_acceptance_oracle_structure_and_enum_parity():
    acceptance = _acceptance()
    assert acceptance["schema_id"] == "expenseledger.acceptance.v1"
    assert acceptance["system"] == "ExpenseLedger"
    assert acceptance["resource"] == "claim"
    assert acceptance["secondary_resource"] == "claim_vendor"

    entries = acceptance["acceptance_criteria"]
    ids = [entry.get("id", "") for entry in entries]
    assert len(entries) >= 10
    assert len(set(ids)) == len(ids)
    assert all(re.fullmatch(r"AC-\d{2}", ac_id) for ac_id in ids)
    assert all(
        entry.get("statement") and entry.get("evidence_key") == entry["id"]
        for entry in entries
    )

    fields = {
        field.name: field
        for model in _extraction().data_models
        if model.name == "claim"
        for field in model.fields
    }
    assert acceptance["statuses"] == fields["status"].enumeration_values
    assert acceptance["categories"] == fields["category"].enumeration_values


def test_hook_flow_records_every_acceptance_id():
    source = HOOKS_PATH.read_text(encoding="utf-8")
    recorded = set(re.findall(r'"(AC-\d{2})"', source))
    oracle_ids = {entry["id"] for entry in _acceptance()["acceptance_criteria"]}
    assert oracle_ids <= recorded


# -- per-trial hooks -----------------------------------------------------------


def test_hooks_resolve_per_trial_directory():
    hooks2 = run_trial.load_trial_hooks(TRIAL2_DIR)
    hooks1 = run_trial.load_trial_hooks(TRIAL1_DIR)
    assert hooks1["run_acceptance_flow"] is run_trial.run_acceptance_flow
    assert hooks1["run_node_smoke"] is run_trial.run_node_smoke
    assert hooks2["run_acceptance_flow"] is not run_trial.run_acceptance_flow
    assert hooks2["run_node_smoke"] is not run_trial.run_node_smoke
    assert callable(hooks2["run_acceptance_flow"])
    assert callable(hooks2["run_node_smoke"])
    assert hooks2["run_acceptance_flow"].__module__ == hooks2[
        "run_node_smoke"
    ].__module__


def test_spec2_hooks_never_reference_forbidden_inputs():
    source = HOOKS_PATH.read_text(encoding="utf-8")
    assert "ARCHITECTURE" not in source
    assert "taskflow/app" not in source
    assert "golden-projects" not in source
