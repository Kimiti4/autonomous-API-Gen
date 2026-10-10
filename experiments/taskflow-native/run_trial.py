"""TASKFLOW-ESAP-NATIVE-001 -- blind-generation trial runner.

Executes the first genuine blind-generation trial end to end, using only the
permitted inputs pinned by ``TRIAL_CONTRACT.json``:

  1. verify the contract's SHA-256 pins over PROBLEM.md / ACCEPTANCE.json;
  2. seed the hermetic recorded transcript at runtime (never committed);
  3. compile the problem statement once for graph evidence (ISR hash);
  4. run the SoftwareFactory: compile -> derive -> select -> generate ->
     static + runtime verification -> bounded repair (<= contract limit);
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

EVIDENCE_SCHEMA = "taskflow.trial.evidence.v1"

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


def intent_config():
    from tiannara.application.intent.config import IntentCompilerConfig

    model = os.environ.get("TASKFLOW_OLLAMA_MODEL", "qwen2.5:3b").strip()
    if not model:
        raise ValueError("taskflow-model-name-required")
    return IntentCompilerConfig(model_id=f"ollama:{model}")


def seed_transcript(statement: str, transcript_path: Path) -> Path:
    """Run live structured elicitation/extraction and record provenance for replay."""
    from tiannara.application.intent import derive_system_id
    from tiannara.application.intent.compiler import IntentCompiler
    from tiannara.infrastructure.llm.ollama_provider import OllamaModelProvider
    from tiannara.infrastructure.llm.recording_provider import RecordingModelProvider
    from tiannara.infrastructure.llm.transcript import ModelCallTranscript

    model = os.environ.get("TASKFLOW_OLLAMA_MODEL", "qwen2.5:3b").strip()
    base_url = os.environ.get("TASKFLOW_OLLAMA_URL", "http://127.0.0.1:11434")
    timeout = float(os.environ.get("TASKFLOW_OLLAMA_TIMEOUT_SECONDS", "180"))
    transcript = ModelCallTranscript(transcript_path)
    live_provider = OllamaModelProvider(
        base_url=base_url, model=model, timeout_seconds=timeout
    )
    recording_provider = RecordingModelProvider(live_provider, transcript)
    IntentCompiler(recording_provider, config=intent_config()).compile_full(
        statement, derive_system_id(statement)
    )
    return transcript_path


def compile_for_graph_evidence(statement: str, transcript_path: Path) -> dict:
    from tiannara.application.intent import derive_system_id
    from tiannara.application.intent.compiler import IntentCompiler
    from tiannara.infrastructure.llm.recorded_provider import RecordedModelProvider
    from tiannara.infrastructure.llm.transcript import ModelCallTranscript

    provider = RecordedModelProvider(ModelCallTranscript(transcript_path))
    result = IntentCompiler(provider, config=intent_config()).compile_full(
        statement, derive_system_id(statement)
    )
    model = result.isr.system_model if hasattr(result.isr, "system_model") else None
    return {
        "evidence_schema": EVIDENCE_SCHEMA,
        "isr_hash": result.isr.content_hash(),
        "system_name": getattr(result.isr, "system_name", "")
        or getattr(model, "system_name", ""),
        "graph_hash": result.requirement_graph.content_hash(),
        "repair_iterations": result.repair_iterations,
        "model_calls": len(result.call_records),
    }


def default_verifier_factory(compilation_result):
    from tiannara.application.compiler.verification import BundleVerifier

    package = getattr(compilation_result, "system_name", "bundle")
    required = sorted(getattr(compilation_result, "files", {}).keys())
    return BundleVerifier(package=package, required_files=required)


def summarize_report(report) -> dict:
    bundles = []
    for outcome in getattr(report, "verification_outcomes", ()) or ():
        test_result = getattr(outcome, "test_result", None)
        test = None
        if test_result is not None:
            test = {
                "evaluated": bool(getattr(test_result, "evaluated", True)),
                "passed": bool(getattr(test_result, "passed", False)),
                "exit_code": int(getattr(test_result, "exit_code", -1)),
                "duration_seconds": float(
                    getattr(test_result, "duration_seconds", 0.0) or 0.0
                ),
                "logs_path": getattr(test_result, "logs_path", None),
            }
        bundles.append(
            {
                "backend_id": getattr(outcome, "bundle_backend_id", ""),
                "static_ok": bool(getattr(outcome, "static_ok", False)),
                "ok": bool(getattr(outcome, "ok", False)),
                "repair_attempts": int(getattr(outcome, "repair_attempts", 0)),
                "test": test,
            }
        )
    return {
        "evidence_schema": EVIDENCE_SCHEMA,
        "ok": bool(getattr(report, "ok", False)),
        "isr_hash": getattr(report, "isr_hash", ""),
        "statement_hash": getattr(report, "statement_hash", ""),
        "plan_id": getattr(report, "plan_id", ""),
        "bundles": bundles,
        "repair_attempts_total": sum(b["repair_attempts"] for b in bundles),
    }


def run_factory(
    statement: str,
    transcript_path: Path,
    repo_root: Path,
    evidence_dir: Path,
    max_repair_attempts: int,
) -> tuple[dict, object]:
    from tiannara.application.compiler.composition import (
        build_compiler_registry,
        build_project_compiler,
    )
    from tiannara.application.factory import (
        RematerializationRepairProvider,
        SoftwareFactory,
        SoftwareFactoryError,
    )
    from tiannara.application.factory.evidence_sink import make_factory_evidence_sink
    from tiannara.application.materializer.materializer import RepositoryMaterializer
    from tiannara.infrastructure.ledger.jsonl_evidence_ledger import JsonlEvidenceLedger
    from tiannara.infrastructure.llm.recorded_provider import RecordedModelProvider
    from tiannara.infrastructure.llm.transcript import ModelCallTranscript
    from tiannara.infrastructure.sandbox.profile_environment import (
        BuildProfileExecutionEnvironment,
    )
    from tiannara.infrastructure.source_control.local_git import LocalGitBackend

    registry = build_compiler_registry()
    provider = RecordedModelProvider(ModelCallTranscript(transcript_path))
    compiler = build_project_compiler(
        provider=provider, registry=registry, config=intent_config()
    )
    sc_backend = LocalGitBackend() if shutil.which("git") else None
    materializer = RepositoryMaterializer(sc_backend)
    ledger = JsonlEvidenceLedger(str(evidence_dir / "factory-ledger.jsonl"))
    factory = SoftwareFactory(
        project_compiler=compiler,
        materializer=materializer,
        execution_environment=BuildProfileExecutionEnvironment(registry),
        repair_provider=RematerializationRepairProvider(),
        verifier_factory=default_verifier_factory,
        max_repair_attempts=max_repair_attempts,
        evidence_sink=make_factory_evidence_sink(ledger),
        require_static=True,
        require_runtime=True,
    )
    try:
        report = factory.run(statement, out_root=str(repo_root), force=True)
    except SoftwareFactoryError as exc:
        failed_report = getattr(exc, "report", None)
        if failed_report is None:
            return (
                {
                    "evidence_schema": EVIDENCE_SCHEMA,
                    "ok": False,
                    "isr_hash": "",
                    "statement_hash": "",
                    "plan_id": "",
                    "bundles": [],
                    "repair_attempts_total": 0,
                    "error": repr(exc),
                },
                None,
            )
        summary = summarize_report(failed_report)
        summary["error"] = repr(exc)
        return summary, failed_report
    return summarize_report(report), report


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


def run_node_smoke(repo_root: Path, slug: str, base: str, api_key: str) -> dict:
    smoke_path = repo_root / slug / "frontend" / "smoke.mjs"
    payload = {
        "title": "Smoke task",
        "status": "open",
        "priority": "medium",
        "notes": "from smoke",
    }
    command = [
        "node",
        str(smoke_path),
        "--base",
        base,
        "--key",
        api_key,
        "--resource",
        "tasks",
        "--payload",
        json.dumps(payload),
        "--changes",
        json.dumps({"status": "done"}),
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


def _pick_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def run_e2e(repo_root: Path, slug: str, evidence_dir: Path) -> dict:
    import secrets

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
            acs = run_acceptance_flow(base, api_key)
            smoke = run_node_smoke(repo_root, slug, base, api_key)
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

    statement = problem_text
    transcript_path = out_dir / "transcript.jsonl"
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        seed_transcript(statement, transcript_path)
        graph_evidence = compile_for_graph_evidence(statement, transcript_path)
    except Exception as exc:
        write_json(
            evidence_dir / "errors.json",
            {"stage": "graph_compile", "error": repr(exc)},
        )
        print(f"BLOCKED: live intent compilation failed ({type(exc).__name__})")
        return 2
    write_json(evidence_dir / "isr_graph.json", graph_evidence)

    factory_summary, _report = run_factory(
        statement,
        transcript_path,
        repo_root,
        evidence_dir,
        int(contract.get("max_repair_attempts", 3)),
    )
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
        e2e = run_e2e(repo_root, slug, evidence_dir)
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
