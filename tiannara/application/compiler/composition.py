"""Cap-C Phase 16: CLI composition root.

Wires the *real* typed IntentCompiler (Cap-A) together with the Cap-C
registration / selection / execution seams into a single entry point.

Provider injection is explicit and environment-safe:

* ``recorded`` -- hermetic. A transcript (JSONL provenance store of
  ModelCallRecord objects) is handed to ``RecordedModelProvider``; every
  structured completion is served from that store. No network, no vendor.
  This is the mode used by the unit / certification test suite.
* ``live`` -- a real LanguageModelProvider adapter lives behind the port and
  is only activated when explicitly configured; in this environment it is
  rejected so we never accidentally reach out or fabricate output.

The composition root is deliberately dependency-light so it can be embedded
both by the CLI (`tiannara create ...`) and by tests without import side
effects beyond the tiannara package graph.
"""
from __future__ import annotations

from pathlib import Path

from tiannara.application.compiler.executor import CompilationExecutor
from tiannara.application.compiler.fastapi_hexagonal_backend import FastAPIHexagonalBackend
from tiannara.application.compiler.go_hexagonal_backend import GoHexagonalBackend
from tiannara.application.compiler.rust_axum_backend import RustAxumBackend
from tiannara.application.compiler.nestjs_backend import NestJSBackend
from tiannara.application.compiler.spring_boot_backend import SpringBootBackend
from tiannara.application.compiler.aspnet_core_backend import AspNetCoreBackend
from tiannara.application.compiler.phoenix_backend import PhoenixBackend
from tiannara.application.compiler.ktor_backend import KtorBackend
from tiannara.application.compiler.react_frontend import ReactFrontend
from tiannara.application.compiler.express_backend import ExpressBackend
from tiannara.application.compiler.laravel_backend import LaravelBackend
from tiannara.application.compiler.vue_frontend import VueFrontend
from tiannara.application.compiler.rails_backend import RailsBackend
from tiannara.application.compiler.project_compiler import ProjectCompiler
from tiannara.application.compiler.registry import CompilerRegistry
from tiannara.application.compiler.selector import DEFAULT_SELECTION_POLICY, SelectionPolicy
from tiannara.application.compiler.verification import BundleVerifier
from tiannara.application.intent.compiler import IntentCompiler
from tiannara.application.intent.config import IntentCompilerConfig
from tiannara.domain.models.backend_declaration import (
    ArtifactKind,
    BackendCapabilityDeclaration,
)
from tiannara.domain.models.capability_manifest import BundleCapability
from tiannara.infrastructure.llm.recorded_provider import RecordedModelProvider
from tiannara.infrastructure.llm.transcript import ModelCallTranscript


class CompositionError(ValueError):
    """Raised when the composition root is mis-configured for this environment."""


def fastapi_declaration() -> BackendCapabilityDeclaration:
    """Default capability declaration for the FastAPI Hexagonal backend."""
    return BackendCapabilityDeclaration(
        backend_id="fastapi_hexagonal",
        artifact_kinds=[ArtifactKind.BACKEND_SERVICE],
        capabilities=list(BundleCapability),
        quality_profile=0.85,
        metadata={"language": "python", "framework": "fastapi", "style": "hexagonal"},
    )


def go_declaration() -> BackendCapabilityDeclaration:
    """Capability declaration for the hermetic Go stdlib backend."""
    return GoHexagonalBackend().build_profile_declaration()


def build_compiler_registry() -> CompilerRegistry:
    """Registry with the independently implemented production backends."""
    registry = CompilerRegistry()
    registry.register(FastAPIHexagonalBackend(), fastapi_declaration())
    go_backend = GoHexagonalBackend()
    registry.register(go_backend, go_declaration())
    rust_backend = RustAxumBackend()
    registry.register(rust_backend, rust_backend.build_profile_declaration())
    nest_backend = NestJSBackend()
    registry.register(nest_backend, nest_backend.build_profile_declaration())
    spring_backend = SpringBootBackend()
    registry.register(spring_backend, spring_backend.build_profile_declaration())
    dotnet_backend = AspNetCoreBackend()
    registry.register(dotnet_backend, dotnet_backend.build_profile_declaration())
    phoenix_backend = PhoenixBackend()
    registry.register(phoenix_backend, phoenix_backend.build_profile_declaration())
    ktor_backend = KtorBackend()
    registry.register(ktor_backend, ktor_backend.build_profile_declaration())
    react_frontend = ReactFrontend()
    registry.register(react_frontend, react_frontend.build_profile_declaration())
    express_backend = ExpressBackend()
    registry.register(express_backend, express_backend.build_profile_declaration())
    laravel_backend = LaravelBackend()
    registry.register(laravel_backend, laravel_backend.build_profile_declaration())
    vue_frontend = VueFrontend()
    registry.register(vue_frontend, vue_frontend.build_profile_declaration())
    rails_backend = RailsBackend()
    registry.register(rails_backend, rails_backend.build_profile_declaration())
    return registry


def build_intent_compiler(
    provider,
    config: IntentCompilerConfig | None = None,
) -> IntentCompiler:
    """Construct the real typed IntentCompiler backed by ``provider``."""
    return IntentCompiler(provider, config=config or IntentCompilerConfig())


def build_project_compiler(
    provider_mode: str = "recorded",
    transcript_path: str | Path | None = None,
    provider=None,
    config: IntentCompilerConfig | None = None,
    registry: CompilerRegistry | None = None,
    policy: SelectionPolicy | None = None,
    executor: CompilationExecutor | None = None,
    plan_all: bool = False,
) -> ProjectCompiler:
    """Compose a ready-to-run ProjectCompiler.

    Parameters
    ----------
    provider_mode:
        ``"recorded"`` (hermetic, default) or ``"live"`` (gated off here).
    transcript_path:
        Required for ``recorded`` mode when ``provider`` is not supplied
        directly. Points at a committed JSONL transcript.
    provider:
        Optional pre-built LanguageModelProvider. When supplied it short
        circuits ``provider_mode``/``transcript_path`` and is injected as-is;
        handy for tests that construct a provider explicitly.
    config:
        IntentCompilerConfig forwarded to the IntentCompiler front-end.
    registry:
        Optional pre-built CompilerRegistry. When omitted, the default registry
        (FastAPIHexagonalBackend only) is used -- the production single-best path.
        Supply a multi-backend registry together with ``plan_all=True`` to compile
        an intent to *every* registered backend (Phase-31 calibration seam).
    policy / executor:
        Forwarded to ProjectCompiler; defaults are used when omitted.
    plan_all:
        When True, plan every satisfying backend per requirement (select-all)
        instead of the single best. Defaults to False (existing semantics).
    """
    if provider is not None:
        intent_provider = provider
    elif provider_mode == "recorded":
        if transcript_path is None:
            raise CompositionError(
                "--transcript is required for recorded (hermetic) mode"
            )
        intent_provider = RecordedModelProvider(
            ModelCallTranscript(Path(transcript_path))
        )
    elif provider_mode == "live":
        raise CompositionError(
            "live LLM providers are not configured in this environment; "
            "supply a LanguageModelProvider adapter behind the port"
        )
    else:
        raise CompositionError(f"unknown provider mode: {provider_mode!r}")

    intent_compiler = build_intent_compiler(intent_provider, config=config)
    chosen_registry = registry if registry is not None else build_compiler_registry()
    return ProjectCompiler(
        intent_compiler,
        chosen_registry,
        policy=policy or DEFAULT_SELECTION_POLICY,
        executor=executor or CompilationExecutor(chosen_registry),
        plan_all=plan_all,
    )


def build_verifier(system_name: str, required_files: list[str]) -> BundleVerifier:
    """Construct the default bundle verifier for a compiled system name."""
    return BundleVerifier(package=system_name, required_files=required_files)
