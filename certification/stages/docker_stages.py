"""Real Docker stages — never STUB; any missing binary / nonzero exit → FAILED."""
from __future__ import annotations
import hashlib
import os
import subprocess
import time

from certification.core.trial import TrialStage
from certification.stages.execution_mode import ExecutionMode, StageExecution


def _h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _run(cmd: list[str], timeout: int = 900) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr
    except FileNotFoundError:
        return 127, "docker binary not found"
    except subprocess.TimeoutExpired:
        return 124, "command timed out"


class RealDockerStages:
    """Docker-backed stages that report REAL_DOCKER only when Docker
    actually produced the artifact; any failure → FAILED (never STUB).
    """

    def build(self, repo_dir: str, tag: str) -> StageExecution:
        t0 = time.time()
        rc, out = _run(["docker", "build", "-q", "-t", tag, repo_dir])
        digest = ""
        if rc == 0:
            rc2, ins = _run(["docker", "inspect", "--format", "{{.Id}}", tag])
            digest = ins.strip() if rc2 == 0 else ""
        return StageExecution(
            stage=TrialStage.BUILD,
            mode=ExecutionMode.REAL_DOCKER if rc == 0 else ExecutionMode.FAILED,
            passed=rc == 0,
            duration_s=time.time() - t0,
            logs_hash=_h(out),
            image_digest=digest,
            detail=out[:500],
        )

    def run_tests(self, image: str, cmd: list[str], test_image: str = "") -> StageExecution:
        target = test_image or image
        t0 = time.time()
        rc, out = _run(["docker", "run", "--rm", target, *cmd])
        return StageExecution(
            stage=TrialStage.TEST,
            mode=ExecutionMode.REAL_DOCKER if rc in (0, 1) else ExecutionMode.FAILED,
            passed=rc == 0,
            duration_s=time.time() - t0,
            logs_hash=_h(out),
            detail=out[:500],
        )

    def deploy(self, image: str, port: int) -> StageExecution:
        t0 = time.time()
        rc, out = _run(["docker", "run", "-d", "-p", f"{port}:8000", image])
        cid = out.strip().splitlines()[-1] if rc == 0 and out.strip() else ""
        return StageExecution(
            stage=TrialStage.DEPLOY,
            mode=ExecutionMode.REAL_DOCKER if rc == 0 else ExecutionMode.FAILED,
            passed=rc == 0,
            duration_s=time.time() - t0,
            logs_hash=_h(out),
            container_id=cid,
            detail=out[:500],
        )

    def probe(self, port: int, cid: str) -> StageExecution:
        t0 = time.time()
        ok = False
        last_err = ""
        for _ in range(10):
            try:
                import urllib.request
                urllib.request.urlopen(f"http://localhost:{port}/health", timeout=5)
                ok = True
                break
            except Exception as e:
                last_err = str(e)
                time.sleep(1)
        _, stats = _run(["docker", "stats", "--no-stream", "--format",
                         "{{.CPUPerc}}/{{.MemUsage}}", cid])
        return StageExecution(
            stage=TrialStage.RUNTIME,
            mode=ExecutionMode.REAL_DOCKER,
            passed=ok,
            duration_s=time.time() - t0,
            logs_hash=_h(stats),
            peak_resource=stats.strip() if ok else "",
            detail="probe OK" if ok else f"probe FAILED: {last_err}",
        )

    def destroy(self, cid: str) -> StageExecution:
        t0 = time.time()
        rc, out = _run(["docker", "rm", "-f", cid])
        _, ps = _run(["docker", "ps", "-a", "-q", "--filter", f"id={cid}"])
        gone = rc == 0 and ps.strip() == ""
        return StageExecution(
            stage=TrialStage.DESTROY,
            mode=ExecutionMode.REAL_DOCKER if rc == 0 else ExecutionMode.FAILED,
            passed=gone,
            duration_s=time.time() - t0,
            logs_hash=_h(out),
            detail=out[:500],
        )
