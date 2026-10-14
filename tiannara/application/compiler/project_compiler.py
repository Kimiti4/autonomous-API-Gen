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
from dataclasses import dataclass, field
from typing import Any

from tiannara.application.compiler.build_profile import BackendBuildProfile, make_verifier
from tiannara.application.compiler.documentation import validate_generated_documentation
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
from tiannara.domain.models.semantic_resolution import (
    SemanticResolutionRecord,
    require_taskflow_semantics,
)
from tiannara.domain.ports import IntentCompiler
from tiannara.application.intent.prompts import derive_system_id
from tiannara.application.intent.prompts import normalize
from tiannara.application.compiler.source_projection import SourceProjectionContext
from tiannara.application.compiler.source_coverage import SourceGraphCoverageReport
from tiannara.domain.models.requirement_graph import RequirementGraph


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
    #: Provenance from the actual intent-compilation calls. Replay records are
    #: retained for regression accounting but are never treated as live evidence.
    model_call_records: list = field(default_factory=list)
    generation_mode: str = "unknown"
    #: Which SelectionPolicy chose the backends.
    policy_name: str | None = None


class ProjectCompiler:
    def __init__(
        self,
        intent_compiler: IntentCompiler,
        registry: CompilerRegistry,
        policy: SelectionPolicy | None = None,
        executor: CompilationExecutor | None = None,
        plan_all: bool = False,
        taskflow_semantic_gate: bool = False,
    ) -> None:
        self._intent_compiler = intent_compiler
        self._registry = registry
        self._policy = policy or SelectionPolicy()
        self._executor = executor or CompilationExecutor(registry)
        # Phase-31 calibration seam: when True, plan *every* satisfying backend
        # per requirement (select-all) so the same ISR compiles to each backend.
        # Default False preserves the existing single-best selection semantics.
        self._plan_all = plan_all
        self._taskflow_semantic_gate = taskflow_semantic_gate

    def compile_intent(self, statement: str, hints: dict) -> ProjectCompilationReport:
        # 1. Front-end -> ISR envelope. Use compile_full so model-call
        # provenance is retained for the evidence boundary.
        system_id = hints.get("system_id") or derive_system_id(statement)
        if self._taskflow_semantic_gate:
            compilation = self._intent_compiler.compile_full(
                statement, system_id, taskflow_semantic_gate=True
            )
            record = compilation.semantic_resolution_record
            if not isinstance(record, SemanticResolutionRecord):
                raise ProjectCompilationError(
                    "TaskFlow semantic gate is enabled but no validated resolution ledger was returned"
                )
            require_taskflow_semantics(compilation.requirement_graph, record)
        else:
            compilation = self._intent_compiler.compile_full(statement, system_id)
        isr = compilation.isr
        model_call_records = list(compilation.call_records)
        statuses = {getattr(record, "status", None) for record in model_call_records}
        if not model_call_records:
            generation_mode = "no_model_calls"
        elif any(str(status).lower().endswith("replayed") for status in statuses):
            generation_mode = "replay"
        elif all(str(status).lower().endswith("live") for status in statuses):
            generation_mode = "live"
        else:
            generation_mode = "mixed_or_failed"
        # 2. Typed payload
        model = isr.system_model()
        if model is None:
            raise ProjectCompilationError(
                "intent compiler returned a legacy (non-typed) ISR; the pure "
                "Cap-C pipeline requires a typed SystemModel payload"
            )
        # Fail closed at the application compiler boundary. The current
        # capability requirements and backend port do not yet accept typed
        # authorization obligations, so merely passing the TaskFlow gate must
        # not authorize backend generation. This guard is intentionally
        # conservative until a backend/runtime contract consumes and enforces
        # the obligations and the acceptance suite proves workspace isolation.
        if self._taskflow_semantic_gate:
            obligations = getattr(
                compilation, "authorization_semantic_obligations", None
            )
            if obligations is None:
                raise ProjectCompilationError(
                    "TaskFlow authorization gate is enabled but typed authorization "
                    "obligations are missing; backend generation is blocked"
                )
            raise ProjectCompilationError(
                "TaskFlow authorization obligations were resolved by the intent "
                "compiler, but no registered backend/runtime consumer currently "
                "proves enforcement; generation remains blocked"
            )
        # Mandatory provenance contract for every non-TaskFlow generation path.
        # A compiler adapter that does not return the frozen source context is
        # exploratory only; it cannot proceed to backend selection.
        source_context = getattr(compilation, "source_projection_context", None)
        graph = getattr(compilation, "requirement_graph", None)
        if not isinstance(source_context, SourceProjectionContext):
            raise ProjectCompilationError(
                "generation blocked: intent compiler returned no validated source projection context"
            )
        if not isinstance(graph, RequirementGraph):
            raise ProjectCompilationError(
                "generation blocked: intent compiler returned no typed requirement graph"
            )
        expected_snapshot_hash = hashlib.sha256(statement.encode("utf-8")).hexdigest()
        if source_context.snapshot_sha256 != expected_snapshot_hash:
            raise ProjectCompilationError(
                "generation blocked: source projection context does not match the exact caller statement bytes"
            )
        if (
            source_context.graph_id != graph.graph_id
            or source_context.graph_sha256 != graph.content_hash()
            or graph.provenance.source_statement_hash
            != normalize(statement).source_statement_hash
        ):
            raise ProjectCompilationError(
                "generation blocked: source-to-graph provenance binding is stale or substituted"
            )

        # A graph hash binds identity but cannot prove that every requirement-
        # bearing source unit survived extraction. Until the trusted intake path
        # supplies a coverage report, generic generation is blocked. Never infer
        # completeness from a matching source/context/graph hash.
        coverage = getattr(compilation, "source_graph_coverage_report", None)
        if not isinstance(coverage, SourceGraphCoverageReport):
            raise ProjectCompilationError(
                "generation blocked: trusted source-unit-to-graph coverage report is missing"
            )
        if (
            not coverage.complete
            or coverage.source_sha256 != source_context.snapshot_sha256
            or coverage.graph_sha256 != source_context.graph_sha256
        ):
            blockers = "; ".join(coverage.blockers) or "source/graph identity mismatch"
            raise ProjectCompilationError(
                "generation blocked: source-unit-to-graph coverage is incomplete or stale: "
                + blockers
            )

        # The typed SystemModel must identify the exact same requirement
        # graph. Matching source and graph hashes alone do not prove that the
        # model synthesis retained the graph's identity.
        requirements_ref = getattr(model, "requirements_ref", None)
        if (
            requirements_ref is None
            or requirements_ref.graph_id != graph.graph_id
            or requirements_ref.graph_hash != graph.content_hash()
        ):
            raise ProjectCompilationError(
                "generation blocked: SystemModel requirement reference does not bind to the active source graph"
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
            if report is None:
                verification_blocked = True
            elif not report.ok:
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
            model_call_records=model_call_records,
            generation_mode=generation_mode,
        )

    def _verify(self, outcome: Any) -> tuple[BundleVerificationReport | None, str]:
        if outcome.status != "success":
            return None, "backend execution failed"
        result = outcome.result
        if not isinstance(result, CompilationResult):
            return (
                None,
                "UNKNOWN: backend result is not a CompilationResult; certification blocked",
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
        readme = result.files.get("README.md", "")
        doc = validate_generated_documentation(
            readme=readme,
            system_name=result.system_name,
            required_capabilities=[str(c.value) for c in result.capability_manifest.capabilities],
            selected_backend=outcome.planned.backend_id,
            generated_paths=result.file_paths(),
        )
        if not doc.passed:
            return None, "documentation certification failed: " + "; ".join(doc.blockers)
        verifier = make_verifier(
            profile.language,
            package=slug,
            required_files=list(profile.required_files),
        )
        with tempfile.TemporaryDirectory() as tmp:
            write_bundle(result, tmp)
            report = verifier.verify(tmp)
        return report, "" if report.ok else "verification failed"
