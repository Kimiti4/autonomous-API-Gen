"""Generalization integrity gate contract tests.

Proves the three-state verdict semantics of
``check_generalization_integrity``: PASS only on complete, distinct,
executed evidence from both trials; BLOCKED when a precondition is missing;
FAIL whenever integrity is violated (fabrication markers, isolation
denials, oracle leakage, pin drift, identical output, unexecuted
acceptance criteria). The gate is the certification record for the second
specification, so its own honesty is itself under test.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

GATE_PATH = (
    Path(__file__).resolve().parent.parent
    / "experiments"
    / "taskflow-native"
    / "check_generalization_integrity.py"
)


def _load_gate():
    spec = importlib.util.spec_from_file_location(
        "generalization_integrity_gate_for_tests", GATE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _load_gate()

CLEAN_RUNNER = "def _clean():\n    return None\n"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _make_trial(
    root: Path,
    name: str,
    statement: str,
    isr_hash: str,
    *,
    ac_count: int = 10,
    runner_source: str | None = None,
    acs_kwargs: dict | None = None,
    isolation_overrides: dict | None = None,
    manifest_files: dict | str | None = None,
    pin_sha: str | None = None,
) -> Path:
    trial = root / name
    evidence = trial / "out" / "evidence"
    evidence.mkdir(parents=True)

    problem = trial / "PROBLEM.md"
    problem.write_text(statement, encoding="utf-8")
    acceptance = {
        "acceptance_criteria": [
            {
                "id": f"AC-{index:02d}",
                "statement": f"criterion {index}",
                "evidence_key": f"AC-{index:02d}",
            }
            for index in range(1, ac_count + 1)
        ]
    }
    (trial / "ACCEPTANCE.json").write_text(
        json.dumps(acceptance), encoding="utf-8"
    )
    contract = {
        "inputs": {
            "problem": {
                "path": "PROBLEM.md",
                "sha256": pin_sha or _sha256(problem),
            },
            "acceptance": {
                "path": "ACCEPTANCE.json",
                "sha256": _sha256(trial / "ACCEPTANCE.json"),
            },
        },
        "forbidden": ["golden-projects/taskflow/app/"],
        "evidence_dir": "out/evidence",
    }
    (trial / "TRIAL_CONTRACT.json").write_text(
        json.dumps(contract), encoding="utf-8"
    )

    if runner_source is not None:
        for filename in gate.RUNNER_FILES:
            (trial / filename).write_text(runner_source, encoding="utf-8")

    acs = {}
    for index in range(1, ac_count + 1):
        ac_id = f"AC-{index:02d}"
        acs[ac_id] = {"passed": True, "http_status": 200}
    if acs_kwargs:
        for ac_id, overrides in acs_kwargs.items():
            acs.setdefault(ac_id, {"passed": True, "http_status": 200})
            acs[ac_id].update(overrides)

    _write(evidence / "isr_graph.json", {"isr_hash": isr_hash})
    _write(evidence / "run_results.json", {"completed": True})
    _write(evidence / "factory_summary.json", {"ok": True})
    _write(
        evidence / "e2e_results.json",
        {"reachable": True, "acs": acs},
    )
    isolation = {
        "violations": [],
        "denied_count": 0,
        "spawn": {"exit_code": 0},
        "workspace": {
            "files": manifest_files
            if isinstance(manifest_files, dict)
            else {"tiannara/main.py": "aa", "PROBLEM.md": "bb"}
        },
    }
    if isolation_overrides:
        isolation.update(isolation_overrides)
    _write(evidence / "isolation.json", isolation)
    return trial


def _pair(tmp_path: Path, **kwargs) -> tuple[Path, Path, Path]:
    kwargs.setdefault("runner_source", CLEAN_RUNNER)
    trial1 = _make_trial(
        tmp_path,
        "trial1",
        "# TaskFlow: organize personal and team work.",
        "a" * 64,
        **kwargs,
    )
    trial2 = _make_trial(
        tmp_path,
        "trial2",
        "# ExpenseLedger: keep spending accountable.",
        "b" * 64,
    )
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    return trial1, trial2, repo_root


# -- verdict semantics ---------------------------------------------------------


def test_gate_passes_on_complete_distinct_executed_evidence(tmp_path):
    trial1, trial2, repo_root = _pair(tmp_path, runner_source=CLEAN_RUNNER)
    verdict, checks = gate.evaluate_gate(trial1, trial2, repo_root)
    assert verdict == "PASS"
    assert {check["status"] for check in checks} == {"PASS"}


def test_gate_blocks_when_evidence_absent(tmp_path):
    trial1 = tmp_path / "trial1"
    trial2 = tmp_path / "trial2"
    trial1.mkdir()
    trial2.mkdir()
    verdict, checks = gate.evaluate_gate(trial1, trial2, tmp_path)
    assert verdict == "BLOCKED"
    by_id = {check["id"]: check for check in checks}
    assert by_id["runner-independent-interpretation"]["status"] == "BLOCKED"
    assert by_id["distinct-specification"]["status"] == "BLOCKED"


def test_gate_blocks_when_second_trial_never_ran(tmp_path):
    trial1, _trial2_unused, repo_root = _pair(tmp_path)
    verdict, checks = gate.evaluate_gate(trial1, trial1 / "missing", repo_root)
    by_id = {check["id"]: check for check in checks}
    assert by_id["distinct-specification"]["status"] == "BLOCKED"
    assert by_id["trial-execution"]["status"] == "BLOCKED"
    assert verdict in {"BLOCKED", "FAIL"}


def test_gate_fails_on_fabrication_markers(tmp_path):
    for marker in ("RecordedModelProvider", "seed_transcript"):
        trial1, trial2, repo_root = _pair(
            tmp_path / marker.replace("_", "-"),
            runner_source=f"X = 1\n{marker}(statement)\n",
        )
        verdict, checks = gate.evaluate_gate(trial1, trial2, repo_root)
        by_id = {check["id"]: check for check in checks}
        assert verdict == "FAIL"
        assert by_id["runner-independent-interpretation"]["status"] == "FAIL"


def test_gate_fails_on_fixture_assignment_names(tmp_path):
    trial1, trial2, repo_root = _pair(
        tmp_path, runner_source="ELICITATION = {}\nEXTRACTION = {}\n"
    )
    verdict, checks = gate.evaluate_gate(trial1, trial2, repo_root)
    by_id = {check["id"]: check for check in checks}
    assert verdict == "FAIL"
    assert by_id["runner-independent-interpretation"]["status"] == "FAIL"


def test_gate_fails_on_identical_problem_statements(tmp_path):
    trial1, trial2, repo_root = _pair(tmp_path)
    trial2.joinpath("PROBLEM.md").write_bytes(
        trial1.joinpath("PROBLEM.md").read_bytes()
    )
    verdict, checks = gate.evaluate_gate(trial1, trial2, repo_root)
    by_id = {check["id"]: check for check in checks}
    assert verdict == "FAIL"
    assert by_id["distinct-specification"]["status"] == "FAIL"


def test_gate_fails_on_identical_isr_output(tmp_path):
    trial1, trial2, repo_root = _pair(tmp_path)
    _write(
        trial2 / "out" / "evidence" / "isr_graph.json",
        {"isr_hash": "a" * 64},
    )
    verdict, checks = gate.evaluate_gate(trial1, trial2, repo_root)
    by_id = {check["id"]: check for check in checks}
    assert verdict == "FAIL"
    assert by_id["distinct-specification"]["status"] == "FAIL"


def test_gate_fails_on_isolation_denial(tmp_path):
    trial1, trial2, repo_root = _pair(tmp_path)
    _write(
        trial2 / "out" / "evidence" / "isolation.json",
        {
            "violations": [],
            "denied_count": 1,
            "denied": [{"event": "open", "path": "/etc/passwd"}],
            "spawn": {"exit_code": 0},
            "workspace": {"files": {"PROBLEM.md": "bb"}},
        },
    )
    verdict, checks = gate.evaluate_gate(trial1, trial2, repo_root)
    by_id = {check["id"]: check for check in checks}
    assert verdict == "FAIL"
    assert by_id["generation-boundary"]["status"] == "FAIL"


def test_gate_fails_on_forbidden_workspace_entry(tmp_path):
    trial1, trial2, repo_root = _pair(
        tmp_path,
        manifest_files={"tiannara/main.py": "aa", ".git/config": "cc"},
    )
    verdict, checks = gate.evaluate_gate(trial1, trial2, repo_root)
    by_id = {check["id"]: check for check in checks}
    assert verdict == "FAIL"
    assert by_id["generation-boundary"]["status"] == "FAIL"


def test_gate_fails_when_oracle_enters_workspace(tmp_path):
    trial1, trial2, repo_root = _pair(
        tmp_path,
        manifest_files={"PROBLEM.md": "bb", "ACCEPTANCE.json": "dd"},
    )
    verdict, checks = gate.evaluate_gate(trial1, trial2, repo_root)
    by_id = {check["id"]: check for check in checks}
    assert verdict == "FAIL"
    assert by_id["contract-pins-and-oracle-held-out"]["status"] == "FAIL"


def test_gate_fails_on_contract_pin_drift(tmp_path):
    trial1, trial2, repo_root = _pair(tmp_path, pin_sha="f" * 64)
    verdict, checks = gate.evaluate_gate(trial1, trial2, repo_root)
    by_id = {check["id"]: check for check in checks}
    assert verdict == "FAIL"
    assert by_id["contract-pins-and-oracle-held-out"]["status"] == "FAIL"


def test_gate_fails_on_unexecuted_or_failed_acceptance(tmp_path):
    trial1, trial2, repo_root = _pair(tmp_path)
    _write(
        trial2 / "out" / "evidence" / "e2e_results.json",
        {
            "reachable": True,
            "acs": {
                f"AC-{index:02d}": {"passed": True, "http_status": 200}
                for index in range(1, 9)
            },
        },
    )
    verdict, checks = gate.evaluate_gate(trial1, trial2, repo_root)
    by_id = {check["id"]: check for check in checks}
    assert verdict == "FAIL"
    assert by_id["trial-execution"]["status"] == "FAIL"

    _write(
        trial2 / "out" / "evidence" / "e2e_results.json",
        {
            "reachable": True,
            "acs": {
                **{
                    f"AC-{index:02d}": {
                        "passed": True,
                        "http_status": 200,
                    }
                    for index in range(1, 10)
                },
                "AC-10": {"passed": False, "http_status": 422},
            },
        },
    )
    verdict, checks = gate.evaluate_gate(trial1, trial2, repo_root)
    by_id = {check["id"]: check for check in checks}
    assert verdict == "FAIL"
    assert by_id["trial-execution"]["status"] == "FAIL"


def test_gate_fails_on_missing_http_execution_evidence(tmp_path):
    trial1, trial2, repo_root = _pair(tmp_path)
    _write(
        trial2 / "out" / "evidence" / "e2e_results.json",
        {
            "reachable": True,
            "acs": {
                f"AC-{index:02d}": {
                    "passed": True,
                    "http_status": None if index == 1 else 200,
                }
                for index in range(1, 11)
            },
        },
    )
    verdict, checks = gate.evaluate_gate(trial1, trial2, repo_root)
    by_id = {check["id"]: check for check in checks}
    assert verdict == "FAIL"
    assert by_id["trial-execution"]["status"] == "FAIL"


def test_gate_fails_when_forbidden_input_present(tmp_path):
    trial1, trial2, repo_root = _pair(tmp_path)
    forbidden = repo_root / "golden-projects" / "taskflow" / "app"
    forbidden.mkdir(parents=True)
    verdict, checks = gate.evaluate_gate(trial1, trial2, repo_root)
    by_id = {check["id"]: check for check in checks}
    assert verdict == "FAIL"
    assert by_id["forbidden-inputs-absent"]["status"] == "FAIL"


# -- main() exit codes ---------------------------------------------------------


def test_main_exit_codes_map_three_states(tmp_path, monkeypatch):
    trial1, trial2, repo_root = _pair(tmp_path)
    report = tmp_path / "report.json"
    monkeypatch.setattr(gate, "TRIAL1", trial1)
    monkeypatch.setattr(gate, "TRIAL2", trial2)
    monkeypatch.setattr(gate, "REPO_ROOT", repo_root)
    monkeypatch.setattr(gate, "REPORT", report)

    assert gate.main() == 0
    assert json.loads(report.read_text(encoding="utf-8"))["verdict"] == "PASS"

    _write(
        trial2 / "out" / "evidence" / "isolation.json",
        {"violations": [], "denied_count": 2, "spawn": {"exit_code": 0},
         "workspace": {"files": {}}},
    )
    assert gate.main() == 1
    assert json.loads(report.read_text(encoding="utf-8"))["verdict"] == "FAIL"

    _write(
        trial2 / "out" / "evidence" / "isolation.json",
        {
            "violations": [],
            "denied_count": 0,
            "spawn": {"exit_code": 0},
            "workspace": {"files": {"PROBLEM.md": "bb"}},
        },
    )
    (trial2 / "out" / "evidence" / "run_results.json").unlink()
    assert gate.main() == 2
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["verdict"] == "BLOCKED"
    assert payload["schema"] == "tiannara.generalization-integrity.v2"
