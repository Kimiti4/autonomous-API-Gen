import copy

import pytest

from constitutional_architecture.compilers.documentation.markdown.compiler import (
    MarkdownDocumentationCompiler,
)
from constitutional_architecture.core.models.genome import (
    ApplicationArchitecture, ArchitectureGenome, PersistenceModel,
)
from constitutional_architecture.core.models.intent import (
    BusinessArchetype, Capability, IntentModel, Persona, QualityAttribute,
)
from constitutional_architecture.core.models.isr import (
    EdgeType, ISREdge, ISRNode, NodeType, UniversalISR,
)


@pytest.fixture
def intent() -> IntentModel:
    return IntentModel(
        project_name="Nexus",
        problem_statement="High-scale data processing",
        personas=[Persona(name="Sys", role="admin", primary_goals=["process"])],
        business_archetype=BusinessArchetype.DATA_PLATFORM,
        core_capabilities=[Capability(name="Ingest", description="d")],
        quality_priorities={
            QualityAttribute.SCALABILITY: 0.95,
            QualityAttribute.MAINTAINABILITY: 0.4,
        },
    )


@pytest.fixture
def genome() -> ArchitectureGenome:
    g = ArchitectureGenome(genome_id="g1", intent_hash="1")
    g.set_gene("app_arch", ApplicationArchitecture.MICROSERVICES)
    g.set_gene("persistence_model", PersistenceModel.POLYGLOT)
    return g


@pytest.fixture
def isr() -> UniversalISR:
    isr = UniversalISR(intent_hash="1", genome_hash="1")
    isr.add_node(ISRNode(id="entity_user", type=NodeType.DATA_ENTITY))
    isr.add_node(ISRNode(id="entity_order", type=NodeType.DATA_ENTITY))
    isr.add_edge(ISREdge(source_id="entity_user", target_id="entity_order", type=EdgeType.RELATES_TO))
    return isr


class TestMarkdownDocumentationCompiler:
    def test_compiler_purity(self, intent, genome, isr):
        compiler = MarkdownDocumentationCompiler()
        snapshot = copy.deepcopy(isr)
        compiler.compile(isr, genome, {}, intent)
        assert isr == snapshot

    def test_readme_generation(self, intent, genome, isr):
        compiler = MarkdownDocumentationCompiler()
        bundle = compiler.compile(isr, genome, {}, intent)

        readme = bundle.manifests[0].files["README.md"]
        assert "# Nexus" in readme
        assert "`microservices`" in readme

    def test_readme_contains_quality_profile(self, intent, genome, isr):
        compiler = MarkdownDocumentationCompiler()
        bundle = compiler.compile(isr, genome, {}, intent)

        readme = bundle.manifests[0].files["README.md"]
        assert "Persistence:" in readme
        assert "`polyglot`" in readme

    def test_readme_falls_back_without_intent(self, genome, isr):
        compiler = MarkdownDocumentationCompiler()
        bundle = compiler.compile(isr, genome, {"project_name": "Fallback"}, None)

        readme = bundle.manifests[0].files["README.md"]
        assert "# Fallback" in readme

    def test_erd_mermaid_generation(self, isr, intent, genome):
        compiler = MarkdownDocumentationCompiler()
        bundle = compiler.compile(isr, genome, {}, intent)

        erd = bundle.manifests[0].files["docs/domain/erd.md"]
        assert "```mermaid" in erd
        assert "erDiagram" in erd
        assert "User ||--o{ Order" in erd

    def test_adr_captures_evolutionary_tradeoffs(self, intent, genome, isr):
        compiler = MarkdownDocumentationCompiler()
        bundle = compiler.compile(isr, genome, {}, intent)

        adr = bundle.manifests[0].files["docs/architecture/adr/001-architecture-style.md"]

        assert "# ADR 001: Architecture Style Selection" in adr
        assert "Status: Accepted (Evolved by Pareto Optimization)" in adr
        assert "scalability priority of 0.95" in adr
        assert "Adopt `microservices` architecture" in adr
        assert "modular_monolith" in adr
        assert "event_driven" in adr
        assert "Increases deployment complexity" in adr
        assert "independent scaling" in adr

    def test_adr_persistence_model(self, intent, genome, isr):
        compiler = MarkdownDocumentationCompiler()
        bundle = compiler.compile(isr, genome, {}, intent)

        adr = bundle.manifests[0].files["docs/architecture/adr/002-persistence-model.md"]
        assert "# ADR 002: Persistence Model Selection" in adr
        assert "Adopt `polyglot` persistence model" in adr
        assert "relational" in adr

    def test_runbook_generation(self, intent, genome, isr):
        compiler = MarkdownDocumentationCompiler()
        bundle = compiler.compile(isr, genome, {"deployment_cmd": "terraform apply -auto-approve"}, intent)

        runbook = bundle.manifests[0].files["docs/deployment/runbook.md"]
        assert "terraform apply -auto-approve" in runbook
        assert "alembic upgrade head" in runbook

    def test_deterministic_output(self, intent, genome, isr):
        compiler = MarkdownDocumentationCompiler()
        bundle1 = compiler.compile(isr, genome, {}, intent)
        bundle2 = compiler.compile(isr, genome, {}, intent)
        assert bundle1.manifests[0].files == bundle2.manifests[0].files

    def test_returns_compilation_bundle(self, intent, genome, isr):
        compiler = MarkdownDocumentationCompiler()
        bundle = compiler.compile(isr, genome, {}, intent)
        assert bundle.compiler_id == "markdown_adr"
        assert bundle.target_technology == "markdown"
        assert bundle.manifests[0].artifact_type.value == "documentation"

    def test_registry_integration(self, intent, genome, isr):
        from constitutional_architecture.core.registry.compiler_registry import (
            CompilerMetadata, CompilerRegistry,
        )
        registry = CompilerRegistry()
        registry.register(MarkdownDocumentationCompiler, CompilerMetadata(
            compiler_id="markdown_adr",
            target_technology="markdown",
            supported_domains=["documentation"],
            required_genes=["app_arch"],
        ))
        resolved = registry.resolve_compilers(genome, isr)
        assert "markdown_adr" in resolved
        compiler = registry.get_compiler("markdown_adr")
        bundle = compiler.compile(isr, genome, {}, intent)
        assert bundle.compiler_id == "markdown_adr"

    def test_orchestrator_injects_intent(self, intent, genome, isr):
        from constitutional_architecture.core.orchestrator.composite_orchestrator import (
            CompositeOrchestrator,
        )
        from constitutional_architecture.core.registry.compiler_registry import (
            CompilerMetadata, CompilerRegistry,
        )
        registry = CompilerRegistry()
        registry.register(MarkdownDocumentationCompiler, CompilerMetadata(
            compiler_id="markdown_adr",
            target_technology="markdown",
            supported_domains=["documentation"],
            required_genes=["app_arch"],
        ))
        orchestrator = CompositeOrchestrator(registry)
        system = orchestrator.compile_system(intent, genome, isr)

        readme = system.bundles["markdown_adr"].manifests[0].files["README.md"]
        assert "# Nexus" in readme
