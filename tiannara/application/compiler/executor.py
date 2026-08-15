"""Cap-C Phase 16: CompilationExecutor.

Executes a CompilationPlan by invoking each selected backend's pure
``generate(system_model)`` path. It never touches the legacy
``compile(isr, genome, output_dir)`` contract used by ExecutionPipeline.

Collect-all semantics: every planned backend is attempted; failures are
recorded with diagnostics rather than raised. Whether a non-empty failure set
is fatal is the orchestrator's (ProjectCompiler's) decision — the executor
reports, it does not short-circuit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tiannara.application.compiler.registry import CompilerRegistry
from tiannara.domain.models.backend_declaration import (
    CompilationPlan,
    PlannedCompilation,
)


@dataclass(frozen=True)
class BackendCompilationOutcome:
    """Result of attempting one planned backend compilation."""

    planned: PlannedCompilation
    status: str  # "success" | "failed"
    result: Any  # backend's generate() output, stored opaquely
    error: str | None

    @property
    def ok(self) -> bool:
        return self.status == "success"


@dataclass(frozen=True)
class ExecutionReport:
    plan_id: str
    outcomes: list[BackendCompilationOutcome]

    @property
    def ok(self) -> bool:
        return all(outcome.ok for outcome in self.outcomes)


class CompilationExecutor:
    """Drives a CompilationPlan through its selected backends via generate()."""

    def __init__(self, registry: CompilerRegistry) -> None:
        self._registry = registry

    def execute(
        self,
        plan: CompilationPlan,
        system_model: Any,
    ) -> ExecutionReport:
        outcomes: list[BackendCompilationOutcome] = []
        for planned in plan.planned:
            backend = self._registry.backend(planned.backend_id)
            try:
                result = backend.generate(system_model)
            except Exception as exc:  # noqa: BLE001 - collect-all by design
                outcomes.append(
                    BackendCompilationOutcome(
                        planned=planned,
                        status="failed",
                        result=None,
                        error=str(exc),
                    )
                )
                continue
            outcomes.append(
                BackendCompilationOutcome(
                    planned=planned,
                    status="success",
                    result=result,
                    error=None,
                )
            )
        return ExecutionReport(plan_id=plan.plan_id, outcomes=outcomes)
