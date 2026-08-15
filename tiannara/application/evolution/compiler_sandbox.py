"""R2.4.0b -- real backend grounding for the candidate sandbox.

The R2.3 ``CandidateSandbox`` (MockRunner) *simulates* backend+codegen+run from the
ISR graph. This module provides the *real* grounding: it compiles the constitutional
ISR through the real ``FastAPIHexagonalBackend`` (appending the backend's
``async_resolution_module`` output as generated source), then executes the bundle
with real ``pytest -W error::RuntimeWarning`` inside ``python:3.12-slim``.

This is the line R2 crosses from "ISR mutation works" to "the Evolution Engine
repairs reality." The simulated sandbox is intentionally left intact so CI without
Docker still exercises the orchestration logic.
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from constitutional_architecture.isr.model import ISR

from tiannara.application.compiler.fastapi_hexagonal_backend import FastAPIHexagonalBackend
from tiannara.application.compiler.writer import write_bundle
from tiannara.application.diagnosis.classifier import (
    FailureClassifier,
    FailureEvidenceInput,
)
from tiannara.application.evolution.candidate_sandbox import CompiledCandidate
from tiannara.application.evolution.transition_restoration import TransitionRestoration
from tiannara.domain.models.bundle import SystemDeploymentBundle
from tiannara.domain.models.evidence import TestExecution, TestOutcome, TestRunResult
from tiannara.domain.models.observation import FailureObservation, FailurePhase
from tiannara.domain.models.system_model import (
    AbstractFieldType,
    BusinessCapability,
    DataModelSpec,
    FieldSpec,
    RequirementsReference,
    SecurityModel,
    SystemModel,
)
from tiannara.domain.services.canonical import canonical_hash
from tiannara.infrastructure.sandbox.docker_environment import DockerExecutionEnvironment

#: pytest test that exercises the generated async-resolution surface. Under
#: ``-W error::RuntimeWarning`` the fire-and-forget form raises the coroutine
#: warning; the awaited form passes cleanly.
_ASYNC_TEST_SOURCE = """\
import asyncio

from {slug}.async_resolution import orchestrate


def test_orchestration_runs_clean():
    asyncio.run(orchestrate())
"""


#: Test-run / install side-effect dirs that the Docker bind-mount writes into the
#: host source tree. ``hash_artifact`` excludes these so a tree touched by
#: ``run_tests`` still hashes identically to a fresh compilation (A5a/A5b).
_IGNORED_PARTS = frozenset(
    {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache",
     ".tox", ".eggs", "build", "dist", ".git"}
)
_IGNORED_SUFFIXES = frozenset({".pyc", ".pyo", ".pyd"})


def docker_available() -> bool:
    """True iff the Docker CLI is on PATH (the closed-loop gate needs it)."""
    return DockerExecutionEnvironment.available()


def hash_artifact(root: str | Path) -> str:
    """Deterministic SHA-256 over a generated source tree (path -> content).

    Only generated *source* is hashed. Test-run / install side effects that the
    Docker execution environment writes into the bind-mounted host tree
    (``__pycache__``, ``.pytest_cache``, bytecode, ``.git``) are excluded so a
    tree touched by ``run_tests`` still hashes identically to a fresh
    compilation -- the contract the R2.4.0b closed loop leans on (A5a/A5b).
    """
    root = Path(root)
    files: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(root).as_posix()
        parts = rel.split("/")
        if _IGNORED_PARTS & set(parts):
            continue
        if path.suffix in _IGNORED_SUFFIXES:
            continue
        files[rel] = path.read_text("utf-8", "replace")
    return canonical_hash(files)


def hash_run(run: TestRunResult) -> str:
    """Deterministic hash over a runtime outcome (for the evidence ledger)."""
    logs = ""
    if run.logs_path and os.path.exists(run.logs_path):
        logs = Path(run.logs_path).read_text("utf-8", "replace")
    return canonical_hash(
        {
            "exit_code": run.exit_code,
            "passed": run.passed,
            "total_tests": run.total_tests,
            "failed_tests": run.failed_tests,
            "pass_count": run.pass_count,
            "tests": [
                {
                    "test_id": t.test_id,
                    "outcome": t.outcome.value,
                    "duration_seconds": t.duration_seconds,
                    "content_hash": t.content_hash,
                    "attempt": t.attempt,
                    "flaky": t.flaky,
                }
                for t in run.tests
            ],
            "logs": logs,
        }
    )


# Transient infrastructure failure signatures (pip/network/OOM/container) that
# may recur on a fresh, ephemeral container even though the artifact is valid.
# Genuine test-failure signatures (below) are NEVER retried -- a real
# ``coroutine '...' was never awaited`` or assertion must fail fast.
_INFRA_TRANSIENT_EXIT_CODES = frozenset({2, 125, 137, 143, 130, 139})
_INFRA_TRANSIENT_PATTERNS = (
    "No module named", "No matching distribution", "Could not find a version",
    "ConnectionError", "Read timed out", "read timed out", "Max retries exceeded",
    "Killed", "Out of memory", "No space left", "resolve: failed",
)
_GENUINE_FAILURE_SIGNATURES = (
    "was never awaited", "RuntimeWarning", "AssertionError", "FAILED",
)


def _is_infra_transient(run) -> bool:
    """True iff the run failed for a retryable infrastructure reason rather than
    a genuine test failure."""
    if run.exit_code == 0:
        return False
    logs = ""
    if getattr(run, "logs_path", None) and os.path.exists(run.logs_path):
        logs = Path(run.logs_path).read_text("utf-8", "replace")
    if any(sig in logs for sig in _GENUINE_FAILURE_SIGNATURES):
        return False
    if run.exit_code in _INFRA_TRANSIENT_EXIT_CODES:
        return True
    return any(p in logs for p in _INFRA_TRANSIENT_PATTERNS)


@dataclass
class RealBackendSandbox:
    """Real FastAPI codegen + Docker execution for the R2.4.0b closed loop."""

    backend: FastAPIHexagonalBackend
    warning_filters: list[str] = field(
        default_factory=lambda: [
            # pytest 9 re-types the GC-time "coroutine was never awaited"
            # RuntimeWarning into PytestUnraisableExceptionWarning via its
            # unraisableexception hook (reporting it as a warning summary, exit 0).
            # Both must be errors for the broken artifact to surface as a real
            # failure whose stderr carries the operator's trigger signature.
            "error::RuntimeWarning",
            "error::pytest.PytestUnraisableExceptionWarning",
        ]
    )
    classifier: FailureClassifier = None  # type: ignore[assignment]
    _environment_cls: type = DockerExecutionEnvironment

    def __post_init__(self) -> None:
        if self.classifier is None:
            self.classifier = FailureClassifier()

    # -- ISR -> SystemModel (bridge; backend codegen consumes SystemModel) ----

    def _system_model(self, isr: ISR) -> SystemModel:
        """Synthesize a minimal typed SystemModel from the ISR identity.

        The async-resolution surface is appended separately from the ISR workflow
        graph; the SystemModel here only needs to be enough for the backend to
        emit a valid, importable bundle (main.py, tests/, requirements*).
        """
        return SystemModel(
            system_name=isr.system.name,
            requirements_ref=RequirementsReference(graph_id="r24", graph_hash="0"),
            capabilities=[BusinessCapability(id="cap-x", name="X")],
            data_models=[
                DataModelSpec(
                    id="dm-x", name="X", owning_service_id="svc-1",
                    fields=[
                        FieldSpec(name="id", type=AbstractFieldType.IDENTIFIER),
                        FieldSpec(name="name", type=AbstractFieldType.TEXT),
                    ],
                )
            ],
            security=SecurityModel(),
        )

    @staticmethod
    def _workflows(isr: ISR) -> list:
        out = []
        for module in isr.system.modules:
            out.extend(module.workflows)
        return out

    def _slug(self, root: str | Path) -> str:
        matches = sorted(Path(root).rglob("async_resolution.py"))
        if not matches:
            raise ValueError(f"no async_resolution.py generated under {root!r}")
        return matches[0].parent.name

    # -- real compile + run --------------------------------------------------

    def build(self, isr: ISR, workspace: str | None = None) -> CompiledCandidate:
        """Compile the ISR through the REAL backend, appending the async
        resolution module + its test. Materializes to ``workspace`` (tmp if None)."""
        model = self._system_model(isr)
        result = self.backend.generate(model)
        slug = result.system_name
        workflows = self._workflows(isr)
        result.files[f"{slug}/async_resolution.py"] = self.backend.async_resolution_module(workflows)
        result.files[f"{slug}/tests/test_async_resolution.py"] = _ASYNC_TEST_SOURCE.format(slug=slug)
        root = write_bundle(result, workspace or tempfile.mkdtemp(prefix="r24-bundle-"))
        return CompiledCandidate(
            source_root=str(root), compile_ok=True, artifact_hash=hash_artifact(root)
        )

    def run_tests(
        self, candidate: CompiledCandidate, warning_filters: list[str] | None = None
    ) -> TestRunResult:
        """Execute the candidate's suite in real Docker with strict warning-as-error.

        ``warning_filters`` defaults to the sandbox's filter spec (RuntimeWarning
        plus pytest's re-typed unraisable variant); callers may override.

        Transient infrastructure failures (pip/network/OOM during container
        setup, exit codes 2/125/137/143) are retried a bounded number of times so
        the benchmark stays stable under daemon load -- but only when the logs do
        NOT contain a genuine test-failure signature, so a real
        ``coroutine '...' was never awaited`` (exit 1) is never retried and still
        fails fast.
        """
        slug = self._slug(candidate.source_root)
        profile = self.backend.build_profile(slug)
        filters = warning_filters or self.warning_filters
        # The test_command is an injectable list (R2.4.0a contract): each filter
        # is its own [-W, spec] pair, and pytest is scoped to the async test that
        # exercises the generated async-resolution surface.
        test_command = [
            "python", "-m", "pytest",
            *(f for spec in filters for f in ("-W", spec)),
            "-v", f"{slug}/tests/test_async_resolution.py",
        ]
        env = self._environment_cls(
            test_command=test_command,
            runtime_image=profile.runtime_image,
            build_command=profile.build_command,
        )
        bundle = SystemDeploymentBundle(
            project_id=slug,
            backend_name=self.backend.backend_id,
            isr_hash="",
            path=candidate.source_root,
            artifacts=[],
            capability_manifest=None,
        )
        return self._run_with_retry(env, bundle)

    def _run_with_retry(self, env, bundle, attempts: int = 3) -> TestRunResult:
        # R2.7: each attempt is retained so a test whose outcome *varies* across
        # infra-retry attempts is attributed FLAKE (a deception vector) instead
        # of being masked into the final verdict. Genuine test failures are never
        # retried (they fail fast); only infra-transient failures retry.
        runs: list[TestRunResult] = [asyncio.run(env.run_verification(bundle))]
        if runs[-1].exit_code == 0:
            return self._attach_tests(runs[-1], bundle, runs)
        for _ in range(attempts - 1):
            if not _is_infra_transient(runs[-1]):
                break
            runs.append(asyncio.run(env.run_verification(bundle)))
            if runs[-1].exit_code == 0:
                break
        return self._attach_tests(runs[-1], bundle, runs)

    def _attach_tests(
        self, final: TestRunResult, bundle, all_runs: list[TestRunResult]
    ) -> TestRunResult:
        """Parse the final run's per-test outcomes from the backend's verbose
        output and attribute FLAKE across infra-retry attempts.

        Per-test parsing is the *backend adapter*'s job: the engine only ever
        consumes normalized ``TestExecution`` records, so the compiler stays
        pure (COMPILER PURITY INVARIANT).
        """
        from tiannara.domain.services.test_identity import parse_pytest_verbose

        def _logs(run: TestRunResult) -> str:
            if run.logs_path and os.path.exists(run.logs_path):
                return Path(run.logs_path).read_text("utf-8", "replace")
            return ""

        per_attempt = [
            parse_pytest_verbose(_logs(r), tree_root=bundle.path, attempt=i)
            for i, r in enumerate(all_runs)
        ]
        final_tests = per_attempt[-1]
        if len(per_attempt) > 1 and final_tests:
            # FLAKE = a test whose outcome differed across infra-retry attempts.
            outcomes_by_test: dict[str, set[str]] = {}
            for attempt_tests in per_attempt:
                for t in attempt_tests:
                    outcomes_by_test.setdefault(t.test_id, set()).add(t.outcome.value)
            flaky_ids = {
                tid for tid, outs in outcomes_by_test.items() if len(outs) > 1
            }
            if flaky_ids:
                final_tests = tuple(
                    TestExecution(
                        test_id=t.test_id,
                        outcome=t.outcome,
                        duration_seconds=t.duration_seconds,
                        content_hash=t.content_hash,
                        attempt=t.attempt,
                        flaky=True,
                    )
                    if t.test_id in flaky_ids
                    else t
                    for t in final_tests
                )
        total = len(final_tests)
        failed = sum(
            1 for t in final_tests
            if t.outcome in (TestOutcome.FAILED, TestOutcome.ERROR)
        )
        return TestRunResult(
            passed=(final.exit_code == 0 and failed == 0),
            exit_code=final.exit_code,
            total_tests=total,
            failed_tests=failed,
            duration_seconds=final.duration_seconds + sum(
                r.duration_seconds for r in all_runs
            ),
            logs_path=final.logs_path,
            tests=final_tests,
        )

    def to_evidence(self, run: TestRunResult) -> FailureEvidenceInput:
        """Bridge a real Docker run result into the R2.2 classifier's evidence.

        Real pytest output is verbose (pip notices + the full unraisable
        traceback with pytest internals). The coroutine-never-awaited
        signature that the classifier reads sits past the classifier's bounded
        excerpt in that noise, so we forward only the failure-relevant lines.
        (The classifier itself is untouched -- it stays pure rule-based R2.2.)
        """
        logs = ""
        if run.logs_path and os.path.exists(run.logs_path):
            logs = Path(run.logs_path).read_text("utf-8", "replace")
        focused = "\n".join(
            line for line in logs.splitlines()
            if any(key in line for key in (
                "coroutine", "was never awaited", "RuntimeWarning", "FAILED",
                "failed", "async_resolution", "test_orchestration", "1 failed",
                "Error", "assert",
            ))
        )
        stderr = focused or logs[:2000]
        return FailureEvidenceInput(
            execution_id=f"r24-run-{run.exit_code}",
            backend_id=self.backend.backend_id,
            phase=FailurePhase.TEST,
        command=(
            ("pytest",)
            + tuple(f for spec in self.warning_filters for f in ("-W", spec))
            + ("-v",)
        ),
            exit_code=run.exit_code,
            stdout="",
            stderr=stderr,
        )

    def observe(self, run: TestRunResult) -> FailureObservation | None:
        return self.classifier.classify(self.to_evidence(run))
