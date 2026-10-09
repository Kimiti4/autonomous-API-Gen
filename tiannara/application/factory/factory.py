"""SoftwareFactory -- Phase 18 closed-loop orchestrator.

Composition over existing ports (no parallel runner):
    ProjectCompiler (P16) -> RepositoryMaterializer (P17)
        -> BundleVerifier (static) + ExecutionEnvironment (build/test)
        -> bounded, evidenced repair loop -> FitnessVector

The factory composes; it owns no codegen and no intelligence. Static
verification is performed by the independent BundleVerifier; runtime
verification by ExecutionEnvironment.run_verification (async, bridged).
Repair is last-resort and its output is always re-verified by the independent
verifier -- the repairer is never trusted.

``ExecutionEnvironment.run_verification`` is async (tree contract); ``run`` is
synchronous, so the async env is bridged via ``asyncio.run``. Callers in an
already-running event loop must use the async entry point provided by the
harness instead.
"""

from __future__ import annotations

import asyncio
import tempfile
from typing import Optional

from tiannara.domain.ports.repair import RepairRequest

from .fitness import build_fitness
from .repair_providers import NullRepairProvider
from .report import SoftwareFactoryError, SoftwareFactoryReport, VerificationOutcome


class _FailedRun:
    """Duck-typed stand-in when an execution environment raises."""

    def __init__(self, error: str) -> None:
        self.passed = False
        self.exit_code = -1
        self.total_tests = 0
        self.failed_tests = 0
        self.duration_seconds = 0.0
        self.logs_path = None
        self.error = error

    @property
    def pass_rate(self) -> float:
        return 0.0


class SoftwareFactory:
    """Orchestrates build -> verify -> repair -> re-verify -> fitness.

    Verification is fail-closed by default: a stage that did not run (no
    verifier configured, no execution environment, no test command, an
    unevaluated run) is NOT a pass. The ``require_static`` / ``require_runtime``
    constructor flags are explicit authorization seams for callers that
    deliberately omit a stage (e.g. static-only experiments); they may only
    excuse an *absent* stage, never a stage that ran and failed.
    """

    def __init__(
        self,
        project_compiler,
        materializer,
        execution_environment=None,
        repair_provider=None,
        verifier_factory=None,
        result_resolver=None,
        max_repair_attempts: int = 2,
        evidence_sink: Optional[callable] = None,
        require_static: bool = True,
        require_runtime: bool = True,
    ) -> None:
        self._project_compiler = project_compiler
        self._materializer = materializer
        self._execution_environment = execution_environment
        self._repair_provider = repair_provider or NullRepairProvider()
        self._verifier_factory = verifier_factory
        self._result_resolver = result_resolver
        self._max_repair_attempts = max_repair_attempts
        self._evidence_sink = evidence_sink
        self._require_static = require_static
        self._require_runtime = require_runtime

    def run(
        self,
        statement: str,
        hints: dict | None = None,
        out_root: str | None = None,
        force: bool = False,
    ) -> SoftwareFactoryReport:
        compilation_report = self._project_compiler.compile_intent(
            statement, hints or {}
        )

        if out_root is None:
            out_root = tempfile.mkdtemp(prefix="tiannara-factory-")

        materialization = self._materializer.materialize(
            compilation_report, out_root=out_root, force=force
        )
        bundles = tuple(getattr(materialization, "bundles", ()) or ())
        if not bundles:
            raise SoftwareFactoryError("materialization produced no bundles")

        outcomes = []
        for bundle in bundles:
            compilation_result = self._resolve_result(bundle, compilation_report)
            outcomes.append(self._verify_and_repair(bundle, compilation_result))

        fitness = build_fitness(outcomes, self._max_repair_attempts)
        ok = bool(outcomes) and all(o.ok for o in outcomes)
        report = SoftwareFactoryReport(
            statement_hash=getattr(compilation_report, "statement_hash", ""),
            isr_hash=getattr(compilation_report, "isr_hash", ""),
            plan_id=getattr(compilation_report, "plan_id", ""),
            policy_name=getattr(compilation_report, "policy_name", None),
            materialization=materialization,
            verification_outcomes=tuple(outcomes),
            fitness=fitness,
            ok=ok,
        )

        if self._evidence_sink is not None:
            try:
                self._evidence_sink(report)
            except Exception:
                pass

        if not ok:
            raise SoftwareFactoryError(
                "one or more bundles failed verification after repair",
                report=report,
            )
        return report

    # -- internals ---------------------------------------------------------

    def _resolve_result(self, bundle, compilation_report):
        if self._result_resolver is not None:
            return self._result_resolver(bundle, compilation_report)
        outcomes = list(getattr(compilation_report, "outcomes", ()) or ())
        results = []
        for outcome in outcomes:
            result = getattr(outcome, "result", None)
            if result is None:
                continue
            planned = getattr(outcome, "planned", None)
            backend_id = getattr(planned, "backend_id", None)
            results.append((result, backend_id))
        # Multi-backend fleets namespace every bundle under the same
        # project_id, so system_name alone is ambiguous: match the bundle's
        # backend first, then fall back to the legacy single-backend match.
        bundle_backend = getattr(bundle, "backend_name", None)
        bundle_project = getattr(bundle, "project_id", None)
        if bundle_backend is not None:
            for result, backend_id in results:
                if (
                    backend_id == bundle_backend
                    and getattr(result, "system_name", None) == bundle_project
                ):
                    return result
            for result, backend_id in results:
                if backend_id == bundle_backend:
                    return result
        for result, _backend_id in results:
            if getattr(result, "system_name", None) == bundle_project:
                return result
        return results[0][0] if results else None

    def _verify_and_repair(self, bundle, compilation_result) -> VerificationOutcome:
        bundle_path = str(getattr(bundle, "path", ""))
        source_artifacts = dict(getattr(compilation_result, "files", {}) or {})
        if compilation_result is None:
            source_artifacts = {}

        verifier = None
        if self._verifier_factory is not None and compilation_result is not None:
            verifier = self._verifier_factory(compilation_result)

        static_report, test_result = self._verify_once(bundle, bundle_path, verifier)
        repair_attempts = 0
        repaired = False

        while not self._all_ok(static_report, test_result) \
                and repair_attempts < self._max_repair_attempts:
            repair_attempts += 1
            signature = self._classify(static_report, test_result)
            request = RepairRequest(
                bundle_path=bundle_path,
                failure_signature=signature,
                static_report=static_report,
                test_result=test_result,
                source_artifacts=source_artifacts,
                attempt=repair_attempts,
                max_attempts=self._max_repair_attempts,
            )
            actions = self._repair_provider.diagnose(request)
            if not actions:
                break
            repair_report = self._repair_provider.apply(bundle_path, actions)
            if not getattr(repair_report, "applied", False):
                break
            repaired = True
            static_report, test_result = self._verify_once(bundle, bundle_path, verifier)

        ok = self._all_ok(static_report, test_result)
        backend_id = (
            getattr(compilation_result, "backend_id", None)
            if compilation_result is not None
            else None
        )
        return VerificationOutcome(
            bundle_backend_id=backend_id or "",
            static_ok=self._static_stage_ok(static_report),
            static_report=static_report,
            test_result=test_result,
            repair_attempts=repair_attempts,
            repaired=repaired,
            ok=ok,
        )

    def _verify_once(self, bundle, bundle_path, verifier):
        static_report = verifier.verify(bundle_path) if verifier is not None else None
        test_result = None
        if self._static_stage_ok(static_report) and self._execution_environment is not None:
            try:
                coro = self._execution_environment.run_verification(bundle)
                if asyncio.iscoroutine(coro):
                    test_result = asyncio.run(coro)
                else:
                    test_result = coro
            except Exception as exc:  # noqa: BLE001 -- capture as a failed run
                test_result = _FailedRun(repr(exc))
        return static_report, test_result

    def _static_stage_ok(self, static_report) -> bool:
        if static_report is None:
            return not self._require_static
        return bool(getattr(static_report, "ok", False))

    def _runtime_stage_ok(self, test_result) -> bool:
        if test_result is None:
            return not self._require_runtime
        if not getattr(test_result, "evaluated", True):
            return not self._require_runtime
        return bool(getattr(test_result, "passed", False))

    def _all_ok(self, static_report, test_result) -> bool:
        return self._static_stage_ok(static_report) and self._runtime_stage_ok(
            test_result
        )

    def _classify(self, static_report, test_result) -> str:
        if static_report is not None and not getattr(static_report, "ok", True):
            if getattr(static_report, "missing_files", None):
                return "static:missing_files"
            if getattr(static_report, "syntax_errors", None):
                return "static:syntax_errors"
            if getattr(static_report, "dependency_violations", None):
                return "static:dependency_violations"
            return "static:unknown"
        if static_report is None and self._require_static:
            return "static:absent"
        if test_result is not None and not getattr(test_result, "evaluated", True):
            return "runtime:not_evaluated"
        if test_result is not None and not getattr(test_result, "passed", True):
            return "runtime:test_failures"
        if test_result is None and self._require_runtime:
            return "runtime:absent"
        return "unknown"
