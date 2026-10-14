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
        binding = ctx.source_binding
        if ctx.config.require_source_binding and binding is None:
            ctx.diagnostics.error(
                "COMP-SOURCE-BINDING-001",
                "Required source/graph/ISR binding is missing",
            )
            return PassResult(
                success=False,
                description="Source binding blocked: required binding is missing",
                metrics={"source_binding_valid": False, "source_binding_missing": True},
            )
        if binding is not None:
            try:
                from constitutional_architecture.compiler.source_binding import (
                    verify_constitutional_source_binding,
                )
                report = verify_constitutional_source_binding(binding=binding, isr=ctx.original_isr)
            except Exception as exc:
                ctx.diagnostics.error(
                    "COMP-SOURCE-BINDING-002",
                    f"Source binding verification unavailable: {type(exc).__name__}: {exc}",
                )
                return PassResult(
                    success=False,
                    description="Source binding blocked: verification unavailable",
                    metrics={"source_binding_valid": False, "source_binding_error": type(exc).__name__},
                )
            if not report.complete:
                ctx.diagnostics.error(
                    "COMP-SOURCE-BINDING-003",
                    "Source/graph/ISR binding failed: " + "; ".join(report.blockers),
                )
                return PassResult(
                    success=False,
                    description="Source binding failed",
                    metrics={
                        "source_binding_valid": False,
                        "source_sha256": report.source_sha256,
                        "graph_sha256": report.graph_sha256,
                        "isr_sha256": report.isr_sha256,
                        "blockers": list(report.blockers),
                    },
                )
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