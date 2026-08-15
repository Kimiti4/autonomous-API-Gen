"""Docker Compose execution environment.

Production adapter for the ExecutionEnvironment port. Falls back to a clear
error when Docker is unavailable (the pre-phase calibrates with
LocalExecutionEnvironment instead). No part of the core pipeline knows which
implementation is in use.
"""
import asyncio
import shlex
import shutil
from ...domain.ports import ExecutionEnvironment
from ...domain.models.bundle import SystemDeploymentBundle
from ...domain.models.evidence import TestRunResult


class DockerComposeEnvironment:
    """Legacy, fixed-shape Docker runner (factory path). Kept for bootstrap.

    Runs the materialized bundle's Python tests with a hardcoded image and
    command. The calibration harness no longer uses this -- see
    ``DockerExecutionEnvironment`` for the backend-driven replacement.
    """

    def __init__(self, timeout_seconds: int = 300) -> None:
        self._timeout = timeout_seconds

    @staticmethod
    def available() -> bool:
        return shutil.which("docker") is not None

    async def run_verification(self, bundle: SystemDeploymentBundle) -> TestRunResult:
        if not self.available():
            raise RuntimeError("Docker is not available; use LocalExecutionEnvironment")
        import time
        start = time.time()
        proc = await asyncio.create_subprocess_exec(
            "docker", "run", "--rm", "-v", f"{bundle.path}:/work", "-w", "/work",
            "python:3.12-slim", "python", "-m", "pytest", "-q",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            code = await asyncio.wait_for(proc.wait(), timeout=self._timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return TestRunResult(passed=False, exit_code=124, total_tests=1, failed_tests=1,
                                 duration_seconds=self._timeout)
        return TestRunResult(passed=(code == 0), exit_code=code, total_tests=1,
                             failed_tests=(0 if code == 0 else 1),
                             duration_seconds=time.time() - start)

    async def teardown(self, bundle: SystemDeploymentBundle) -> None:
        if bundle.path.exists():
            shutil.rmtree(bundle.path, ignore_errors=True)


class DockerExecutionEnvironment:
    """Backend-driven Docker execution environment (calibration harness).

    Runs a backend's declared ``test_command`` inside its declared ``runtime_image``
    so the toolchain lives in the container, not on the host. Backends ship no
    technology assumptions: each declares its own image (e.g. Go via
    ``golang:1.22-alpine``, Python via ``python:3.12-slim``). When Docker is
    absent the harness degrades to ``LocalExecutionEnvironment`` or
    ``skipped:toolchain_absent`` rather than faking evidence.
    """

    def __init__(
        self,
        test_command: list[str],
        runtime_image: str,
        timeout_seconds: int = 300,
        build_command: list[str] | None = None,
    ) -> None:
        self._test_command = list(test_command)
        self._image = runtime_image
        self._timeout = timeout_seconds
        # Optional install phase composed into the container entrypoint when the
        # backend's build profile opts in (``requires_build_phase``). Kept None
        # for backends (e.g. Go) whose image already carries the toolchain.
        self._build_command = list(build_command) if build_command else None

    @staticmethod
    def available() -> bool:
        # R2.9.1: probe the DAEMON, not just the CLI. The previous CLI-only
        # check made Docker-gated tests run-and-fail when the daemon was down
        # (they surfaced as four failures instead of honest skips).
        # R2.9.3: a warm Docker Desktop daemon can take ~9s just to answer
        # ``docker info``; a 10s probe misclassified slow-but-up as down.
        if shutil.which("docker") is None:
            return False
        import subprocess
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True, timeout=30,
            )
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    async def run_verification(self, bundle: SystemDeploymentBundle) -> TestRunResult:
        if not self._test_command:
            raise RuntimeError("DockerExecutionEnvironment requires a test_command")
        if not self._image:
            raise RuntimeError("DockerExecutionEnvironment requires a runtime_image")
        import time
        from pathlib import Path

        start = time.time()
        # Docker volume mounts require an absolute host path (a relative bundle
        # path silently fails to mount, making `go test` see an empty /work dir
        # and report spurious failures). Resolve defensively.
        host_path = str(Path(bundle.path).resolve())
        if self._build_command:
            # Compose deps install + tests into the container entrypoint as a
            # single ``sh -c`` so a single ``docker run`` carries both. The
            # test command is still a list (injectable), only stringified here.
            inner = (
                shlex.join(self._build_command)
                + " && "
                + shlex.join(self._test_command)
            )
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{host_path}:/work", "-w", "/work",
                self._image,
                "sh", "-c", inner,
            ]
        else:
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{host_path}:/work", "-w", "/work",
                self._image,
                *self._test_command,
            ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            code = await asyncio.wait_for(proc.wait(), timeout=self._timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return TestRunResult(passed=False, exit_code=124, total_tests=1, failed_tests=1,
                                 duration_seconds=self._timeout)
        out = await proc.stdout.read() if proc.stdout else b""
        err = await proc.stderr.read() if proc.stderr else b""
        logs = out.decode("utf-8", "replace") + "\n" + err.decode("utf-8", "replace")
        import os, tempfile
        fd, logs_path = tempfile.mkstemp(prefix="docker-run-", suffix=".log")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(logs)
        return TestRunResult(
            passed=(code == 0),
            exit_code=code,
            total_tests=1,
            failed_tests=(0 if code == 0 else 1),
            duration_seconds=time.time() - start,
            logs_path=logs_path,
        )

    async def teardown(self, bundle: SystemDeploymentBundle) -> None:
        if bundle.path.exists():
            shutil.rmtree(bundle.path, ignore_errors=True)
