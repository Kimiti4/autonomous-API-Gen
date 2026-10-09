"""Blind-input isolation contract tests for TASKFLOW-ESAP-NATIVE-001.

Covers Phase 3's boundary claims without running the full factory:

  * the generation workspace contains only pipeline source + the pinned
    statement (no version control, no golden project, no oracle);
  * workspace violations flag any forbidden content;
  * the audit hook denies reads, writes, listings, and external network use
    outside allowlisted roots (loopback self-verification stays allowed),
    records every denial, and allows workspace/runtime paths;
  * self-created scratch dirs become session roots while pre-existing temp
    files stay unreadable;
  * the stripped child environment carries no secrets;
  * empirical escape canaries in a real child process: a probe outside the
    boundary is denied and logged; a probe inside is allowed;
  * the ``compile`` phase runs inside the boundary end to end with zero
    denials, writes interpretation/graph evidence, and leaves no repo-root
    entry on ``sys.path``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
TRIAL_DIR = REPO_ROOT / "experiments" / "taskflow-native"


def _load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_trial = _load_script("taskflow_run_trial_for_isolation", TRIAL_DIR / "run_trial.py")
isolated_generation = _load_script(
    "taskflow_isolated_generation_for_isolation",
    TRIAL_DIR / "isolated_generation.py",
)


def _hook_for(root: Path):
    roots = [os.path.normcase(os.path.realpath(str(root)))]
    records: list = []
    sink = io.StringIO()
    return isolated_generation.build_audit_hook(roots, records, sink), records, sink


# -- workspace layout ---------------------------------------------------------


def test_workspace_contains_only_pipeline_source_and_statement(tmp_path):
    statement_bytes = b"# Demo statement\n\nThe system records demo entries.\n"
    workspace = run_trial.build_workspace(tmp_path / "out", statement_bytes)
    assert (workspace / "PROBLEM.md").read_bytes() == statement_bytes
    assert (workspace / "tiannara" / "__init__.py").is_file()
    assert (workspace / "tiannara" / "application" / "intent" / "__init__.py").is_file()
    assert sorted(p.name for p in workspace.iterdir()) == ["PROBLEM.md", "tiannara"]
    assert not (workspace / ".git").exists()
    assert not any(
        "__pycache__" in part for path in workspace.rglob("*") for part in path.parts
    )
    assert run_trial.workspace_violations(workspace) == []


def test_workspace_violations_flag_forbidden_content(tmp_path):
    workspace = tmp_path / "genws"
    (workspace / ".git").mkdir(parents=True)
    (workspace / "golden-projects" / "taskflow").mkdir(parents=True)
    (workspace / "ACCEPTANCE.json").write_text("{}", encoding="utf-8")
    (workspace / "oracle2.json").write_text("{}", encoding="utf-8")
    problems = run_trial.workspace_violations(workspace)
    assert any("version control" in problem for problem in problems)
    assert any("golden project" in problem for problem in problems)
    assert sum("oracle or acceptance" in problem for problem in problems) == 2


def test_workspace_manifest_hashes_the_pinned_statement(tmp_path):
    statement_bytes = (TRIAL_DIR / "PROBLEM.md").read_bytes()
    workspace = run_trial.build_workspace(tmp_path / "out", statement_bytes)
    manifest = run_trial.workspace_manifest(workspace)
    assert manifest["root"] == "genws"
    assert manifest["file_count"] > 100
    assert manifest["files"]["PROBLEM.md"] == hashlib.sha256(
        statement_bytes
    ).hexdigest()
    assert "tiannara/application/intent/interpretation/__init__.py" in manifest[
        "files"
    ]


# -- stripped child environment ------------------------------------------------


def test_child_env_is_stripped_of_secrets(monkeypatch, tmp_path):
    monkeypatch.setenv("ESAP_CANARY_SECRET", "canary-value")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws-canary")
    workspace = tmp_path / "genws"
    workspace.mkdir()
    env = run_trial.isolated_child_env(workspace)
    assert "ESAP_CANARY_SECRET" not in env
    assert "AWS_SECRET_ACCESS_KEY" not in env
    assert env["PYTHONPATH"] == str(workspace)
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"
    assert "PATH" in env


# -- audit hook contract -------------------------------------------------------


def test_audit_hook_denies_reads_writes_listings_and_network(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("secret", encoding="utf-8")
    outside_dir = tmp_path / "elsewhere"
    outside_dir.mkdir()
    (root / "inside.md").write_text("ok", encoding="utf-8")
    hook, records, _sink = _hook_for(root)

    import pytest

    for mode in ("r", "w", "a"):
        with pytest.raises(PermissionError):
            hook("open", (str(outside_file), mode, 0))
    with pytest.raises(PermissionError):
        hook("os.listdir", (str(outside_dir),))
    with pytest.raises(PermissionError):
        hook("os.scandir", (str(outside_dir),))
    with pytest.raises(PermissionError):
        hook("socket.getaddrinfo", ("example.com", 443))
    with pytest.raises(PermissionError):
        hook("socket.connect", (None, ("10.0.0.1", 80)))

    hook("open", (str(root / "inside.md"), "r", 0))
    hook("open", (None, "r", 0))
    hook("open", (4, "rb", 65536))
    hook("socket.getaddrinfo", ("127.0.0.1", 8080))
    hook("socket.getaddrinfo", ("localhost", 8080))
    hook("socket.connect", (None, ("127.0.0.1", 9336)))
    hook("socket.connect", (None, ("::1", 9336)))
    hook("os.fork", ())

    assert len(records) == 7
    assert {record["event"] for record in records} == {
        "open",
        "os.listdir",
        "os.scandir",
        "socket.getaddrinfo",
        "socket.connect",
    }


def test_audit_hook_records_every_denial_to_the_sink(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    outside_file = tmp_path / "canary.txt"
    outside_file.write_text("hunter2", encoding="utf-8")
    hook, records, sink = _hook_for(root)

    import pytest

    with pytest.raises(PermissionError):
        hook("open", (str(outside_file), "r", 0))

    assert len(records) == 1
    assert records[0]["event"] == "open"
    assert "canary.txt" in records[0]["path"]
    lines = [line for line in sink.getvalue().splitlines() if line]
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["event"] == "open"
    assert "hunter2" not in sink.getvalue()


def test_audit_hook_allows_workspace_and_runtime_roots(tmp_path):
    root = tmp_path / "ws"
    (root / "sub").mkdir(parents=True)
    hook, records, _sink = _hook_for(root)
    hook("open", (str(root / "sub" / "file.py"), "r", 0))
    hook("os.listdir", (str(root),))
    assert records == []


# -- self-created scratch space (session roots) --------------------------------


def test_session_tracking_reads_own_scratch_but_not_preexisting_temp():
    import shutil
    import tempfile

    preexisting = Path(tempfile.mkdtemp(prefix="esap-pre-"))
    own_scratch = None
    isolated_generation._install_tempfile_tracking()
    try:
        own_scratch = Path(tempfile.mkdtemp(prefix="esap-own-"))
        tracked = [
            os.path.realpath(entry)
            for entry in isolated_generation._SESSION_ROOTS
        ]
        assert os.path.realpath(str(own_scratch)) in tracked
        assert os.path.realpath(str(preexisting)) not in tracked

        before = list(isolated_generation._SESSION_ROOTS)
        isolated_generation._track_session_path(str(REPO_ROOT))
        assert isolated_generation._SESSION_ROOTS == before

        own_file = own_scratch / "bundle.py"
        own_file.write_text("staged", encoding="utf-8")
        pre_file = preexisting / "foreign.txt"
        pre_file.write_text("foreign", encoding="utf-8")

        roots = [os.path.normcase(os.path.realpath(str(REPO_ROOT / "nowhere")))]
        records: list = []
        sink = io.StringIO()
        hook = isolated_generation.build_audit_hook(
            roots,
            records,
            sink,
            write_roots=[os.path.normcase(os.path.realpath(tempfile.gettempdir()))],
            session_roots=isolated_generation._SESSION_ROOTS,
        )
        hook("open", (str(own_file), "r", 0))
        hook("os.scandir", (str(own_scratch),))
        assert records == []

        import pytest

        with pytest.raises(PermissionError):
            hook("open", (str(pre_file), "r", 0))
        with pytest.raises(PermissionError):
            hook("os.scandir", (str(preexisting),))
        assert len(records) == 2
    finally:
        isolated_generation._uninstall_tempfile_tracking()
        shutil.rmtree(preexisting, ignore_errors=True)
        if own_scratch is not None:
            shutil.rmtree(own_scratch, ignore_errors=True)


# -- empirical escape canaries in a real child process --------------------------


def test_selftest_probe_outside_boundary_is_denied(tmp_path):
    out_dir = tmp_path / "out"
    workspace = out_dir / "genws"
    workspace.mkdir(parents=True)
    canary = tmp_path / "canary.txt"
    canary.write_text("must-not-be-read", encoding="utf-8")

    proc = run_trial.run_isolated_generation(
        trial_dir=TRIAL_DIR,
        out_dir=out_dir,
        workspace=workspace,
        evidence_dir=out_dir / "evidence",
        repo_root=out_dir / "repo",
        statement_path=workspace / "PROBLEM.md",
        max_repair_attempts=3,
        phase="selftest-escape",
        probe_path=canary,
    )
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    evidence_dir = out_dir / "evidence"
    selftest = json.loads(
        (evidence_dir / "isolation_selftest.json").read_text(encoding="utf-8")
    )
    record = json.loads(
        (evidence_dir / "isolation_child.json").read_text(encoding="utf-8")
    )
    assert selftest["opened"] is False
    assert selftest["error"]
    assert record["phase"] == "selftest-escape"
    assert record["denied_count"] == 1
    assert record["denied"][0]["event"] == "open"
    assert "canary.txt" in record["denied"][0]["path"]
    denied_log = (evidence_dir / "isolation-denied.jsonl").read_text(encoding="utf-8")
    assert "must-not-be-read" not in denied_log
    child_text = (evidence_dir / "isolation_child.json").read_text(encoding="utf-8")
    assert "must-not-be-read" not in child_text


def test_selftest_probe_inside_boundary_is_allowed(tmp_path):
    out_dir = tmp_path / "out"
    workspace = out_dir / "genws"
    workspace.mkdir(parents=True)
    inside = workspace / "statement.txt"
    inside.write_text("readable", encoding="utf-8")

    proc = run_trial.run_isolated_generation(
        trial_dir=TRIAL_DIR,
        out_dir=out_dir,
        workspace=workspace,
        evidence_dir=out_dir / "evidence",
        repo_root=out_dir / "repo",
        statement_path=workspace / "PROBLEM.md",
        max_repair_attempts=3,
        phase="selftest-escape",
        probe_path=inside,
    )
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    evidence_dir = out_dir / "evidence"
    selftest = json.loads(
        (evidence_dir / "isolation_selftest.json").read_text(encoding="utf-8")
    )
    record = json.loads(
        (evidence_dir / "isolation_child.json").read_text(encoding="utf-8")
    )
    assert selftest["opened"] is True
    assert record["denied_count"] == 0
    assert record["denied"] == []


# -- compile phase inside the boundary ------------------------------------------


def test_compile_phase_runs_isolated_with_zero_denials(tmp_path):
    out_dir = tmp_path / "out"
    statement_bytes = (TRIAL_DIR / "PROBLEM.md").read_bytes()
    workspace = run_trial.build_workspace(out_dir, statement_bytes)
    assert run_trial.workspace_violations(workspace) == []

    proc = run_trial.run_isolated_generation(
        trial_dir=TRIAL_DIR,
        out_dir=out_dir,
        workspace=workspace,
        evidence_dir=out_dir / "evidence",
        repo_root=out_dir / "repo",
        statement_path=workspace / "PROBLEM.md",
        max_repair_attempts=3,
        phase="compile",
    )
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    evidence_dir = out_dir / "evidence"

    record = json.loads(
        (evidence_dir / "isolation_child.json").read_text(encoding="utf-8")
    )
    assert record["phase"] == "compile"
    assert record["denied_count"] == 0
    assert record["denied"] == []
    assert os.path.realpath(record["cwd"]) == os.path.realpath(str(workspace))
    assert record["statement_sha256"] == hashlib.sha256(statement_bytes).hexdigest()

    graph = json.loads((evidence_dir / "isr_graph.json").read_text(encoding="utf-8"))
    assert graph["node_count"] >= 1
    assert graph["isr_hash"]
    interpretation = json.loads(
        (evidence_dir / "interpretation.json").read_text(encoding="utf-8")
    )
    assert interpretation["provider_model"] == run_trial.INTERPRETER_MODEL_ID
    assert interpretation["calls"]
    assert not (evidence_dir / "factory_summary.json").exists()
    assert not (evidence_dir / "errors.json").exists()

    repo_root_real = os.path.normcase(os.path.realpath(str(REPO_ROOT)))
    roots = [
        os.path.normcase(os.path.realpath(entry))
        if entry not in ("", None)
        else None
        for entry in record["sys_path"]
    ]
    assert repo_root_real not in roots
    for entry in record["sys_path"]:
        if entry in ("", None):
            resolved = os.path.normcase(os.path.realpath(str(workspace)))
        else:
            resolved = os.path.normcase(os.path.realpath(entry))
        assert any(
            resolved == root or resolved.startswith(root + os.sep)
            for root in record["allowed_roots"]
        ), f"sys.path entry outside allowlist: {entry}"
