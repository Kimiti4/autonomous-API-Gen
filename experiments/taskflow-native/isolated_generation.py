"""Isolated generation child for TASKFLOW-ESAP-NATIVE-001.

Executed as a separate process with its working directory inside a dedicated
generation workspace (``out/genws``) and a stripped environment. Its trusted
bootstrap (argument parsing, importing ``generationlib``, pruning ``sys.path``
down to allowlisted roots) completes before it installs an irreversible
``sys.addaudithook`` boundary. The boundary denies:

  * file opens outside the allowlisted roots: the generation workspace
    (pipeline source copy + pinned statement), the trial ``out/`` tree
    (materialized repository + evidence), the Python runtime (stdlib,
    site-packages, user site), and this script's own trusted files. The
    system temp directory is a write-only root -- pre-existing contents are
    never readable from inside the boundary. Temporary directories created
    by this process itself (tracked through the ``tempfile`` API) become
    readable session roots, so the pipeline may stage and verify bundles in
    its own scratch space without gaining access to any other temp file;
  * directory listings outside those roots;
  * external network connects or DNS resolves -- generation is offline.
    Loopback (127.0.0.0/8, ::1, localhost) is permitted so the factory can
    health-check the service it spawns for runtime verification.

Denied attempts are appended to ``isolation-denied.jsonl`` and summarized in
``isolation_child.json``; the parent trial fails the run if any denial
occurred. Phases:

  * ``selftest-escape`` -- probe a path and record whether the boundary
    denied it (empirical escape canary for tests and CI);
  * ``compile`` -- interpret the statement and write graph evidence only;
  * ``generate`` -- the full generation pipeline (interpret, compile,
    materialize, verify, bounded repair) inside the boundary.

Exit codes: 0 phase succeeded (boundary held), 1 phase failed, 2 misuse.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import site
import sys
import sysconfig
import tempfile
import traceback
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent

_PATH_EVENTS = ("open", "os.listdir", "os.scandir")
_NETWORK_EVENTS = ("socket.connect", "socket.getaddrinfo")
_DENIED_EVENTS = _PATH_EVENTS + _NETWORK_EVENTS
_MAX_DENIED_RECORDS = 50

_SESSION_ROOTS: list[str] = []


def _temp_write_root() -> str:
    return os.path.normcase(os.path.realpath(tempfile.gettempdir()))


def _track_session_path(path) -> None:
    temp_root = _temp_write_root()
    resolved = os.path.normcase(os.path.realpath(str(path)))
    if (
        resolved == temp_root or resolved.startswith(temp_root + os.sep)
    ) and resolved not in _SESSION_ROOTS:
        _SESSION_ROOTS.append(resolved)


def _install_tempfile_tracking() -> None:
    if getattr(tempfile, "_esap_session_tracking", False):
        return
    original_mkdtemp = tempfile.mkdtemp
    original_mkstemp = tempfile.mkstemp
    original_td = tempfile.TemporaryDirectory

    def tracked_mkdtemp(*args, **kwargs):
        path = original_mkdtemp(*args, **kwargs)
        _track_session_path(path)
        return path

    def tracked_mkstemp(*args, **kwargs):
        result = original_mkstemp(*args, **kwargs)
        _track_session_path(result[1])
        return result

    class _TrackedTemporaryDirectory(original_td):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            _track_session_path(self.name)

    tempfile.mkdtemp = tracked_mkdtemp
    tempfile.mkstemp = tracked_mkstemp
    tempfile.TemporaryDirectory = _TrackedTemporaryDirectory
    tempfile._esap_session_tracking = True
    tempfile._esap_originals = {
        "mkdtemp": original_mkdtemp,
        "mkstemp": original_mkstemp,
        "TemporaryDirectory": original_td,
    }


def _uninstall_tempfile_tracking() -> None:
    originals = getattr(tempfile, "_esap_originals", None)
    if not originals:
        return
    tempfile.mkdtemp = originals["mkdtemp"]
    tempfile.mkstemp = originals["mkstemp"]
    tempfile.TemporaryDirectory = originals["TemporaryDirectory"]
    del tempfile._esap_session_tracking
    del tempfile._esap_originals


def _resolve_target(target) -> str | None:
    if target is None or isinstance(target, int):
        return None
    if isinstance(target, (bytes, os.PathLike)):
        text = os.fsdecode(target)
    elif isinstance(target, str):
        text = target
    else:
        return None
    return os.path.normcase(os.path.realpath(text))


def _allowed_roots(workspace: Path, out_root: Path) -> list[str]:
    paths: list[Path] = [
        workspace,
        out_root,
        Path(sysconfig.get_paths()["stdlib"]),
        Path(sysconfig.get_paths()["purelib"]),
        Path(sysconfig.get_paths()["platlib"]),
        Path(sys.prefix),
        Path(sys.base_prefix),
        SCRIPT_PATH,
        SCRIPT_DIR / "generationlib.py",
    ]
    try:
        paths.append(Path(site.getusersitepackages()))
    except Exception:
        pass
    try:
        paths.extend(Path(p) for p in site.getsitepackages())
    except Exception:
        pass
    roots: list[str] = []
    for path in paths:
        resolved = os.path.normcase(os.path.realpath(str(path)))
        if resolved not in roots:
            roots.append(resolved)
    return roots


def _is_allowed(resolved: str, roots: list[str]) -> bool:
    return any(
        resolved == root or resolved.startswith(root + os.sep) for root in roots
    )


def _is_write_open(args) -> bool:
    mode = args[1] if len(args) > 1 else None
    flags = args[2] if len(args) > 2 else None
    if isinstance(mode, str):
        return any(marker in mode for marker in ("w", "a", "x", "+"))
    for candidate in (flags, mode):
        if isinstance(candidate, int):
            return bool(candidate & (os.O_WRONLY | os.O_RDWR))
    return False


def _is_loopback_host(host) -> bool:
    if not isinstance(host, str):
        return False
    normalized = host.strip("[]").lower()
    if normalized in ("localhost", "ip6-localhost", "ip6-loopback"):
        return True
    if normalized in ("::1", "0:0:0:0:0:0:0:1"):
        return True
    return normalized.startswith("127.")


def _is_loopback_call(event: str, args) -> bool:
    if event == "socket.connect":
        address = args[1] if len(args) > 1 else None
        if isinstance(address, tuple) and address:
            return _is_loopback_host(address[0])
        return False
    if event == "socket.getaddrinfo":
        return _is_loopback_host(args[0] if args else None)
    return False


def build_audit_hook(
    roots: list[str],
    records: list,
    sink,
    write_roots: list[str] | None = None,
    session_roots: list[str] | None = None,
) -> object:
    def hook(event, args):
        if event not in _DENIED_EVENTS:
            return
        if event in _NETWORK_EVENTS:
            if _is_loopback_call(event, args):
                return
            record = {
                "event": event,
                "path": None,
                "attempted": repr(args),
            }
            records.append(record)
            try:
                sink.write(json.dumps(record, sort_keys=True, default=str) + "\n")
                sink.flush()
            except Exception:
                pass
            raise PermissionError(
                f"isolated generation denied {event}: external network use "
                f"is not permitted inside the generation boundary"
            )
        target = args[0] if args else None
        if target is None or isinstance(target, int):
            return
        resolved = _resolve_target(target)
        if resolved is None:
            resolved_text = repr(target)
        else:
            resolved_text = resolved
            if _is_allowed(resolved, roots):
                return
            if session_roots and _is_allowed(resolved, session_roots):
                return
            if (
                write_roots
                and _is_write_open(args)
                and _is_allowed(resolved, write_roots)
            ):
                return
        record = {
            "event": event,
            "path": resolved_text,
            "attempted": str(target),
        }
        records.append(record)
        try:
            sink.write(json.dumps(record, sort_keys=True, default=str) + "\n")
            sink.flush()
        except Exception:
            pass
        raise PermissionError(
            f"isolated generation denied {event} outside allowlisted roots: "
            f"{resolved_text}"
        )

    return hook


def _prune_sys_path(roots: list[str]) -> None:
    kept = []
    for entry in sys.path:
        resolved = _resolve_target(entry)
        if entry in ("", None) or (resolved is not None and _is_allowed(resolved, roots)):
            kept.append(entry)
    sys.path[:] = kept


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _selftest(probe_path: str) -> dict:
    outcome = {
        "probe_path": str(probe_path),
        "opened": False,
        "error": None,
    }
    try:
        with open(probe_path, "r", encoding="utf-8", errors="replace") as handle:
            handle.read(64)
        outcome["opened"] = True
    except PermissionError as exc:
        outcome["error"] = str(exc)
    except OSError as exc:
        outcome["error"] = repr(exc)
    return outcome


def _run_phase(args: argparse.Namespace, phase: str) -> int:
    import generationlib

    evidence_dir = Path(args.evidence_dir)
    statement_path = Path(args.statement)
    statement = statement_path.read_text(encoding="utf-8")
    graph_evidence, interpretation = generationlib.compile_for_graph_evidence(
        statement
    )
    _write_json(evidence_dir / "isr_graph.json", graph_evidence)
    _write_json(evidence_dir / "interpretation.json", interpretation)
    if phase == "compile":
        print(
            f"isolated compile: nodes={graph_evidence['node_count']} "
            f"edges={graph_evidence['edge_count']} "
            f"repairs={graph_evidence['repair_iterations']}"
        )
        return 0
    factory_summary, _report = generationlib.run_factory(
        statement,
        Path(args.repo_root),
        evidence_dir,
        int(args.max_repair),
    )
    _write_json(evidence_dir / "factory_summary.json", factory_summary)
    print(f"isolated generation: factory_ok={factory_summary.get('ok')}")
    return 0 if factory_summary.get("ok") else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="isolated generation child")
    parser.add_argument(
        "--phase",
        required=True,
        choices=("selftest-escape", "compile", "generate"),
    )
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--statement", default=None)
    parser.add_argument("--max-repair", default="3")
    parser.add_argument("--probe-path", default=None)
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).resolve()
    out_root = Path(args.out_root).resolve()
    evidence_dir = Path(args.evidence_dir).resolve()
    if not workspace.is_dir():
        print(f"workspace missing: {workspace}")
        return 2
    evidence_dir.mkdir(parents=True, exist_ok=True)

    import generationlib

    roots = _allowed_roots(workspace, out_root)
    _prune_sys_path(roots)
    write_roots = [_temp_write_root()]
    _install_tempfile_tracking()

    records: list = []
    sink_path = evidence_dir / "isolation-denied.jsonl"
    sink = sink_path.open("w", encoding="utf-8")
    sys.addaudithook(
        build_audit_hook(
            roots,
            records,
            sink,
            write_roots=write_roots,
            session_roots=_SESSION_ROOTS,
        )
    )

    exit_code = 2
    selftest: dict | None = None
    statement_sha: str | None = None
    try:
        if args.phase == "selftest-escape":
            if not args.probe_path:
                print("selftest-escape requires --probe-path")
                exit_code = 2
            else:
                selftest = _selftest(args.probe_path)
                _write_json(evidence_dir / "isolation_selftest.json", selftest)
                exit_code = 0
        elif args.phase in ("compile", "generate"):
            if not args.statement or not args.repo_root:
                print(f"{args.phase} requires --statement and --repo-root")
                exit_code = 2
            else:
                statement_sha = hashlib.sha256(
                    Path(args.statement).read_bytes()
                ).hexdigest()
                exit_code = _run_phase(args, args.phase)
        else:
            exit_code = 2
    except PermissionError as exc:
        _write_json(
            evidence_dir / "errors.json",
            {
                "stage": args.phase,
                "error": str(exc),
                "traceback": traceback.format_exc()[-4000:],
            },
        )
        print(f"FAILED: boundary denial: {exc}")
        exit_code = 1
    except BaseException as exc:
        _write_json(
            evidence_dir / "errors.json",
            {
                "stage": args.phase,
                "error": repr(exc),
                "traceback": traceback.format_exc()[-4000:],
            },
        )
        print(f"FAILED: {args.phase} raised {exc!r}")
        exit_code = 1
    finally:
        record = {
            "evidence_schema": generationlib.EVIDENCE_SCHEMA,
            "phase": args.phase,
            "exit_code": exit_code,
            "denied_count": len(records),
            "denied": records[:_MAX_DENIED_RECORDS],
            "workspace": str(workspace),
            "out_root": str(out_root),
            "cwd": os.getcwd(),
            "allowed_roots": roots,
            "session_roots": list(_SESSION_ROOTS),
            "sys_path": [entry for entry in sys.path],
            "env_keys": sorted(os.environ),
            "statement_sha256": statement_sha,
            "selftest": selftest,
        }
        try:
            _write_json(evidence_dir / "isolation_child.json", record)
        finally:
            sink.close()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
