import asyncio
import shlex
import shutil
from ...domain.ports import ExecutionEnvironment
from ...domain.models.bundle import SystemDeploymentBundle
from ...domain.models.evidence import TestRunResult


class LocalExecutionEnvironment:
    """Runs a test command inside the bundle directory; no container isolation.
    Swap for DockerComposeEnvironment behind the same port in production."""

    def __init__(
        self,
        test_command: list[str] | None = None,
        *,
        build_command: list[str] | None = None,
    ) -> None:
        self._test_command = test_command
        self._build_command = list(build_command) if build_command else None

    async def run_verification(self, bundle: SystemDeploymentBundle) -> TestRunResult:
        if self._test_command is None:
            return TestRunResult(passed=True, exit_code=0, total_tests=1, failed_tests=0)
        import time
        start = time.time()
        if self._build_command:
            inner = (
                shlex.join(self._build_command)
                + " && "
                + shlex.join(self._test_command)
            )
            proc = await asyncio.create_subprocess_exec(
                "sh", "-c", inner,
                cwd=str(bundle.path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        else:
            proc = await asyncio.create_subprocess_exec(
                *self._test_command,
                cwd=str(bundle.path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        code = await proc.wait()
        duration = time.time() - start
        return TestRunResult(
            passed=(code == 0), exit_code=code, total_tests=1,
            failed_tests=(0 if code == 0 else 1), duration_seconds=duration,
        )

    async def teardown(self, bundle: SystemDeploymentBundle) -> None:
        if bundle.path.exists():
            shutil.rmtree(bundle.path, ignore_errors=True)
