"""TASKFLOW-ESAP-NATIVE-001 -- blind-generation trial runner.

Executes the first genuine blind-generation trial end to end, using only the
permitted inputs pinned by ``TRIAL_CONTRACT.json``:

  1. verify the contract's SHA-256 pins over PROBLEM.md / ACCEPTANCE.json;
  2. build a dedicated generation workspace (``out/genws``) containing only
     a copy of the pipeline source (``tiannara/``) and the pinned statement
     -- no version-control metadata, no golden project, no oracle;
  3. run the generation phase (interpret -> compile -> SoftwareFactory with
     static + runtime verification and bounded repair) inside an isolated
     child process whose audit-hook boundary denies every file or network
     access outside allowlisted roots and records each denial;
  4. fail the trial if the boundary recorded any denial or the workspace
     contains forbidden content;
  5. hash the materialized tree into a manifest;
  6. start the generated service for real and execute the acceptance flow
     over HTTP (stdlib), plus the generated frontend smoke;
  7. write evidence under ``out/evidence/`` for the evaluator gate.

Exit codes: 0 pipeline completed, 1 pipeline failed (evidence still
written), 2 blocked (environment or contract preconditions unmet).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import http.client
import time
import urllib.parse
from pathlib import Path

TRIAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = TRIAL_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(TRIAL_DIR) not in sys.path:
    sys.path.insert(0, str(TRIAL_DIR))

import generationlib  # noqa: E402

EVIDENCE_SCHEMA = generationlib.EVIDENCE_SCHEMA
INTERPRETER_MODEL_ID = generationlib.INTERPRETER_MODEL_ID
_interpreter_config = generationlib._interpreter_config
_interpreter_provider = generationlib._interpreter_provider
compile_for_graph_evidence = generationlib.compile_for_graph_evidence


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_contract(trial_dir: Path) -> dict:
    return json.loads((trial_dir / "TRIAL_CONTRACT.json").read_text(encoding="utf-8"))


def scan_text_tokens(text: str) -> list[str]:
    from tiannara.domain.models.system_model import TECHNOLOGY_TOKENS

    hits = []
    for token in TECHNOLOGY_TOKENS:
        if re.search(rf"\b{re.escape(token)}\b", text, re.IGNORECASE):
            hits.append(token)
    return hits


def verify_contract_pins(contract: dict, trial_dir: Path) -> list[str]:
    problems = []
    for spec in contract.get("inputs", {}).values():
        path = (trial_dir / spec["path"]).resolve()
        if not path.is_file():
            problems.append(f"missing contract input: {spec['path']}")
            continue
        actual = sha256_file(path)
        if actual != spec["sha256"]:
            problems.append(
                f"contract pin mismatch for {spec['path']}: "
                f"expected {spec['sha256']}, got {actual}"
            )
    return problems


def environment_blockers() -> list[str]:
    blockers = []
    if shutil.which("node") is None:
        blockers.append("node is not on PATH")
    for module in ("uvicorn", "fastapi", "pytest"):
        try:
            __import__(module)
        except ImportError:
            blockers.append(f"python module unavailable: {module}")
    return blockers


WORKSPACE_IGNORE_PATTERNS = ("__pycache__", "*.pyc", "*.pyo", ".pytest_cache")


def build_workspace(out_dir: Path, statement_bytes: bytes) -> Path:
    workspace = out_dir / "genws"
    if workspace.exists():
        shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True)
    shutil.copytree(
        REPO_ROOT / "tiannara",
        workspace / "tiannara",
        ignore=shutil.ignore_patterns(*WORKSPACE_IGNORE_PATTERNS),
    )
    (workspace / "PROBLEM.md").write_bytes(statement_bytes)
    return workspace


def workspace_violations(workspace: Path) -> list[str]:
    problems = []
    for path in workspace.rglob("*"):
        rel = path.relative_to(workspace).as_posix()
        parts = rel.lower().split("/")
        if ".git" in parts:
            problems.append(f"version control metadata present: {rel}")
        if "golden-projects" in parts:
            problems.append(f"golden project content present: {rel}")
        if parts[-1] == "acceptance.json" or parts[-1].startswith("oracle"):
            problems.append(f"oracle or acceptance content present: {rel}")
    return problems


def workspace_manifest(workspace: Path) -> dict:
    files: dict[str, str] = {}
    for path in sorted(workspace.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(workspace).as_posix()
        if "__pycache__" in rel.split("/") or path.suffix in (".pyc", ".pyo"):
            continue
        files[rel] = sha256_file(path)
    return {"root": workspace.name, "file_count": len(files), "files": files}


def isolated_child_env(workspace: Path) -> dict[str, str]:
    keep = (
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "USERNAME",
        "HOMEDRIVE",
        "HOMEPATH",
        "APPDATA",
        "LOCALAPPDATA",
        "HOME",
        "LANG",
        "LC_ALL",
        "LD_LIBRARY_PATH",
    )
    env = {key: os.environ[key] for key in keep if key in os.environ}
    env["PYTHONPATH"] = str(workspace)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_isolated_generation(
    trial_dir: Path,
    out_dir: Path,
    workspace: Path,
    evidence_dir: Path,
    repo_root: Path,
    statement_path: Path,
    max_repair_attempts: int,
    phase: str = "generate",
    probe_path: Path | None = None,
) -> subprocess.CompletedProcess:
    command = [
        sys.executable,
        "-u",
        str(TRIAL_DIR / "isolated_generation.py"),
        "--phase",
        phase,
        "--workspace",
        str(workspace),
        "--out-root",
        str(out_dir),
        "--evidence-dir",
        str(evidence_dir),
        "--repo-root",
        str(repo_root),
        "--statement",
        str(statement_path),
        "--max-repair",
        str(max_repair_attempts),
    ]
    if probe_path is not None:
        command.extend(["--probe-path", str(probe_path)])
    return subprocess.run(
        command,
        cwd=str(workspace),
        env=isolated_child_env(workspace),
        capture_output=True,
        text=True,
        timeout=1800,
    )


def _load_json_safe(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None


def write_manifest(repo_root: Path) -> dict:
    files: dict[str, str] = {}
    for path in sorted(repo_root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(repo_root).as_posix()
        parts = rel.split("/")
        if ".git" in parts or "__pycache__" in parts or ".pytest_cache" in parts:
            continue
        if path.suffix in (".pyc", ".pyo"):
            continue
        files[rel] = sha256_file(path)
    return {
        "evidence_schema": EVIDENCE_SCHEMA,
        "root": repo_root.name,
        "file_count": len(files),
        "files": files,
    }


def _http(method: str, url: str, payload=None, key: str | None = None):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["X-API-Key"] = key
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    parsed = urllib.parse.urlsplit(url)
    connection = http.client.HTTPConnection(
        parsed.hostname, parsed.port, timeout=15
    )
    try:
        connection.request(
            method, parsed.path or "/", body=data, headers=headers
        )
        response = connection.getresponse()
        return response.status, response.read().decode("utf-8", "replace")
    finally:
        connection.close()


def _wait_for_health(base: str, attempts: int = 90) -> bool:
    for _ in range(attempts):
        try:
            status, _body = _http("GET", f"{base}/health")
            if status == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _record_ac(acs: dict, ac_id: str, request_desc: str, status, body, passed):
    acs[ac_id] = {
        "passed": bool(passed),
        "http_status": int(status) if isinstance(status, int) else None,
        "request": request_desc,
        "response_excerpt": (body or "")[:600],
    }


def run_acceptance_flow(base: str, api_key: str) -> dict:
    acs: dict[str, dict] = {}
    resource = "tasks"
    task_payload = {
        "title": "Write the field report",
        "notes": "first draft",
        "status": "open",
        "priority": "high",
        "due_date": "2026-10-20T00:00:00",
    }

    status, body = _http("GET", f"{base}/health")
    _record_ac(acs, "AC-07", "GET /health", status, body, status == 200 and "ok" in body)

    status, body = _http("GET", f"{base}/{resource}")
    _record_ac(acs, "AC-06", f"GET /{resource} without key", status, body, status == 401)

    status, body = _http("POST", f"{base}/{resource}", task_payload, api_key)
    created = json.loads(body) if body else {}
    task_id = created.get("id")
    created_ok = (
        status == 201
        and bool(task_id)
        and created.get("title") == task_payload["title"]
        and created.get("priority") == "high"
        and created.get("status") == "open"
        and "2026-10-20" in json.dumps(created)
    )
    _record_ac(acs, "AC-01", f"POST /{resource}", status, body, created_ok)

    status, body = _http("GET", f"{base}/{resource}", key=api_key)
    listed = json.loads(body) if body else []
    list_ok = status == 200 and isinstance(listed, list) and any(
        entry.get("id") == task_id for entry in listed
    )
    _record_ac(acs, "AC-02", f"GET /{resource}", status, body, list_ok)

    status, body = _http("GET", f"{base}/{resource}/{task_id}", key=api_key)
    fetched = json.loads(body) if body else {}
    get_ok = status == 200 and fetched.get("id") == task_id and fetched == created
    _record_ac(acs, "AC-03", f"GET /{resource}/{{id}}", status, body, get_ok)

    done_payload = dict(task_payload, status="done")
    status_done, body_done = _http(
        "PUT", f"{base}/{resource}/{task_id}", done_payload, api_key
    )
    open_payload = dict(task_payload, status="open")
    status_open, body_open = _http(
        "PUT", f"{base}/{resource}/{task_id}", open_payload, api_key
    )
    reopened = json.loads(body_open) if body_open else {}
    put_ok = (
        status_done == 200
        and (json.loads(body_done) if body_done else {}).get("status") == "done"
        and status_open == 200
        and reopened.get("status") == "open"
    )
    _record_ac(
        acs,
        "AC-04",
        f"PUT /{resource}/{{id}} done then open",
        status_open,
        body_done + body_open,
        put_ok,
    )

    status, body = _http("GET", f"{base}/{resource}/{task_id}", key=api_key)
    after = json.loads(body) if body else {}
    retained = (
        status == 200
        and after.get("priority") == "high"
        and "2026-10-20" in json.dumps(after)
    )
    _record_ac(acs, "AC-09", f"GET /{resource}/{{id}} after updates", status, body, retained)

    minimal = {"title": "No date yet", "status": "open", "priority": "low"}
    status, body = _http("POST", f"{base}/{resource}", minimal, api_key)
    minimal_created = json.loads(body) if body else {}
    minimal_id = minimal_created.get("id")
    status2, body2 = _http("GET", f"{base}/{resource}/{minimal_id}", key=api_key)
    minimal_fetched = json.loads(body2) if body2 else {}
    minimal_ok = (
        status == 201
        and status2 == 200
        and minimal_fetched.get("due_date") in (None, "")
        and minimal_fetched.get("notes") in (None, "")
    )
    _record_ac(
        acs,
        "AC-10",
        f"POST /{resource} without due date then GET",
        status2,
        body + body2,
        minimal_ok,
    )

    status, body = _http("POST", f"{base}/task_lists", {"name": "Field Work"}, api_key)
    task_list = json.loads(body) if body else {}
    list_id = task_list.get("id")
    in_list_payload = dict(task_payload, title="Pack the kit", list_id=list_id)
    status3, body3 = _http("POST", f"{base}/{resource}", in_list_payload, api_key)
    in_list = json.loads(body3) if body3 else {}
    in_list_id = in_list.get("id")
    status4, body4 = _http("GET", f"{base}/{resource}/{in_list_id}", key=api_key)
    fetched_in_list = json.loads(body4) if body4 else {}
    status5, body5 = _http("GET", f"{base}/task_lists", key=api_key)
    lists = json.loads(body5) if body5 else []
    membership_ok = (
        status == 201
        and bool(list_id)
        and status3 == 201
        and status4 == 200
        and fetched_in_list.get("list_id") == list_id
        and status5 == 200
        and any(entry.get("id") == list_id for entry in lists)
    )
    _record_ac(
        acs,
        "AC-08",
        "POST /task_lists + task with list_id + membership fetch",
        status5,
        body + body3 + body4 + body5,
        membership_ok,
    )

    status, body = _http("DELETE", f"{base}/{resource}/{task_id}", key=api_key)
    status_after, body_after = _http(
        "GET", f"{base}/{resource}/{task_id}", key=api_key
    )
    delete_ok = status == 204 and status_after == 404
    _record_ac(
        acs,
        "AC-05",
        f"DELETE /{resource}/{{id}} then GET",
        status_after,
        body + body_after,
        delete_ok,
    )

    return acs


def _bundle_slug(system_name: str) -> str:
    from tiannara.application.compiler.naming import slugify

    return slugify(system_name) if system_name else ""


def _run_node_smoke(
    repo_root: Path,
    slug: str,
    base: str,
    api_key: str,
    resource: str,
    payload: dict,
    changes: dict,
) -> dict:
    smoke_path = repo_root / slug / "frontend" / "smoke.mjs"
    command = [
        "node",
        str(smoke_path),
        "--base",
        base,
        "--key",
        api_key,
        "--resource",
        resource,
        "--payload",
        json.dumps(payload),
        "--changes",
        json.dumps(changes),
    ]
    proc = subprocess.run(
        command,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=180,
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    parsed_ok = None
    for candidate_text in (proc.stdout or "", combined):
        try:
            candidate = json.loads(candidate_text)
        except ValueError:
            continue
        if isinstance(candidate, dict) and "ok" in candidate:
            parsed_ok = bool(candidate["ok"])
            break
    if parsed_ok is None:
        for line in reversed(combined.strip().splitlines()):
            try:
                candidate = json.loads(line)
            except ValueError:
                continue
            if isinstance(candidate, dict) and "ok" in candidate:
                parsed_ok = bool(candidate["ok"])
                break
    return {
        "exit": proc.returncode,
        "ok": parsed_ok if parsed_ok is not None else proc.returncode == 0,
        "output_tail": combined[-2000:],
    }


def run_node_smoke(repo_root: Path, slug: str, base: str, api_key: str) -> dict:
    payload = {
        "title": "Smoke task",
        "status": "open",
        "priority": "medium",
        "notes": "from smoke",
    }
    return _run_node_smoke(
        repo_root,
        slug,
        base,
        api_key,
        "tasks",
        payload,
        {"status": "done"},
    )


def _pick_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def load_trial_hooks(trial_dir: Path) -> dict:
    """Resolve the acceptance-flow and frontend-smoke hooks for a trial.

    A trial directory may ship a ``trial_hooks.py`` exporting
    ``run_acceptance_flow(base, api_key)`` and
    ``run_node_smoke(repo_root, slug, base, api_key)``; when it does not,
    the built-in TaskFlow hooks are used. This lets a second blind trial
    reuse the identical runner, isolation boundary, and evidence contract
    while exercising its own held-out acceptance flow.
    """
    hooks_path = trial_dir / "trial_hooks.py"
    if not hooks_path.is_file():
        return {
            "run_acceptance_flow": run_acceptance_flow,
            "run_node_smoke": run_node_smoke,
        }
    module_name = (
        "_trial_hooks_"
        + hashlib.sha256(str(hooks_path).encode("utf-8")).hexdigest()[:12]
    )
    spec = importlib.util.spec_from_file_location(module_name, hooks_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    flow = getattr(module, "run_acceptance_flow", None)
    smoke = getattr(module, "run_node_smoke", None)
    if not callable(flow) or not callable(smoke):
        raise ValueError(
            f"{hooks_path} must export callable run_acceptance_flow "
            "and run_node_smoke"
        )
    return {"run_acceptance_flow": flow, "run_node_smoke": smoke}


def run_e2e(
    repo_root: Path,
    slug: str,
    evidence_dir: Path,
    hooks: dict | None = None,
) -> dict:
    import secrets

    hooks = hooks or load_trial_hooks(TRIAL_DIR)
    api_key = secrets.token_hex(16)
    port = _pick_port()
    base = f"http://127.0.0.1:{port}"
    log_path = evidence_dir / "server.log"
    env = dict(os.environ)
    env["API_KEY"] = api_key
    env["LOG_LEVEL"] = "INFO"
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        f"{slug}.main:create_app",
        "--factory",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    with log_path.open("w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            command,
            cwd=str(repo_root),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
        try:
            if not _wait_for_health(base):
                return {
                    "evidence_schema": EVIDENCE_SCHEMA,
                    "reachable": False,
                    "server": {"command": command, "log": str(log_path.name)},
                    "acs": {},
                    "node_smoke": {"exit": None, "ok": False, "output_tail": ""},
                    "error": "service did not become healthy",
                }
            acs = hooks["run_acceptance_flow"](base, api_key)
            smoke = hooks["run_node_smoke"](repo_root, slug, base, api_key)
            return {
                "evidence_schema": EVIDENCE_SCHEMA,
                "reachable": True,
                "server": {
                    "command": command,
                    "log": str(log_path.name),
                    "base_url": base,
                    "pid": process.pid,
                },
                "acs": acs,
                "node_smoke": smoke,
            }
        finally:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def run_trial(trial_dir: Path, keep: bool = False) -> int:
    trial_dir = Path(trial_dir).resolve()
    contract_path = trial_dir / "TRIAL_CONTRACT.json"
    if not contract_path.is_file():
        print("BLOCKED: TRIAL_CONTRACT.json missing")
        return 2
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    pin_problems = verify_contract_pins(contract, trial_dir)
    if pin_problems:
        for problem in pin_problems:
            print(f"FAILED: {problem}")
        return 1

    problem_text = (trial_dir / "PROBLEM.md").read_text(encoding="utf-8")
    token_hits = scan_text_tokens(problem_text)
    if token_hits:
        print(f"FAILED: PROBLEM.md contains technology tokens: {token_hits}")
        return 1

    blockers = environment_blockers()
    if blockers:
        for blocker in blockers:
            print(f"BLOCKED: {blocker}")
        return 2

    out_dir = trial_dir / contract["output_dir"]
    evidence_dir = trial_dir / contract["evidence_dir"]
    if out_dir.exists() and not keep:
        shutil.rmtree(out_dir, ignore_errors=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    repo_root = out_dir / "repo"

    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    write_json(
        evidence_dir / "run_meta.json",
        {
            "evidence_schema": EVIDENCE_SCHEMA,
            "task_id": contract["task_id"],
            "started_at": started_at,
            "contract_sha256": sha256_file(contract_path),
            "permitted_input_hashes": {
                name: sha256_file((trial_dir / spec["path"]).resolve())
                for name, spec in contract["inputs"].items()
            },
            "python": sys.version.split()[0],
            "node": _tool_version("node"),
            "uvicorn": _tool_version_module("uvicorn"),
            "fastapi": _tool_version_module("fastapi"),
            "api_key_configured": True,
        },
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in (
        "isr_graph.json",
        "interpretation.json",
        "factory_summary.json",
        "isolation_child.json",
        "isolation-denied.jsonl",
        "errors.json",
    ):
        (evidence_dir / stale).unlink(missing_ok=True)

    try:
        workspace = build_workspace(
            out_dir, (trial_dir / "PROBLEM.md").read_bytes()
        )
    except OSError as exc:
        write_json(
            evidence_dir / "errors.json",
            {"stage": "workspace", "error": repr(exc)},
        )
        print(f"FAILED: workspace preparation raised {exc!r}")
        return 1

    violations = workspace_violations(workspace)
    proc = None
    spawn_error = None
    if not violations:
        try:
            proc = run_isolated_generation(
                trial_dir=trial_dir,
                out_dir=out_dir,
                workspace=workspace,
                evidence_dir=evidence_dir,
                repo_root=repo_root,
                statement_path=workspace / "PROBLEM.md",
                max_repair_attempts=int(contract.get("max_repair_attempts", 3)),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            spawn_error = repr(exc)
    child_record = _load_json_safe(evidence_dir / "isolation_child.json")
    if proc is not None:
        spawn_info = {
            "exit_code": proc.returncode,
            "cwd": str(workspace),
            "stdout_tail": (proc.stdout or "")[-4000:],
            "stderr_tail": (proc.stderr or "")[-4000:],
        }
    elif violations:
        spawn_info = {"skipped": "workspace violations"}
    else:
        spawn_info = {"error": spawn_error or "spawn failed without detail"}
    write_json(
        evidence_dir / "isolation.json",
        {
            "evidence_schema": EVIDENCE_SCHEMA,
            "workspace": workspace_manifest(workspace),
            "violations": violations,
            "denied_count": (
                child_record.get("denied_count") if child_record else None
            ),
            "denied": (child_record or {}).get("denied", []),
            "child": child_record,
            "spawn": spawn_info,
        },
    )
    isolation_ok = bool(
        not violations
        and child_record is not None
        and child_record.get("denied_count") == 0
        and proc is not None
        and proc.returncode in (0, 1)
    )
    if not isolation_ok:
        if not (evidence_dir / "errors.json").is_file():
            write_json(
                evidence_dir / "errors.json",
                {
                    "stage": "isolation",
                    "violations": violations,
                    "denied_count": (
                        child_record.get("denied_count") if child_record else None
                    ),
                    "spawn": spawn_info,
                },
            )
        print("FAILED: generation boundary check failed")
        return 1

    graph_evidence = _load_json_safe(evidence_dir / "isr_graph.json")
    if graph_evidence is None:
        if not (evidence_dir / "errors.json").is_file():
            write_json(
                evidence_dir / "errors.json",
                {"stage": "graph_compile", "spawn": spawn_info},
            )
        print("FAILED: graph compile produced no evidence")
        return 1

    factory_summary = _load_json_safe(evidence_dir / "factory_summary.json")
    if factory_summary is None:
        write_json(
            evidence_dir / "e2e_results.json",
            {
                "evidence_schema": EVIDENCE_SCHEMA,
                "reachable": False,
                "acs": {},
                "node_smoke": {"exit": None, "ok": False, "output_tail": ""},
                "error": "factory stage did not complete",
            },
        )
        print("FAILED: factory stage produced no evidence")
        return 1
    if graph_evidence["isr_hash"] and factory_summary.get("isr_hash"):
        factory_summary["isr_hash_matches_graph"] = (
            graph_evidence["isr_hash"] == factory_summary["isr_hash"]
        )
    else:
        factory_summary["isr_hash_matches_graph"] = False
    write_json(evidence_dir / "factory_summary.json", factory_summary)

    if not repo_root.exists():
        write_json(
            evidence_dir / "e2e_results.json",
            {
                "evidence_schema": EVIDENCE_SCHEMA,
                "reachable": False,
                "acs": {},
                "node_smoke": {"exit": None, "ok": False, "output_tail": ""},
                "error": "materialized repository not found",
            },
        )
        print("FAILED: no materialized repository")
        return 1

    write_json(evidence_dir / "manifest.json", write_manifest(repo_root))

    slug = _bundle_slug(graph_evidence.get("system_name", ""))
    if factory_summary["ok"] and slug:
        e2e = run_e2e(
            repo_root, slug, evidence_dir, hooks=load_trial_hooks(trial_dir)
        )
    else:
        e2e = {
            "evidence_schema": EVIDENCE_SCHEMA,
            "reachable": False,
            "acs": {},
            "node_smoke": {"exit": None, "ok": False, "output_tail": ""},
            "error": "factory did not succeed; runtime stage skipped",
        }
    write_json(evidence_dir / "e2e_results.json", e2e)

    completed = bool(
        factory_summary["ok"]
        and e2e.get("reachable")
        and all(ac.get("passed") for ac in e2e.get("acs", {}).values())
        and e2e.get("node_smoke", {}).get("ok")
    )
    write_json(
        evidence_dir / "run_results.json",
        {
            "evidence_schema": EVIDENCE_SCHEMA,
            "completed": completed,
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "system_name": slug,
        },
    )
    print(
        f"trial {'completed' if completed else 'failed'}: "
        f"system={slug} factory_ok={factory_summary['ok']} "
        f"acs_passed={sum(1 for a in e2e.get('acs', {}).values() if a.get('passed'))}"
        f"/{len(e2e.get('acs', {}))}"
    )
    return 0 if completed else 1


def _tool_version(name: str) -> str | None:
    path = shutil.which(name)
    if path is None:
        return None
    try:
        proc = subprocess.run(
            [path, "--version"], capture_output=True, text=True, timeout=30
        )
        return (proc.stdout or proc.stderr or "").strip().splitlines()[0]
    except (OSError, subprocess.SubprocessError, IndexError):
        return None


def _tool_version_module(name: str) -> str | None:
    try:
        from importlib.metadata import version

        return version(name)
    except Exception:
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run TASKFLOW-ESAP-NATIVE-001")
    parser.add_argument(
        "--keep",
        action="store_true",
        help="keep an existing out/ directory instead of wiping it",
    )
    parser.add_argument(
        "--trial-dir",
        default=None,
        help="trial directory (defaults to this script's directory)",
    )
    args = parser.parse_args(argv)
    trial_dir = Path(args.trial_dir) if args.trial_dir else TRIAL_DIR
    return run_trial(trial_dir, keep=args.keep)


if __name__ == "__main__":
    raise SystemExit(main())
