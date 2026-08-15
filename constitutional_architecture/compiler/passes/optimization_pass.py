from __future__ import annotations

from constitutional_architecture.compiler.compiler_context import CompilerContext
from constitutional_architecture.compiler.pass_interface import CompilerPass, PassResult
from constitutional_architecture.compiler.quality.optimization_engine import OptimizationEngine


class OptimizationPass(CompilerPass):
    @property
    def identifier(self) -> str:
        return "optimization"

    @property
    def description(self) -> str:
        return "Architecture-preserving optimizations (no semantic change)"

    @property
    def dependencies(self) -> list[str]:
        return ["normalization"]

    @property
    def input_requirements(self) -> set[str]:
        return {"isr_normalized"}

    @property
    def output_guarantees(self) -> set[str]:
        return {"isr_optimized", "semantics_preserved"}

    def execute(self, ctx: CompilerContext) -> PassResult:
        engine = OptimizationEngine()
        level = ctx.config.optimization_level.value
        records = engine.optimize(ctx, level=level)

        ctx.diagnostics.info("COMP-OPT-001", f"Applied {len(records)} optimization(s) at level {level}")

        return PassResult(
            success=True,
            description=f"Applied {len(records)} optimizations",
            metrics={
                "optimizations_applied": len(records),
                "optimization_level": level,
                "optimization_names": [r.name for r in records],
            },
        )
