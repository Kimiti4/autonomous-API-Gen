import pytest

from constitutional_architecture.compilers.backend.fastapi.compiler import FastAPICompiler
from constitutional_architecture.compilers.deployment.cicd.compiler import (
    CICDDeploymentCompiler,
)
from constitutional_architecture.compilers.operational.intelligence.compiler import (
    OperationalIntelligenceCompiler,
)
from constitutional_architecture.compilers.testing.pytest.compiler import PytestCompiler
from constitutional_architecture.core.models.bundle import ArtifactType
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.intent import (
    BusinessArchetype, Capability, IntentModel, Persona,
)
from constitutional_architecture.core.models.isr import UniversalISR
from constitutional_architecture.core.orchestrator.composite_orchestrator import (
    CompositeOrchestrator,
)
from constitutional_architecture.core.registry.compiler_registry import (
    CompilerMetadata, CompilerRegistry,
)


@pytest.fixture
def intent() -> IntentModel:
    return IntentModel(
        project_name="Nexus",
        problem_statement="High-scale data processing",
        personas=[Persona(name="Sys", role="admin", primary_goals=["process"])],
        business_archetype=BusinessArchetype.DATA_PLATFORM,
        core_capabilities=[Capability(name="Ingest", description="d")],
    )


@pytest.fixture
def genome() -> ArchitectureGenome:
    return ArchitectureGenome(genome_id="g1", intent_hash="1")


@pytest.fixture
def isr() -> UniversalISR:
    return UniversalISR(intent_hash="1", genome_hash="1")


def bundle_with(compiler_ids, intent, genome, isr):
    registry = CompilerRegistry()
    for comp_id in compiler_ids:
        if comp_id == "fastapi_hexagonal":
            registry.register(FastAPICompiler, CompilerMetadata(
                compiler_id=comp_id, target_technology="fastapi",
                supported_domains=["backend"], required_genes=["app_arch"],
            ))
        elif comp_id == "operational_intelligence_v1":
            registry.register(OperationalIntelligenceCompiler, CompilerMetadata(
                compiler_id=comp_id, target_technology="prometheus_grafana_otel",
                supported_domains=["operational"], required_genes=["observability_depth"],
            ))
        elif comp_id == "pytest_layered":
            registry.register(PytestCompiler, CompilerMetadata(
                compiler_id=comp_id, target_technology="pytest",
                supported_domains=["testing"], required_genes=["app_arch"],
            ))
    registry.register(CICDDeploymentCompiler, CompilerMetadata(
        compiler_id="github_actions_compose", target_technology="cicd",
        supported_domains=["deployment"], meta_compiler=True,
    ))
    orchestrator = CompositeOrchestrator(registry)
    return orchestrator.compile_system(intent, genome, isr)


def all_files(bundle):
    files = {}
    for manifest in bundle.manifests:
        files.update(manifest.files)
    return files


class TestCICDDeploymentCompiler:
    def test_compiles_pipeline_and_compose(self, intent, genome, isr):
        system = bundle_with(
            ["fastapi_hexagonal", "operational_intelligence_v1", "pytest_layered"],
            intent, genome, isr,
        )
        files = all_files(system.bundles["github_actions_compose"])
        assert ".github/workflows/deploy.yml" in files
        assert "docker-compose.yml" in files

    def test_workflow_runs_compiled_tests(self, intent, genome, isr):
        system = bundle_with(
            ["fastapi_hexagonal", "operational_intelligence_v1", "pytest_layered"],
            intent, genome, isr,
        )
        workflow = all_files(system.bundles["github_actions_compose"])[
            ".github/workflows/deploy.yml"
        ]
        assert "name: Deploy" in workflow
        assert "pytest tests/" in workflow
        assert "needs: test" in workflow

    def test_workflow_wires_terraform_and_migrations(self, intent, genome, isr):
        from constitutional_architecture.compilers.infrastructure.terraform.compiler import (
            TerraformCompiler,
        )
        from constitutional_architecture.compilers.database.postgres.compiler import (
            PostgresCompiler,
        )
        registry = CompilerRegistry()
        registry.register(FastAPICompiler, CompilerMetadata(
            compiler_id="fastapi_hexagonal", target_technology="fastapi",
            supported_domains=["backend"], required_genes=["app_arch"],
        ))
        registry.register(TerraformCompiler, CompilerMetadata(
            compiler_id="terraform_aws", target_technology="terraform",
            supported_domains=["infra"], required_genes=["deployment_topology"],
        ))
        registry.register(PostgresCompiler, CompilerMetadata(
            compiler_id="postgres_alembic", target_technology="postgres",
            supported_domains=["database"], required_genes=["persistence_model"],
        ))
        registry.register(CICDDeploymentCompiler, CompilerMetadata(
            compiler_id="github_actions_compose", target_technology="cicd",
            supported_domains=["deployment"], meta_compiler=True,
        ))
        system = CompositeOrchestrator(registry).compile_system(intent, genome, isr)
        workflow = all_files(system.bundles["github_actions_compose"])[
            ".github/workflows/deploy.yml"
        ]
        assert "terraform apply" in workflow
        assert "alembic upgrade head" in workflow
        assert "docker compose up -d" in workflow

    def test_compose_wires_backend_port_from_bundle(self, intent, genome, isr):
        system = bundle_with(["fastapi_hexagonal"], intent, genome, isr)
        compose = all_files(system.bundles["github_actions_compose"])["docker-compose.yml"]
        assert '"8000:8000"' in compose
        assert "build: ./backend" in compose

    def test_compose_wires_observability_stack(self, intent, genome, isr):
        system = bundle_with(
            ["fastapi_hexagonal", "operational_intelligence_v1"], intent, genome, isr,
        )
        compose = all_files(system.bundles["github_actions_compose"])["docker-compose.yml"]
        assert "otel-collector" in compose
        assert '"9090:9090"' in compose
        assert '"3001:3001"' in compose

    def test_meta_compiler_not_in_resolved_app_compilers(self, genome, isr):
        registry = CompilerRegistry()
        registry.register(CICDDeploymentCompiler, CompilerMetadata(
            compiler_id="github_actions_compose", target_technology="cicd",
            supported_domains=["deployment"], meta_compiler=True,
        ))
        assert registry.resolve_compilers(genome, isr) == []
        assert registry.resolve_meta_compilers() == ["github_actions_compose"]

    def test_orchestrator_runs_meta_pass_after_artifacts(self, intent, genome, isr):
        system = bundle_with(["fastapi_hexagonal"], intent, genome, isr)
        assert "github_actions_compose" in system.bundles
        compose = all_files(system.bundles["github_actions_compose"])["docker-compose.yml"]
        assert "backend" in compose

    def test_exposed_deploy_interface(self, intent, genome, isr):
        system = bundle_with(["fastapi_hexagonal"], intent, genome, isr)
        bundle = system.bundles["github_actions_compose"]
        assert bundle.exposed_interfaces["deploy_platform"] == "github_actions"
        assert bundle.manifests[0].artifact_type == ArtifactType.CI_CD_PIPELINE

    def test_deterministic_output(self, intent, genome, isr):
        system1 = bundle_with(["fastapi_hexagonal"], intent, genome, isr)
        system2 = bundle_with(["fastapi_hexagonal"], intent, genome, isr)
        assert all_files(system1.bundles["github_actions_compose"]) == all_files(
            system2.bundles["github_actions_compose"]
        )
