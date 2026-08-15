import pytest

from constitutional_architecture.core.contracts.compiler import CompilerBackend
from constitutional_architecture.core.models.bundle import (
    ArtifactType, CompilationBundle, CompilationManifest,
)
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.intent import (
    BusinessArchetype, Capability, IntentModel, Persona,
)
from constitutional_architecture.core.models.isr import UniversalISR
from constitutional_architecture.core.orchestrator.composite_orchestrator import (
    CompositeOrchestrator, OrchestrationError,
)
from constitutional_architecture.core.registry.compiler_registry import (
    CompilerMetadata, CompilerRegistry,
)


class MockFrontendCompiler(CompilerBackend):
    def compile(self, isr, genome, context):
        return CompilationBundle(
            compiler_id="mock_frontend",
            target_technology="mock_fe",
            manifests=[CompilationManifest(
                artifact_type=ArtifactType.SOURCE_CODE,
                domain="frontend",
                files={"index.html": "<html></html>"},
            )],
            exposed_interfaces={"fe_port": 8080},
        )


class MockInfraCompiler(CompilerBackend):
    def compile(self, isr, genome, context):
        fe_port = context.get("fe_port", "UNKNOWN")
        return CompilationBundle(
            compiler_id="mock_infra",
            target_technology="mock_infra",
            manifests=[CompilationManifest(
                artifact_type=ArtifactType.INFRASTRUCTURE,
                domain="infra",
                files={"main.tf": f"resource 'server' {{ port = {fe_port} }}"},
            )],
        )


@pytest.fixture
def registry() -> CompilerRegistry:
    reg = CompilerRegistry()
    reg.register(MockFrontendCompiler, CompilerMetadata(
        compiler_id="mock_frontend",
        target_technology="mock_fe",
        supported_domains=["frontend"],
        required_genes=["app_arch"],
    ))
    reg.register(MockInfraCompiler, CompilerMetadata(
        compiler_id="mock_infra",
        target_technology="mock_infra",
        supported_domains=["infra"],
        required_genes=["deployment_topology"],
    ))
    return reg


@pytest.fixture
def sample_genome() -> ArchitectureGenome:
    return ArchitectureGenome()


@pytest.fixture
def sample_intent() -> IntentModel:
    return IntentModel(
        project_name="TestSys",
        problem_statement="Test",
        personas=[Persona(name="U", role="u", primary_goals=["g"])],
        business_archetype=BusinessArchetype.B2B_SAAS,
        core_capabilities=[Capability(name="C", description="d")],
    )


@pytest.fixture
def sample_isr() -> UniversalISR:
    return UniversalISR(intent_hash="1", genome_hash="1")


class TestCompilerRegistry:
    def test_register_and_resolve(self, registry, sample_genome, sample_isr):
        resolved = registry.resolve_compilers(sample_genome, sample_isr)
        assert "mock_frontend" in resolved
        assert "mock_infra" in resolved

    def test_get_compiler_instantiates(self, registry):
        compiler = registry.get_compiler("mock_frontend")
        assert isinstance(compiler, MockFrontendCompiler)

    def test_get_unknown_compiler_raises(self, registry):
        with pytest.raises(ValueError, match="not found"):
            registry.get_compiler("nonexistent")


class TestCompositeOrchestrator:
    def test_compile_system_returns_bundle(self, registry, sample_intent, sample_genome, sample_isr):
        orch = CompositeOrchestrator(registry)
        system = orch.compile_system(sample_intent, sample_genome, sample_isr)
        assert system.project_name == "TestSys"
        assert "mock_frontend" in system.bundles
        assert "mock_infra" in system.bundles

    def test_context_passing_between_compilers(self, registry, sample_intent, sample_genome, sample_isr):
        orch = CompositeOrchestrator(registry)
        system = orch.compile_system(sample_intent, sample_genome, sample_isr)
        infra_tf = system.bundles["mock_infra"].manifests[0].files["main.tf"]
        assert "port = 8080" in infra_tf

    def test_get_all_files_flattens(self, registry, sample_intent, sample_genome, sample_isr):
        orch = CompositeOrchestrator(registry)
        system = orch.compile_system(sample_intent, sample_genome, sample_isr)
        all_files = system.get_all_files()
        assert any("index.html" in path for path in all_files)
        assert any("main.tf" in path for path in all_files)

    def test_no_compilers_raises(self, sample_intent, sample_genome, sample_isr):
        empty_reg = CompilerRegistry()
        orch = CompositeOrchestrator(empty_reg)
        with pytest.raises(OrchestrationError, match="No compilers resolved"):
            orch.compile_system(sample_intent, sample_genome, sample_isr)
