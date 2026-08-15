import pytest

from constitutional_architecture.compiler.backends.backend_interface import BackendResult
from constitutional_architecture.compiler.backends.backend_registry import BackendRegistry
from constitutional_architecture.compiler.backends.backend_interface import CompilerBackend
from constitutional_architecture.compiler.bir.model import BIR, BIRModule, BIRNode, BIRNodeType
from constitutional_architecture.compiler.compilation_config import CompilationConfig
from constitutional_architecture.compiler.compiler_context import CompilerContext
from constitutional_architecture.compiler.passes.code_generation_pass import CodeGenerationPass
from constitutional_architecture.compiler.quality.diagnostics import Diagnostic
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.system import System


class _TestBackend(CompilerBackend):
    @property
    def name(self) -> str:
        return "test"

    def validate(self, bir: object) -> list[Diagnostic]:
        return []

    def bind_capabilities(self, capability_contracts: dict[str, object]) -> list[object]:
        return []

    def compile(self, bir: object, bindings: list[object]) -> BackendResult:
        from constitutional_architecture.compiler.artifacts.artifact_model import Artifact, ArtifactType
        return BackendResult(artifacts=[Artifact(path="test.py", content="print('hello')", artifact_type=ArtifactType.SOURCE, backend="test")])

    def report_unsupported(self, bir: object) -> list[str]:
        return []


class _FailingBackend(CompilerBackend):
    @property
    def name(self) -> str:
        return "failing"

    def validate(self, bir: object) -> list[Diagnostic]:
        return [Diagnostic(code="ERR", message="fail")]

    def bind_capabilities(self, capability_contracts: dict[str, object]) -> list[object]:
        return []

    def compile(self, bir: object, bindings: list[object]) -> BackendResult:
        msg = "backend error"
        raise RuntimeError(msg)

    def report_unsupported(self, bir: object) -> list[str]:
        return ["feature_x"]


class TestCodeGenerationPass:
    def test_generates_artifacts_from_bir(self):
        config = CompilationConfig(project_name="shop", target_backends=("test",))
        registry = BackendRegistry()
        registry.register(_TestBackend())
        ctx = CompilerContext(_isr=ISR(system=System(id="s", name="S")), _config=config, backend_registry=registry)
        ctx.bir = BIR(project_name="shop")
        result = CodeGenerationPass().execute(ctx)
        assert result.success
        assert len(ctx.artifacts) > 0
        assert result.metrics["total_artifacts"] > 0

    def test_fails_without_bir(self):
        config = CompilationConfig(project_name="shop", target_backends=("test",))
        registry = BackendRegistry()
        registry.register(_TestBackend())
        ctx = CompilerContext(_isr=ISR(system=System(id="s", name="S")), _config=config, backend_registry=registry)
        result = CodeGenerationPass().execute(ctx)
        assert not result.success

    def test_fails_without_backend_registry(self):
        config = CompilationConfig(project_name="shop", target_backends=("test",))
        ctx = CompilerContext(_isr=ISR(system=System(id="s", name="S")), _config=config, backend_registry=None)
        ctx.bir = BIR(project_name="shop")
        result = CodeGenerationPass().execute(ctx)
        assert not result.success

    def test_reports_missing_backends(self):
        config = CompilationConfig(project_name="shop", target_backends=("nonexistent",))
        registry = BackendRegistry()
        ctx = CompilerContext(_isr=ISR(system=System(id="s", name="S")), _config=config, backend_registry=registry)
        ctx.bir = BIR(project_name="shop")
        result = CodeGenerationPass().execute(ctx)
        assert not result.success

    def test_reports_backend_errors(self):
        config = CompilationConfig(project_name="shop", target_backends=("failing",))
        registry = BackendRegistry()
        registry.register(_FailingBackend())
        ctx = CompilerContext(_isr=ISR(system=System(id="s", name="S")), _config=config, backend_registry=registry)
        ctx.bir = BIR(project_name="shop", modules=(BIRModule(id="m", name="M"),))
        result = CodeGenerationPass().execute(ctx)
        assert not result.success
