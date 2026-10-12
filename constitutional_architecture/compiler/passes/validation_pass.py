from __future__ import annotations

from constitutional_architecture.compiler.compiler_context import CompilerContext
from constitutional_architecture.compiler.pass_interface import CompilerPass, PassResult


class ValidationPass(CompilerPass):
    @property
    def identifier(self) -> str:
        return "validation"

    @property
    def description(self) -> str:
        return "Validate ISR integrity, type safety, and invariants"

    @property
    def output_guarantees(self) -> set[str]:
        return {"isr_validated"}

    def execute(self, ctx: CompilerContext) -> PassResult:
        try:
            from constitutional_architecture.validation.checker import ArchitecturalTypeChecker
            from constitutional_architecture.engine.isr_adapter import isr_to_graph
            graph = isr_to_graph(ctx.isr)
            result = ArchitecturalTypeChecker().validate(graph)
        except Exception as exc:
            # Validation is a safety boundary. A broken/unavailable validator
            # cannot be treated as evidence that the ISR is valid.
            ctx.diagnostics.error(
                "COMP-VAL-003",
                f"ISR validation could not be completed: {type(exc).__name__}: {exc}",
            )
            return PassResult(
                success=False,
                description="ISR validation blocked: validator failed or unavailable",
                metrics={"valid": False, "validation_unavailable": True},
            )

        errors = list(getattr(result, "errors", ()))
        warnings = list(getattr(result, "warnings", ()))
        passed = bool(getattr(result, "passed", False)) and not errors
        if not passed:
            ctx.diagnostics.error(
                "COMP-VAL-001",
                f"ISR validation failed: {len(errors)} errors, {len(warnings)} warnings",
            )
            return PassResult(
                success=False,
                description="ISR validation failed",
                metrics={"valid": False, "errors": len(errors), "warnings": len(warnings)},
            )

        ctx.diagnostics.info(
            "COMP-VAL-002",
            f"ISR validated: {len(errors)} errors, {len(warnings)} warnings",
        )
        return PassResult(
            success=True,
            description="ISR validation passed",
            metrics={"valid": True, "errors": len(errors), "warnings": len(warnings)},
        )