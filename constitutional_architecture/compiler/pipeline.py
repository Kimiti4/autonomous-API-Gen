"""
Compiler Pipeline — 8-Pass Compilation from ISR to Production Code.

Each pass is independently testable, replaceable, and extensible.
The pipeline transforms a validated ISR through successive passes
until production artifacts are emitted.

Pass order:
1. Validation — Architectural type checking, completeness verification
2. Normalization — Canonical form, deterministic ordering
3. Optimization — Semantics-preserving transforms
4. Capability Resolution — Abstract capability contracts
5. Lowering — ISR → BIR
6. Code Generation — Backend compilation
7. Verification — Artifact verification
8. Cross-Target — Cross-target consistency
"""

from __future__ import annotations

import time
from typing import Any, Optional

from constitutional_architecture.compiler.backends.backend_registry import BackendRegistry
from constitutional_architecture.compiler.cache.compilation_cache import CompilationCache
from constitutional_architecture.compiler.compilation_config import CompilationConfig as CompilationConfigAlias
from constitutional_architecture.compiler.compiler_context import CompilerContext

CompilerConfig = CompilationConfigAlias
CompilationConfig = CompilationConfigAlias
from constitutional_architecture.compiler.compiler_result import (
    CapabilityReport, CompilationResult, VerificationResult,
)
from constitutional_architecture.compiler.observability.compiler_events import (
    CompilerEvent, CompilerEventBus, CompilerEventType,
)
from constitutional_architecture.compiler.observability.compiler_metrics import CompilerMetrics
from constitutional_architecture.compiler.pass_manager import PassManager
from constitutional_architecture.compiler.pass_registry import PassRegistry
from constitutional_architecture.isr.model.isr import ISR


def build_default_pipeline() -> PassRegistry:
    from constitutional_architecture.compiler.passes.validation_pass import ValidationPass
    from constitutional_architecture.compiler.passes.normalization_pass import NormalizationPass
    from constitutional_architecture.compiler.passes.optimization_pass import OptimizationPass
    from constitutional_architecture.compiler.passes.capability_resolution_pass import CapabilityResolutionPass
    from constitutional_architecture.compiler.passes.lowering_pass import LoweringPass
    from constitutional_architecture.compiler.passes.code_generation_pass import CodeGenerationPass
    from constitutional_architecture.compiler.passes.verification_pass import VerificationPass
    from constitutional_architecture.compiler.passes.cross_target_pass import CrossTargetPass

    registry = PassRegistry()
    registry.register(ValidationPass())
    registry.register(NormalizationPass())
    registry.register(OptimizationPass())
    registry.register(CapabilityResolutionPass())
    registry.register(LoweringPass())
    registry.register(CodeGenerationPass())
    registry.register(VerificationPass())
    registry.register(CrossTargetPass())
    return registry


def build_default_backend_registry() -> BackendRegistry:
    from constitutional_architecture.compiler.backends.fastapi_backend import FastAPIBackend
    registry = BackendRegistry()
    registry.register(FastAPIBackend())
    return registry


class CompilerPipeline:
    def __init__(
        self,
        backend_registry: Optional[BackendRegistry] = None,
        pass_registry: Optional[PassRegistry] = None,
        cache: Optional[CompilationCache] = None,
        event_bus: Optional[CompilerEventBus] = None,
    ) -> None:
        self._backend_registry = backend_registry or build_default_backend_registry()
        self._pass_registry = pass_registry or build_default_pipeline()
        self._cache = cache or CompilationCache()
        self._event_bus = event_bus or CompilerEventBus()
        self._metrics = CompilerMetrics()

    def compile(self, isr: ISR, config: Optional[CompilationConfig] = None) -> CompilationResult:
        if config is None:
            config = CompilationConfig(project_name=isr.system.name)

        start_time = time.perf_counter()
        self._event_bus.publish(CompilerEvent(
            event_type=CompilerEventType.COMPILATION_STARTED,
            data={"isr_hash": isr.content_hash, "targets": list(config.target_backends)},
        ))

        cache_key = self._cache.compute_key(isr.content_hash, config.config_hash, config.compiler_version)
        cached = self._cache.get(cache_key)
        if cached is not None:
            self._metrics.record_cache(hit=True)
            self._event_bus.publish(CompilerEvent(event_type=CompilerEventType.CACHE_HIT))
            return cached

        self._metrics.record_cache(hit=False)

        ctx = CompilerContext(_isr=isr, _config=config, backend_registry=self._backend_registry)
        pass_manager = PassManager(self._pass_registry)
        passes_success = pass_manager.execute_all(ctx)

        capability_report = CapabilityReport(
            resolved={k: str(v) for k, v in ctx.capability_contracts.items()},
            unresolved=(), hints_applied=dict(config.capability_hints),
        )

        verification = VerificationResult(
            passed=not ctx.diagnostics.has_errors,
            checks_run=ctx.pass_metrics.get("verification", {}).get("verification_checks", 0),
            checks_passed=ctx.pass_metrics.get("verification", {}).get("verification_passed", 0),
            checks_failed=ctx.pass_metrics.get("verification", {}).get("verification_failed", 0),
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        result = CompilationResult(
            isr_hash=isr.content_hash, config_hash=config.config_hash,
            compiler_version=config.compiler_version,
            artifacts=tuple(ctx.artifacts), artifact_count=len(ctx.artifacts),
            diagnostics=tuple(ctx.diagnostics.diagnostics),
            error_count=len(ctx.diagnostics.errors), warning_count=len(ctx.diagnostics.warnings),
            compilation_time_ms=elapsed_ms, pass_timings=dict(ctx.pass_timings),
            targets_compiled=tuple(config.target_backends),
            capability_report=capability_report, verification=verification,
            source_map_entries=len(ctx.source_map_entries),
            success=passes_success and not ctx.diagnostics.has_errors,
        )

        if result.success:
            self._cache.put(cache_key, result)

        self._metrics.record_compilation(elapsed_ms, len(ctx.artifacts), len(ctx.diagnostics.errors), len(ctx.diagnostics.warnings))
        self._event_bus.publish(CompilerEvent(
            event_type=CompilerEventType.COMPILATION_COMPLETED,
            data={"success": result.success, "artifacts": result.artifact_count},
        ))

        return result

    def register_backend(self, backend) -> None:
        self._backend_registry.register(backend)

    def register_pass(self, pass_instance) -> None:
        self._pass_registry.register(pass_instance)

    def subscribe(self, event_type: CompilerEventType, handler) -> None:
        self._event_bus.subscribe(event_type, handler)

    @property
    def metrics(self) -> CompilerMetrics:
        return self._metrics

    @property
    def registered_backends(self) -> list[str]:
        return self._backend_registry.all_names
