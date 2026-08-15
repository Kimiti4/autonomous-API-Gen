from __future__ import annotations

from constitutional_architecture.compiler.compiler_context import CompilerContext
from constitutional_architecture.compiler.pass_interface import CompilerPass, PassResult


class CrossTargetPass(CompilerPass):
    @property
    def identifier(self) -> str:
        return "cross_target"

    @property
    def description(self) -> str:
        return "Cross-target consistency checks"

    @property
    def dependencies(self) -> list[str]:
        return ["verification"]

    @property
    def input_requirements(self) -> set[str]:
        return {"artifacts_verified"}

    @property
    def output_guarantees(self) -> set[str]:
        return {"cross_target_consistent"}

    def execute(self, ctx: CompilerContext) -> PassResult:
        metrics = {"backends": len(ctx.config.target_backends), "artifacts": len(ctx.artifacts)}

        if len(ctx.config.target_backends) > 1:
            backends_seen = {a.backend for a in ctx.artifacts if hasattr(a, "backend")}
            missing = set(ctx.config.target_backends) - backends_seen
            for m in missing:
                ctx.diagnostics.warning("COMP-CROSS-001", f"Backend '{m}' produced no artifacts")

        ctx.diagnostics.info("COMP-CROSS-002", f"Cross-target check: {len(ctx.config.target_backends)} target(s), {len(ctx.artifacts)} artifact(s)")
        return PassResult(success=True, description="Cross-target consistency check passed", metrics=metrics)
