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


# Recognized transient infrastructure error signatures. A BOUNDED retry is
# honest: each attempt is real, retries are recorded in the evidence, and a
# failure after retries is still FAILED (never silently converted to passed).
TRANSIENT_BUILD_MARKS = (
    "failed to fetch", "i/o timeout", "network", "connection",
    "eof", "unknown blob", "no such host", "timeout", "temporary failure",
    "failed to solve", "timed out", "no such job", "deadline",
)
# Deploy-stage transients.  These are SPECIFIC daemon/environment signatures:
# bare "bind" is deliberately absent — a generic "bind: ..." string can be a
# genuine application/runtime defect and must NOT be auto-labeled transient.
# The Windows host-ported Docker signatures are matched verbatim.
TRANSIENT_DEPLOY_MARKS = (
    "ports are not available",
    "forbidden by its access permissions",
    "address already in use",
    "socket is already in use",
    "resource temporarily unavailable",
)
TRANSIENT_RUN_MARKS = (
    "error waiting for container", "unexpected eof", "eof", "i/o timeout",
    "cannot connect to the docker", "failed to fetch", "network",
    "no matching manifest", "compression", "command timed out", "timed out",
)
TRANSIENT_PROBE_MARKS = (
    "remote end closed", "connection reset", "timed out", "timeout",
    "temporarily unavailable", "connection aborted", "eof",
)
PRODUCT_PROBE_MARKS = (
    "connection refused", "actively refused", "10061", "404", "500", "503",
)

MAX_BUILD_ATTEMPTS = 2
MAX_DEPLOY_ATTEMPTS = 2
TRANSIENT_BACKOFF_S = 2.0
# Startup readiness poll bound — independent of retry amplification.  A probe
# may poll at most this many times (1s apart) waiting for a slow-starting
# container; exceeding it is a startup/availability bound, not a retry model.
MAX_STARTUP_POLLS = 10


def _transient(hay: str, marks: tuple[str, ...]) -> bool:
    h = hay.lower()
    return any(m in h for m in marks)


def _match(hay: str, marks: tuple[str, ...]) -> str:
    """Return the first recognized transient signature present in hay, or ''."""
    h = hay.lower()
    for m in marks:
        if m in h:
            return m
    return ""


def classify_deploy_failure(out: str) -> str:
    """Deploy is a daemon/host operation: it reports the environment, not the
    product.  Recognized transient signatures are infrastructure; anything else
    stays honestly unclassified (""), never a product defect.

    Pure function (no docker) so it is unit-testable.
    """
    if _transient(out, TRANSIENT_DEPLOY_MARKS):
        return "infrastructure"
    return ""


def classify_build_failure(out: str) -> str:
    """Build-stage classification.  Recognized daemon/BuildKit/environment
    signals (registry fetch failure, BuildKit job loss, deadline/timeout) are
    infrastructure; anything else that failed to build is honestly attributed
    to the toolchain/Dockerfile (compiler) — never silently passed.

    Pure function (no docker) so it is unit-testable.
    """
    if out == "command timed out":
        return "infrastructure"
    if _transient(out, TRANSIENT_BUILD_MARKS):
        return "infrastructure"
    return "compiler"


class RealDockerStages:
    """Docker-backed stages that report REAL_DOCKER only when Docker
    actually produced the artifact; any failure → FAILED (never STUB).
    """

    def build(self, repo_dir: str, tag: str) -> StageExecution:
        t0 = time.time()
        attempts = 0
        out = ""
        rc = -1
        retry_signatures: list[str] = []
        for attempt in range(1, MAX_BUILD_ATTEMPTS + 1):
            attempts = attempt
            rc, out = _run(["docker", "build", "-q", "-t", tag, repo_dir])
            if rc == 0:
                break
            mark = _match(out, TRANSIENT_BUILD_MARKS)
            if attempt < MAX_BUILD_ATTEMPTS and mark:
                retry_signatures.append(mark)
                time.sleep(TRANSIENT_BACKOFF_S)
                continue
            break
        retried = attempts > 1
        digest = ""
        if rc == 0:
            rc2, ins = _run(["docker", "inspect", "--format", "{{.Id}}", tag])
            digest = ins.strip() if rc2 == 0 else ""
        detail = out[:500]
        if retried:
            detail = f"[retried {attempts}/{MAX_BUILD_ATTEMPTS} on transient] {detail}"
        failure_class = ""
        if rc != 0:
            failure_class = classify_build_failure(out)
        return StageExecution(
            stage=TrialStage.BUILD,
            mode=ExecutionMode.REAL_DOCKER if rc == 0 else ExecutionMode.FAILED,
            passed=rc == 0,
            duration_s=time.time() - t0,
            logs_hash=_h(out),
            image_digest=digest,
            detail=detail,
            retries=attempts - 1,
            retry_signatures=tuple(retry_signatures),
            failure_class=failure_class,
        )

    def run_tests(self, image: str, spec: "TestSpec", repo_dir: str = "", tag: str = "") -> StageExecution:
        """Dispatch test execution based on the backend's TestSpec.

        runs_in="runtime": run the toolchain in the runtime image.
        runs_in="build": build the toolchain-bearing stage, execute tests inside it, then clean up.

        Classification is honest about WHICH command failed: a failed toolchain
        docker build (e.g. base-image fetch) is infrastructure/compiler, never
        silently "product"; only a successfully-built toolchain whose test run
        returned nonzero is a product failure.  The failure detail carries the
        ERROR TAIL (not head) so the reason is in the evidence.
        """
        from compiler.core.protocol import TestSpec
        t0 = time.time()
        build_failed = False
        if spec.runs_in == "runtime":
            rc, out = _run(["docker", "run", "--rm", image, *spec.command])
        else:
            # Build the toolchain-bearing stage, then execute tests inside it.
            test_tag = f"{tag}-test"
            rc_build, out_build = _run(["docker", "build", "--target", spec.build_target,
                                        "-t", test_tag, repo_dir])
            out = out_build
            if rc_build == 0:
                rc, out = _run(["docker", "run", "--rm", test_tag, *spec.command])
            else:
                build_failed = True
                rc = rc_build  # docker build --target failed; tests never ran
            _run(["docker", "rmi", "-f", test_tag])
        failure_class = ""
        if rc == 1 and not build_failed:
            failure_class = "product"
        elif rc != 0:
            # docker-level error (toolchain build / create / run) — infra
            # transient vs toolchain defect, from the actual tail text.
            failure_class = "infrastructure" if _transient(out, TRANSIENT_RUN_MARKS) else "compiler"
        tail = out[-600:] if rc != 0 else out[:300]
        return StageExecution(
            stage=TrialStage.TEST,
            mode=ExecutionMode.REAL_DOCKER if rc in (0, 1) else ExecutionMode.FAILED,
            passed=rc == 0,
            duration_s=time.time() - t0,
            logs_hash=_h(out),
            detail=f"runs_in={spec.runs_in} cmd={' '.join(spec.command)} {tail}",
            failure_class=failure_class,
        )

    def deploy(self, image: str, port: int) -> StageExecution:
        t0 = time.time()
        attempts = 0
        out = ""
        rc = -1
        retry_signatures: list[str] = []
        for attempt in range(1, MAX_DEPLOY_ATTEMPTS + 1):
            attempts = attempt
            rc, out = _run(["docker", "run", "-d", "-p", f"{port}:8000", image])
            if rc == 0:
                break
            mark = _match(out, TRANSIENT_DEPLOY_MARKS)
            if attempt < MAX_DEPLOY_ATTEMPTS and mark:
                retry_signatures.append(mark)
                time.sleep(TRANSIENT_BACKOFF_S)
                continue
            break
        retried = attempts > 1
        cid = out.strip().splitlines()[-1] if rc == 0 and out.strip() else ""
        detail = out[:500]
        if retried:
            detail = f"[retried {attempts}/{MAX_DEPLOY_ATTEMPTS} on transient] {detail}"
        # Deploy is a daemon/host operation: it reports the environment, not the
        # product.  Recognized transient signatures are infrastructure; anything
        # else stays honestly unclassified (""), never a product defect.
        failure_class = ""
        if rc != 0:
            failure_class = classify_deploy_failure(out)
        return StageExecution(
            stage=TrialStage.DEPLOY,
            mode=ExecutionMode.REAL_DOCKER if rc == 0 else ExecutionMode.FAILED,
            passed=rc == 0,
            duration_s=time.time() - t0,
            logs_hash=_h(out),
            container_id=cid,
            detail=detail,
            retries=attempts - 1,
            retry_signatures=tuple(retry_signatures),
            failure_class=failure_class,
        )

    def probe(self, port: int, cid: str) -> StageExecution:
        t0 = time.time()
        if not cid:
            # Cascade: deploy did not produce a container — probing is a
            # phantom; mark honestly as SKIPPED (never PASS, never inflate).
            return StageExecution(
                stage=TrialStage.RUNTIME,
                mode=ExecutionMode.SKIPPED,
                passed=False,
                duration_s=time.time() - t0,
                logs_hash=_h("cascade-probe"),
                detail="cascade: deploy did not produce a container",
            )
        ok = False
        last_err = ""
        attempts = 0
        wait_start = time.time()
        for _ in range(MAX_STARTUP_POLLS):
            attempts += 1
            try:
                import urllib.request
                urllib.request.urlopen(f"http://localhost:{port}/health", timeout=5)
                ok = True
                break
            except Exception as e:
                last_err = str(e)
                time.sleep(1)
        wait_s = time.time() - wait_start
        _, stats = _run(["docker", "stats", "--no-stream", "--format",
                         "{{.CPUPerc}}/{{.MemUsage}}", cid])
        failure_class = ""
        if not ok:
            if _transient(last_err, TRANSIENT_PROBE_MARKS):
                failure_class = "infrastructure"
            elif _transient(last_err, PRODUCT_PROBE_MARKS):
                failure_class = "product"
        return StageExecution(
            stage=TrialStage.RUNTIME,
            mode=ExecutionMode.REAL_DOCKER,
            passed=ok,
            duration_s=time.time() - t0,
            logs_hash=_h(stats),
            peak_resource=stats.strip() if ok else "",
            detail="probe OK" if ok else f"probe FAILED: {last_err}",
            # Readiness polls are WAITS, not retries: bounded independently via
            # startup_polls/startup_wait_s, and excluded from retry_rate.
            retries=0,
            retry_signatures=(),
            startup_polls=attempts - 1,
            startup_wait_s=round(wait_s, 3),
            failure_class=failure_class,
        )

    def destroy(self, cid: str) -> StageExecution:
        t0 = time.time()
        if not cid:
            # Cascade: deploy did not produce a container — this is NOT a
            # destroy attempt; mark it honestly as SKIPPED (never PASS).
            return StageExecution(
                stage=TrialStage.DESTROY,
                mode=ExecutionMode.SKIPPED,
                passed=False,
                duration_s=time.time() - t0,
                logs_hash=_h("cascade"),
                detail="cascade: deploy did not produce a container",
            )
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
            failure_class="" if rc == 0 else "infrastructure",
        )
