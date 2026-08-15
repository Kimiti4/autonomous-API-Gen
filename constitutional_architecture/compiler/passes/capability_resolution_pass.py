from __future__ import annotations

from constitutional_architecture.compiler.capability import Capability, CapabilityResolver
from constitutional_architecture.compiler.compiler_context import CompilerContext
from constitutional_architecture.compiler.pass_interface import CompilerPass, PassResult


class CapabilityResolutionPass(CompilerPass):
    @property
    def identifier(self) -> str:
        return "capability_resolution"

    @property
    def description(self) -> str:
        return "Resolve abstract capability contracts to backend-specific implementations"

    @property
    def dependencies(self) -> list[str]:
        return ["optimization"]

    @property
    def input_requirements(self) -> set[str]:
        return {"isr_optimized"}

    @property
    def output_guarantees(self) -> set[str]:
        return {"capabilities_resolved"}

    def execute(self, ctx: CompilerContext) -> PassResult:
        isr = ctx.isr
        required: set[Capability] = set()

        for module in isr.system.modules:
            for policy in module.policies:
                if policy.strategy:
                    strat = policy.strategy.lower()
                    if "oauth" in strat:
                        required.add(Capability.OAUTH2)
                    elif "jwt" in strat:
                        required.add(Capability.JWT_AUTH)

            for iface in module.interfaces:
                if iface.interface_type.value == "rest":
                    required.add(Capability.REST_API)
                    required.add(Capability.INPUT_VALIDATION)
                    required.add(Capability.SERIALIZATION)

            if module.entities:
                required.add(Capability.ORM)
                required.add(Capability.MIGRATIONS)

            if module.services:
                required.add(Capability.VALIDATION)

        required.add(Capability.STRUCTURED_LOGGING)
        required.add(Capability.HEALTH_CHECKS)
        required.add(Capability.CONTAINERIZATION)

        dep = isr.system.deployment
        if dep:
            if dep.monitoring.metrics_enabled:
                required.add(Capability.METRICS)
            if dep.monitoring.tracing_enabled:
                required.add(Capability.DISTRIBUTED_TRACING)

        metrics = {"capabilities_required": len(required), "capabilities": [c.value for c in required]}

        for backend_name in ctx.config.target_backends:
            try:
                capability_map = CapabilityResolver.resolve(backend_name, required)
                ctx.capability_contracts[backend_name] = {
                    cap.value: details for cap, details in capability_map.mappings.items()
                }
            except ValueError as e:
                ctx.diagnostics.warning("COMP-CAP-001", f"Capability resolution for '{backend_name}' failed: {e}")

        ctx.diagnostics.info("COMP-CAP-002", f"Resolved {len(required)} capability(ies) across {len(ctx.config.target_backends)} backend(s)")
        return PassResult(success=True, description=f"Resolved {len(required)} capabilities", metrics=metrics)
