"""BuildProfileExecutionEnvironment -- per-backend, profile-driven execution.

Where ``LocalExecutionEnvironment`` runs a single caller-supplied test command
(through ``sh -c``, unavailable on Windows), this environment resolves the
bundle's own backend from the ``CompilerRegistry`` and executes exactly the
``build_command`` / ``test_command`` that the backend's ``build_profile``
declares. The meta-compiler therefore never hardcodes any backend's
verification shape -- the shape travels with the backend (Phase 19 contract).

Honesty contract (fail-closed, mirrors ``LocalExecutionEnvironment``):

  * no test command configured       -> ``evaluated=False`` (stage never ran)
  * toolchain absent (tool not on
    PATH)                            -> ``evaluated=False``, exit ``-127``
  * build phase exits non-zero       -> ``evaluated=True``, ``passed=False``
  * test command exit code           -> ``evaluated=True``, ``passed=(0)``

Every run writes its captured stdout/stderr to
``<bundle root>/verification-<backend>.log`` (bundle roots are shared across a
multi-backend fleet, so logs are backend-namespaced) and the path is attached
to the result. ``teardown`` is a no-op: the bundle root is materialized by the
owner, never deleted by the runner.
"""

from __future__ import annotations

import asyncio
import shutil
import time
from pathlib import Path

from tiannara.domain.models.bundle import SystemDeploymentBundle
from tiannara.domain.models.evidence import TestRunResult


class BuildProfileExecutionEnvironment:
    """Runs each bundle's build/test via its backend-declared profile."""

    def __init__(self, registry) -> None:
        self._registry = registry

    async def run_verification(
        self, bundle: SystemDeploymentBundle
    ) -> TestRunResult:
        backend_id = getattr(bundle, "backend_name", None)
        if not backend_id:
            return self._unevaluated(-1)
        try:
            backend = self._registry.backend(backend_id)
        except Exception:
            return self._unevaluated(-1)

        profile = backend.build_profile(
            getattr(bundle, "project_id", "") or ""
        )
        test_command = list(getattr(profile, "test_command", None) or [])
        if not test_command:
            return self._unevaluated(-1)
        if shutil.which(test_command[0]) is None:
            return self._unevaluated(-127)

        root = Path(str(bundle.path))
        started = time.time()

        build_command = list(getattr(profile, "build_command", None) or [])
        if getattr(profile, "requires_build_phase", False) and build_command:
            if shutil.which(build_command[0]) is None:
                return self._unevaluated(-127)
            build_code, build_out = await self._exec(build_command, root)
            if build_code != 0:
                duration = time.time() - started
                log_path = self._write_log(root, backend_id, build_out)
                return TestRunResult(
                    passed=False,
                    exit_code=build_code,
                    total_tests=0,
                    failed_tests=0,
                    duration_seconds=duration,
                    logs_path=str(log_path) if log_path else None,
                    evaluated=True,
                )

        code, output = await self._exec(test_command, root)
        duration = time.time() - started
        log_path = self._write_log(root, backend_id, output)
        return TestRunResult(
            passed=(code == 0),
            exit_code=code,
            total_tests=1,
            failed_tests=(0 if code == 0 else 1),
            duration_seconds=duration,
            logs_path=str(log_path) if log_path else None,
            evaluated=True,
        )

    async def teardown(self, bundle: SystemDeploymentBundle) -> None:
        return None

    # -- internals ---------------------------------------------------------

    @staticmethod
    def _unevaluated(exit_code: int) -> TestRunResult:
        return TestRunResult(
            passed=False,
            exit_code=exit_code,
            total_tests=0,
            failed_tests=0,
            evaluated=False,
        )

    @staticmethod
    async def _exec(command: list[str], cwd: Path) -> tuple[int, str]:
        proc = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await proc.communicate()
        text = out.decode("utf-8", errors="replace") if out else ""
        code = proc.returncode if proc.returncode is not None else -1
        return code, text

    @staticmethod
    def _write_log(root: Path, backend_id: str, output: str) -> Path | None:
        try:
            log_path = root / f"verification-{backend_id}.log"
            log_path.write_text(output, encoding="utf-8")
            return log_path
        except OSError:
            return None
