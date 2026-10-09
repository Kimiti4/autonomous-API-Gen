"""TASKFLOW-ESAP-NATIVE-001 trial harness contract tests.

Covers the trial's binding contract and its two gate scripts without running
the heavyweight pipeline (the CI workflow runs ``run_trial.py`` for real):

  * contract pins over the permitted inputs (PROBLEM.md / ACCEPTANCE.json),
    the six required family backends, and the PASS/FAILED/BLOCKED codes;
  * the technology-token scanner on the problem statement;
  * ``evaluate`` verdict semantics: PASS only on a complete consistent
    evidence set, FAILED on tampered/simulated/unevaluated evidence,
    BLOCKED when the trial never produced an output directory;
  * ``run_trial`` preconditions (missing contract, pin mismatch, token hit)
    and the seed-transcript -> ISR -> six-family derivation mapping;
  * the BuildProfileExecutionEnvironment fail-closed honesty contract.
"""
from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
TRIAL_DIR = REPO_ROOT / "experiments" / "taskflow-native"
PROBLEM_PATH = TRIAL_DIR / "PROBLEM.md"
CONTRACT_PATH = TRIAL_DIR / "TRIAL_CONTRACT.json"
ACCEPTANCE_PATH = REPO_ROOT / "golden-projects" / "taskflow" / "ACCEPTANCE.json"

EVIDENCE_SCHEMA = "taskflow.trial.evidence.v1"


def _load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_trial = _load_script("taskflow_run_trial", TRIAL_DIR / "run_trial.py")
evaluate_mod = _load_script("taskflow_evaluate", TRIAL_DIR / "evaluate.py")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _make_trial(tmp_path: Path, problem_text: str | None = None) -> Path:
    """Mirror the repository layout so the contract's relative paths resolve."""
    trial = tmp_path / "experiments" / "taskflow-native"
    trial.mkdir(parents=True)
    golden = tmp_path / "golden-projects" / "taskflow"
    golden.mkdir(parents=True)
    shutil.copy(ACCEPTANCE_PATH, golden / "ACCEPTANCE.json")

    problem = trial / "PROBLEM.md"
    text = problem_text if problem_text is not None else PROBLEM_PATH.read_text(
        encoding="utf-8"
    )
    problem.write_text(text, encoding="utf-8")

    contract = _contract()
    contract["inputs"]["problem"]["sha256"] = _sha256(problem)
    contract["inputs"]["acceptance"]["sha256"] = _sha256(
        golden / "ACCEPTANCE.json"
    )
    (trial / "TRIAL_CONTRACT.json").write_text(
        json.dumps(contract, indent=2) + "\n", encoding="utf-8"
    )
    return trial


def _structural_files() -> dict[str, str]:
    return {
        "svc/main.py": "def create_app():\n    return None\n",
        "svc/tests/test_api.py": "def test_ok():\n    assert True\n",
        "svc/frontend/app.js": "export const app = 1;\n",
        "svc/frontend/tests/app.test.mjs": "import test from 'node:test';\n",
        "svc/migrations/apply.py": "def apply():\n    return []\n",
        "svc/migrations/0001_init.sql": "CREATE TABLE tasks (id TEXT);\n",
        "svc/infra/topology.json": "{}\n",
        "svc/deploy/plan.py": "def plan():\n    return []\n",
        "svc/docs/validate_docs.py": "def main():\n    return 0\n",
    }


def _write_full_pass_evidence(trial: Path) -> dict:
    """Fabricate a complete, self-consistent evidence set (synthetic fixture)."""
    contract = _contract()
    evidence_dir = trial / "out" / "evidence"
    repo = trial / "out" / "repo"
    evidence_dir.mkdir(parents=True)
    repo.mkdir(parents=True)

    manifest_files: dict[str, str] = {}
    for rel, content in _structural_files().items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        manifest_files[rel] = _sha256(path)

    acceptance = json.loads(ACCEPTANCE_PATH.read_text(encoding="utf-8"))
    ac_ids = [entry["id"] for entry in acceptance["acceptance_criteria"]]
    acs = {
        ac_id: {
            "passed": True,
            "http_status": 200,
            "request": "GET /tasks",
            "response_excerpt": '{"ok": true}',
        }
        for ac_id in ac_ids
    }
    required = contract["required_backends"]
    bundles = [
        {
            "backend_id": backend_id,
            "static_ok": True,
            "ok": True,
            "repair_attempts": 0,
            "test": {
                "evaluated": True,
                "passed": True,
                "exit_code": 0,
                "duration_seconds": 0.1,
                "logs_path": None,
            },
        }
        for backend_id in required
    ]
    isr_hash = hashlib.sha256(b"synthetic-isr").hexdigest()

    def write(name: str, payload: dict) -> None:
        payload = dict(payload, evidence_schema=EVIDENCE_SCHEMA)
        (evidence_dir / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    write(
        "run_meta.json",
        {
            "task_id": contract["task_id"],
            "contract_sha256": _sha256(trial / "TRIAL_CONTRACT.json"),
            "permitted_input_hashes": {
                name: _sha256((trial / spec["path"]).resolve())
                for name, spec in contract["inputs"].items()
            },
        },
    )
    write(
        "isr_graph.json",
        {"isr_hash": isr_hash, "system_name": "svc"},
    )
    write(
        "factory_summary.json",
        {
            "ok": True,
            "isr_hash": isr_hash,
            "bundles": bundles,
            "repair_attempts_total": 0,
        },
    )
    write(
        "e2e_results.json",
        {
            "reachable": True,
            "acs": acs,
            "node_smoke": {"exit": 0, "ok": True, "output_tail": ""},
        },
    )
    write(
        "manifest.json",
        {"root": "repo", "file_count": len(manifest_files), "files": manifest_files},
    )
    write("run_results.json", {"completed": True, "system_name": "svc"})
    return {"evidence_dir": evidence_dir, "repo": repo, "ac_ids": ac_ids}


def _edit_evidence(evidence_dir: Path, name: str, mutate) -> None:
    path = evidence_dir / name
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


class _FakeProfile:
    def __init__(
        self,
        test_command: list[str] | None,
        build_command: list[str] | None = None,
        requires_build_phase: bool = False,
    ) -> None:
        self.test_command = test_command
        self.build_command = build_command
        self.requires_build_phase = requires_build_phase


class _FakeBackend:
    def __init__(self, profile: _FakeProfile) -> None:
        self._profile = profile

    def build_profile(self, project_id: str) -> _FakeProfile:
        return self._profile


class _FakeRegistry:
    def __init__(self, backend: _FakeBackend | None = None) -> None:
        self._backend = backend

    def backend(self, backend_id: str):
        if self._backend is None:
            raise KeyError(backend_id)
        return self._backend


# -- contract ----------------------------------------------------------------


def test_contract_pins_match_permitted_inputs_on_disk():
    contract = _contract()
    for name, spec in contract["inputs"].items():
        path = (TRIAL_DIR / spec["path"]).resolve()
        assert path.is_file(), f"{name}: {path} missing"
        assert _sha256(path) == spec["sha256"], f"{name} pin drifted"


def test_contract_requires_all_six_families_and_gate_codes():
    contract = _contract()
    assert contract["task_id"] == "TASKFLOW-ESAP-NATIVE-001"
    assert contract["mode"] == "blind-generation"
    assert sorted(contract["required_backends"]) == sorted(
        [
            "fastapi_hexagonal",
            "static_spa_frontend",
            "sql_migrations",
            "container_stack",
            "rolling_deploy",
            "traceability_docs",
        ]
    )
    assert contract["exit_codes"] == {"PASS": 0, "FAILED": 1, "BLOCKED": 2}
    assert contract["evidence_schema"] == EVIDENCE_SCHEMA
    assert contract["max_repair_attempts"] == 3
    assert any("app/" in entry for entry in contract["forbidden"])


def test_problem_statement_is_technology_free():
    text = PROBLEM_PATH.read_text(encoding="utf-8")
    assert evaluate_mod.scan_text_tokens(text) == []
    poisoned = "The service stores rows in postgres behind docker."
    assert "postgres" in evaluate_mod.scan_text_tokens(poisoned)
    assert "docker" in evaluate_mod.scan_text_tokens(poisoned)


def test_trial_scripts_never_reference_forbidden_inputs():
    for script in ("run_trial.py", "evaluate.py"):
        source = (TRIAL_DIR / script).read_text(encoding="utf-8")
        assert "ARCHITECTURE" not in source
        assert "taskflow/app" not in source


# -- run_trial preconditions -------------------------------------------------


def test_run_trial_blocks_without_contract(tmp_path):
    assert run_trial.run_trial(tmp_path) == 2


def test_run_trial_fails_on_pin_mismatch(tmp_path, capsys):
    trial = _make_trial(tmp_path)
    contract = _contract()
    contract["inputs"]["problem"]["sha256"] = "0" * 64
    (trial / "TRIAL_CONTRACT.json").write_text(
        json.dumps(contract), encoding="utf-8"
    )
    assert run_trial.run_trial(trial) == 1
    assert "pin mismatch" in capsys.readouterr().out


def test_run_trial_fails_on_technology_tokens(tmp_path, capsys):
    trial = _make_trial(
        tmp_path, problem_text="TaskFlow keeps data in postgres for now.\n"
    )
    assert run_trial.run_trial(trial) == 1
    assert "technology tokens" in capsys.readouterr().out


def test_bundle_slug_maps_isr_name_to_package_name():
    assert (
        run_trial._bundle_slug("taskflow-organize-personal-and-team-work")
        == "taskflow_organize_personal_and_team_work"
    )
    assert run_trial._bundle_slug("") == ""


# -- seed -> ISR -> six families ---------------------------------------------


def _compiled_isr_model(tmp_path: Path):
    statement = PROBLEM_PATH.read_text(encoding="utf-8")
    transcript = run_trial.seed_transcript(statement, tmp_path / "transcript.jsonl")

    from tiannara.application.intent import derive_system_id
    from tiannara.application.intent.compiler import IntentCompiler
    from tiannara.infrastructure.llm.recorded_provider import RecordedModelProvider
    from tiannara.infrastructure.llm.transcript import ModelCallTranscript

    provider = RecordedModelProvider(ModelCallTranscript(transcript))
    return IntentCompiler(provider).compile_full(
        statement, derive_system_id(statement)
    )


def test_seed_transcript_maps_to_isr_models(tmp_path):
    result = _compiled_isr_model(tmp_path)
    model = result.isr.system_model()
    assert model is not None

    model_names = sorted(dm.name.lower() for dm in model.data_models)
    assert model_names == ["task", "task_list"]
    field_names = {
        field.name for dm in model.data_models for field in dm.fields
    }
    assert {"title", "notes", "status", "priority", "due_date", "list_id"} <= field_names
    assert len(model.services) >= 3
    assert model.capabilities

    seed_path = tmp_path / "transcript.jsonl"
    records = [
        json.loads(line)
        for line in seed_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 2


def test_seed_drives_all_six_required_families(tmp_path):
    from tiannara.application.compiler.composition import build_compiler_registry
    from tiannara.application.compiler.derivation import (
        derive_compilation_requirements,
    )
    from tiannara.application.compiler.selector import plan_compilation

    model = _compiled_isr_model(tmp_path).isr.system_model()
    requirements = derive_compilation_requirements(model)
    assert len(requirements) == 6

    plan = plan_compilation(build_compiler_registry(), requirements)
    planned = {entry.backend_id for entry in plan.planned}
    assert planned == set(_contract()["required_backends"])
    assert plan.planned[0].backend_id == "fastapi_hexagonal"


# -- evaluator verdict semantics ---------------------------------------------


def test_evaluator_passes_on_complete_consistent_evidence(tmp_path):
    trial = _make_trial(tmp_path)
    _write_full_pass_evidence(trial)
    verdict, checks = evaluate_mod.evaluate(trial)
    failed = [c["name"] for c in checks if not c["ok"]]
    assert failed == []
    assert verdict == 0


def test_evaluator_fails_on_tampered_manifest_file(tmp_path):
    trial = _make_trial(tmp_path)
    fixture = _write_full_pass_evidence(trial)
    target = fixture["repo"] / "svc" / "main.py"
    target.write_text(target.read_text(encoding="utf-8") + "# tampered\n",
                      encoding="utf-8")
    verdict, checks = evaluate_mod.evaluate(trial)
    assert verdict == 1
    failed = {c["name"] for c in checks if not c["ok"]}
    assert "manifest-hashes-match-disk" in failed


def test_evaluator_rejects_simulated_acceptance_evidence(tmp_path):
    trial = _make_trial(tmp_path)
    fixture = _write_full_pass_evidence(trial)

    def strip_excerpt(payload):
        del payload["acs"]["AC-01"]["response_excerpt"]
        payload["acs"]["AC-01"]["http_status"] = None

    _edit_evidence(fixture["evidence_dir"], "e2e_results.json", strip_excerpt)
    verdict, checks = evaluate_mod.evaluate(trial)
    assert verdict == 1
    failed = {c["name"] for c in checks if not c["ok"]}
    assert "acceptance-evidence" in failed


def test_evaluator_fails_unevaluated_runtime_stage(tmp_path):
    trial = _make_trial(tmp_path)
    fixture = _write_full_pass_evidence(trial)

    def unevaluate(payload):
        payload["bundles"][0]["test"]["evaluated"] = False
        payload["bundles"][0]["test"]["passed"] = False

    _edit_evidence(fixture["evidence_dir"], "factory_summary.json", unevaluate)
    verdict, checks = evaluate_mod.evaluate(trial)
    assert verdict == 1
    failed = {c["name"] for c in checks if not c["ok"]}
    assert "factory-bundles-pass" in failed


def test_evaluator_fails_missing_evidence_file(tmp_path):
    trial = _make_trial(tmp_path)
    fixture = _write_full_pass_evidence(trial)
    (fixture["evidence_dir"] / "factory_summary.json").unlink()
    verdict, checks = evaluate_mod.evaluate(trial)
    assert verdict == 1
    failed = {c["name"] for c in checks if not c["ok"]}
    assert "evidence:factory_summary.json" in failed


def test_evaluator_fails_isr_hash_mismatch_between_graph_and_factory(tmp_path):
    trial = _make_trial(tmp_path)
    fixture = _write_full_pass_evidence(trial)

    def desync(payload):
        payload["isr_hash"] = hashlib.sha256(b"other-isr").hexdigest()

    _edit_evidence(fixture["evidence_dir"], "factory_summary.json", desync)
    verdict, checks = evaluate_mod.evaluate(trial)
    assert verdict == 1
    failed = {c["name"] for c in checks if not c["ok"]}
    assert "isr-hash-consistency" in failed


def test_evaluator_blocks_when_trial_never_ran(tmp_path):
    trial = _make_trial(tmp_path)
    verdict, checks = evaluate_mod.evaluate(trial)
    assert verdict == 2
    assert {c["name"] for c in checks} == {"trial-output-present"}


def test_evaluator_blocks_on_missing_contract(tmp_path):
    verdict, checks = evaluate_mod.evaluate(tmp_path)
    assert verdict == 2
    assert checks[0]["name"] == "contract-present"


# -- profile environment honesty contract ------------------------------------


def _run_verification(registry, bundle):
    from tiannara.infrastructure.sandbox.profile_environment import (
        BuildProfileExecutionEnvironment,
    )

    env = BuildProfileExecutionEnvironment(registry)
    return asyncio.run(env.run_verification(bundle))


def test_profile_environment_unevaluated_without_test_command(tmp_path):
    bundle = SimpleNamespace(backend_name="fake", project_id="svc",
                             path=str(tmp_path))
    env = _run_verification(_FakeRegistry(_FakeBackend(_FakeProfile(None))), bundle)
    assert env.evaluated is False
    assert env.passed is False
    assert env.exit_code == -1


def test_profile_environment_unevaluated_when_tool_absent(tmp_path):
    bundle = SimpleNamespace(backend_name="fake", project_id="svc",
                             path=str(tmp_path))
    profile = _FakeProfile(["definitely-not-a-real-tool-xyz"])
    env = _run_verification(_FakeRegistry(_FakeBackend(profile)), bundle)
    assert env.evaluated is False
    assert env.exit_code == -127


def test_profile_environment_unevaluated_for_unknown_backend(tmp_path):
    bundle = SimpleNamespace(backend_name="ghost", project_id="svc",
                             path=str(tmp_path))
    env = _run_verification(_FakeRegistry(None), bundle)
    assert env.evaluated is False


def test_profile_environment_fail_closed_on_build_failure(tmp_path):
    bundle = SimpleNamespace(backend_name="fake", project_id="svc",
                             path=str(tmp_path))
    profile = _FakeProfile(
        test_command=["python", "-c", "pass"],
        build_command=["python", "-c", "import sys; sys.exit(5)"],
        requires_build_phase=True,
    )
    env = _run_verification(_FakeRegistry(_FakeBackend(profile)), bundle)
    assert env.evaluated is True
    assert env.passed is False
    assert env.exit_code == 5


def test_profile_environment_reports_test_failure_honestly(tmp_path):
    bundle = SimpleNamespace(backend_name="fake", project_id="svc",
                             path=str(tmp_path))
    profile = _FakeProfile(["python", "-c", "import sys; sys.exit(7)"])
    env = _run_verification(_FakeRegistry(_FakeBackend(profile)), bundle)
    assert env.evaluated is True
    assert env.passed is False
    assert env.exit_code == 7
    assert env.logs_path is not None


def test_profile_environment_passes_when_tests_pass(tmp_path):
    bundle = SimpleNamespace(backend_name="fake", project_id="svc",
                             path=str(tmp_path))
    env = _run_verification(
        _FakeRegistry(_FakeBackend(_FakeProfile(["python", "-c", "pass"]))),
        bundle,
    )
    assert env.evaluated is True
    assert env.passed is True
    assert env.exit_code == 0
