"""D5 harness — Docker execution plumbing + docker-probe helpers.

The GOVERNED logic (causal classification, backend-swap policy, candidate,
learning consumption) comes from the real `certification.feedback` modules —
NOT duplicated here.  This harness only provides:

  - docker build/run/probe/cleanup (the real execution substrate)
  - a minimal append-only trial ledger + structured event log (isolated, tmp)

This is the "production replacement point" for docker exec plumbing.  It does
not modify, patch, or rewrite generated repositories.
"""
from __future__ import annotations

import hashlib
import json
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from certification.feedback.rule import analyze_failure, FailureClassification
from certification.feedback.policy import BackendSwapPolicy
from certification.feedback.candidate import EvolutionCandidate
from certification.feedback.repair import GovernedRepair


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_dir(root: Path) -> str:
    """Deterministic artifact hash over a build context directory."""
    h = hashlib.sha256()
    for p in sorted(Path(root).rglob("*")):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            h.update(rel.encode("utf-8"))
            h.update(b"\0")
            h.update(p.read_bytes())
            h.update(b"\0")
    return h.hexdigest()


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_cmd(cmd, cwd: Optional[Path] = None) -> str:
    proc = subprocess.run(
        cmd, cwd=str(cwd) if cwd else None,
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed: {cmd}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return proc.stdout.strip()


def docker_available() -> bool:
    try:
        subprocess.run(["docker", "info"], capture_output=True, check=True)
        return True
    except Exception:
        return False


def build_image(tag: str, context: Path) -> str:
    run_cmd(["docker", "build", "--quiet", "-t", tag, str(context)])
    return run_cmd(["docker", "image", "inspect", "--format", "{{.Id}}", tag])


def run_container(name: str, image: str, host_port: int, container_port: int = 8080) -> None:
    run_cmd([
        "docker", "run", "-d", "--name", name,
        "-p", f"{host_port}:{container_port}", image,
    ])


def stop_container(name: str) -> None:
    for sub in (["docker", "stop", name], ["docker", "rm", "-f", name]):
        try:
            run_cmd(sub)
        except Exception:
            pass


def container_logs(name: str) -> str:
    try:
        return run_cmd(["docker", "logs", name])
    except Exception as exc:
        return f"<failed to fetch logs: {exc}>"


def remove_image(tag: str) -> None:
    try:
        run_cmd(["docker", "image", "rm", "-f", tag])
    except Exception:
        pass


def http_get_json(url: str, timeout: float = 2.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8") if hasattr(e, "read") else ""
        status = e.code
    except Exception:
        return 0, {}
    try:
        return status, json.loads(raw)
    except Exception:
        return status, {}


def wait_http_live(url: str, timeout: float = 90.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status, _ = http_get_json(url, timeout=2.0)
        if status == 200:
            return True
        time.sleep(0.5)
    return False


def items_behavior_ok(status: int, body: Any) -> bool:
    """D5 workload behavioral contract: /live 200 and /items returns a
    non-empty list.  The parent (rust) fixture is live but violates /items;
    the candidate (python) fixture satisfies it.  A runtime backend-behavior
    failure, not infrastructure."""
    return (
        status == 200
        and isinstance(body, dict)
        and isinstance(body.get("items"), list)
        and len(body.get("items", [])) > 0
    )


# Re-export the real governed contracts/classes so the trial uses the SAME
# logic as production (no parallel stub taxonomy).
__all__ = [
    "utcnow", "sha256_text", "hash_dir", "free_port", "run_cmd",
    "docker_available", "build_image", "run_container", "stop_container",
    "container_logs", "remove_image", "http_get_json", "wait_http_live",
    "items_behavior_ok",
    "FailureClassification", "EvolutionCandidate", "BackendSwapPolicy",
    "GovernedRepair", "analyze_failure",
]
