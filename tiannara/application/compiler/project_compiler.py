"""Cap-C Phase 16: ProjectCompiler — the autonomous intent->artifact pipeline.

Composes Cap-A (IntentCompiler) with the Cap-C registration/derivation/
selection/execution seams into a single ``compile_intent`` entry point. Returns
a full-provenance report; raises ``ProjectCompilationError`` when execution or
verification fails.

Verification is best-effort and shape-driven: a backend output exposing the
CompilationResult shape (system_name + files) is materialized and run through
BundleVerifier; outputs that don't are marked absent (``verification_report=None``
with a reason) — never a silent pass.
"""

from __future__ import annotations

import hashlib
import tempfile
from dataclasses import dataclass
from typing import Any

from tiannara.application.compiler.build_profile import BackendBuildProfile, make_verifier
from tiannara.application.compiler.derivation import (
    derive_compilation_requirements,
)
from tiannara.application.compiler.executor import CompilationExecutor
from tiannara.application.compiler.registry import CompilerRegistry
from tiannara.application.compiler.selector import (
    BackendSelectionError,
    SelectionPolicy,
    plan_compilation,
    plan_compilation_across_backends,
)
from tiannara.application.compiler.verification import BundleVerificationReport
from tiannara.application.compiler.writer import write_bundle
from tiannara.domain.models.backend_declaration import PlannedCompilation
from tiannara.domain.models.compilation import CompilationResult
from tiannara.domain.ports import IntentCompiler


class ProjectCompilationError(ValueError):
    """Raised when the autonomous compilation cannot produce a verified artifact."""


@dataclass(frozen=True)
class ProjectOutcome:
    planned: PlannedCompilation
    status: str  # "success" | "failed"
    result: Any  # opaquely the backend's generate() output
    error: str | None
    verification_report: BundleVerificationReport | None
    verification_reason: str


@dataclass(frozen=True)
class ProjectCompilationReport:
    statement_hash: str
    isr_hash: str
    plan_id: str
    outcomes: list[ProjectOutcome]
    ok: bool
    #: Which SelectionPolicy chose the backends. Optional so legacy
    #: constructors keep working; populated from plan.policy_name.
    policy_name: str | None = None


class ProjectCompiler:
    def __init__(
        self,
        intent_compiler: IntentCompiler,
        registry: CompilerRegistry,
        policy: SelectionPolicy | None = None,
        executor: CompilationExecutor | None = None,
        plan_all: bool = False,
    ) -> None:
        self._intent_compiler = intent_compiler
        self._registry = registry
        self._policy = policy or SelectionPolicy()
        self._executor = executor or CompilationExecutor(registry)
        # Phase-31 calibration seam: when True, plan *every* satisfying backend
        # per requirement (select-all) so the same ISR compiles to each backend.
        # Default False preserves the existing single-best selection semantics.
        self._plan_all = plan_all

    def compile_intent(self, statement: str, hints: dict) -> ProjectCompilationReport:
        # 1. Front-end -> ISR envelope
        isr = self._intent_compiler.compile(statement, hints)
        # 2. Typed payload
        model = isr.system_model()
        if model is None:
            raise ProjectCompilationError(
                "intent compiler returned a legacy (non-typed) ISR; the pure "
                "Cap-C pipeline requires a typed SystemModel payload"
            )
        # 3. Derive requirements
        requirements = derive_compilation_requirements(model)
        # 4. Plan (select-all when calibrating, single-best otherwise)
        planner = (
            plan_compilation_across_backends
            if self._plan_all
            else plan_compilation
        )
        try:
            plan = planner(self._registry, requirements, self._policy)
        except BackendSelectionError as exc:
            raise ProjectCompilationError(
                f"no registered backend can satisfy the compiled intent: {exc}"
            ) from exc
        # 5. Execute (collect-all; never raises)
        execution = self._executor.execute(plan, model)
        # 6. Verification
        outcomes: list[ProjectOutcome] = []
        verification_blocked = False
        for outcome in execution.outcomes:
            report, reason = self._verify(outcome)
            outcomes.append(
                ProjectOutcome(
                    planned=outcome.planned,
                    status=outcome.status,
                    result=outcome.result,
                    error=outcome.error,
                    verification_report=report,
                    verification_reason=reason,
                )
            )
            if report is not None and not report.ok:
                verification_blocked = True
        ok = execution.ok and not verification_blocked
        # 7. Report
        if not ok:
            failed = [o for o in outcomes if o.status == "failed"]
            if failed:
                raise ProjectCompilationError(
                    f"compilation failed for {len(failed)} backend(s); "
                    f"first error: {failed[0].error}"
                )
            raise ProjectCompilationError(
                "one or more backends failed verification"
            )
        return ProjectCompilationReport(
            statement_hash=hashlib.sha256(
                statement.encode("utf-8")
            ).hexdigest(),
            isr_hash=isr.content_hash(),
            plan_id=plan.plan_id,
            policy_name=plan.policy_name,
            outcomes=outcomes,
            ok=ok,
        )

    def _verify(self, outcome: Any) -> tuple[BundleVerificationReport | None, str]:
        if outcome.status != "success":
            return None, "backend execution failed"
        result = outcome.result
        if not isinstance(result, CompilationResult):
            return (
                None,
                "backend result is not a CompilationResult; no verification shape",
            )
        slug = result.system_name
        # Read the verification contract from the backend (Phase 19), not from
        # the meta-compiler. Fallbacks keep the path safe if a backend omits one.
        backend = self._registry.backend(outcome.planned.backend_id)
        build_profile: BackendBuildProfile | None = getattr(
            backend, "build_profile", None
        )
        if callable(build_profile):
            profile = build_profile(slug)
        else:
            profile = BackendBuildProfile(
                language="python",
                required_files=(f"{slug}/main.py",),
                verifier_kind="python",
            )
        verifier = make_verifier(
            profile.language,
            package=slug,
            required_files=list(profile.required_files),
        )
        with tempfile.TemporaryDirectory() as tmp:
            write_bundle(result, tmp)
            report = verifier.verify(tmp)
        return report, "" if report.ok else "verification failed"
