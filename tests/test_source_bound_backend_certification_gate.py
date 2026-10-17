from constitutional_architecture.compiler.backends.backend_interface import (
    BackendResult,
    CompilerBackend,
)
from constitutional_architecture.compiler.backends.backend_registry import BackendRegistry
from constitutional_architecture.compiler.bir.model import BIR
from constitutional_architecture.compiler.compilation_config import CompilationConfig
from constitutional_architecture.compiler.compiler_context import CompilerContext
from constitutional_architecture.compiler.passes.code_generation_pass import CodeGenerationPass
from constitutional_architecture.compiler.quality.diagnostics import DiagnosticSeverity
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.system import System
from constitutional_architecture.isr.semantics.requirement import RequirementGraphReference


class _Backend(CompilerBackend):
    def __init__(self, *, certified=False):
        self.calls = 0
        self.source_bound_codegen_certified = certified

    @property
    def name(self):
        return "test-backend"

    def validate(self, bir):
        return []

    def bind_capabilities(self, capability_contracts):
        return []

    def compile(self, bir, bindings):
        self.calls += 1
        return BackendResult(artifacts=[object()])

    def report_unsupported(self, bir):
        return []


def _context(
    backend,
    *,
    require_source_binding=True,
    source_graph=False,
    source_binding=False,
):
    registry = BackendRegistry()
    registry.register(backend)
    system = System(id="strict-source-bound", name="Strict source-bound")
    if source_graph:
        system = System(
            id=system.id,
            name=system.name,
            requirement_graph_ref=RequirementGraphReference(
                graph_id="source-graph",
                graph_sha256="a" * 64,
                source_sha256="b" * 64,
            ),
        )
    return CompilerContext(
        _isr=ISR(system=system),
        _config=CompilationConfig(
            project_name="strict-source-bound",
            target_backends=("test-backend",),
            require_source_binding=require_source_binding,
        ),
        backend_registry=registry,
        bir=BIR(project_name="strict-source-bound"),
        source_binding=object() if source_binding else None,
    )


def test_uncertified_backend_is_blocked_before_compile_and_emits_no_artifacts():
    backend = _Backend(certified=False)
    context = _context(backend)

    result = CodeGenerationPass().execute(context)

    assert not result.success
    assert backend.calls == 0
    assert context.artifacts == []
    diagnostic = next(
        item for item in context.diagnostics.diagnostics
        if item.code == "COMP-CODE-009"
    )
    assert diagnostic.severity is DiagnosticSeverity.FATAL
    assert result.metrics["uncertified_backends"] == ["test-backend"]
    assert result.metrics["artifacts_generated"] == 0


def test_explicitly_certified_backend_can_enter_codegen():
    backend = _Backend(certified=True)
    context = _context(backend)

    result = CodeGenerationPass().execute(context)

    assert result.success
    assert backend.calls == 1
    assert len(context.artifacts) == 1


def test_legacy_non_source_bound_compile_keeps_compatibility_behavior():
    backend = _Backend(certified=False)
    context = _context(backend, require_source_binding=False)

    result = CodeGenerationPass().execute(context)

    assert result.success
    assert backend.calls == 1
    assert len(context.artifacts) == 1


def test_source_graph_cannot_bypass_backend_certification_with_legacy_config():
    backend = _Backend(certified=False)
    context = _context(
        backend,
        require_source_binding=False,
        source_graph=True,
    )

    result = CodeGenerationPass().execute(context)

    assert not result.success
    assert backend.calls == 0
    assert context.artifacts == []
    assert result.metrics["artifacts_generated"] == 0


def test_explicit_binding_cannot_bypass_backend_certification_with_legacy_config():
    backend = _Backend(certified=False)
    context = _context(
        backend,
        require_source_binding=False,
        source_binding=True,
    )

    result = CodeGenerationPass().execute(context)

    assert not result.success
    assert backend.calls == 0
    assert context.artifacts == []
    assert result.metrics["artifacts_generated"] == 0
