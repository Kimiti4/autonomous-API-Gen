import datetime

import pytest

from constitutional_architecture.compilers.backend.fastapi.compiler import FastAPICompiler
from constitutional_architecture.compilers.deployment.base import DeploymentMetaCompiler
from constitutional_architecture.compilers.deployment.cicd.compiler import CICDDeploymentCompiler
from constitutional_architecture.compilers.infrastructure.terraform.compiler import TerraformCompiler
from constitutional_architecture.core.build.dag import (
    BuildGraphResolver, CompilerNode, build_platform_graph,
)
from constitutional_architecture.core.build.provenance import (
    ArtifactProvenance, EvolutionaryBuildCache, bundle_hash, genome_signature,
    intent_signature, isr_signature,
)
from constitutional_architecture.core.models.bundle import (
    ArtifactType, CompilationBundle, CompilationManifest,
)
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.intent import (
    BusinessArchetype, Capability, IntentModel, Persona,
)
from constitutional_architecture.core.models.isr import (
    ISRNode, NodeType, UniversalISR,
)
from constitutional_architecture.core.orchestrator.provenance_orchestrator import (
    ProvenanceOrchestrator,
)


class MockFrontendCompiler:
    VERSION = "2.0.0"
    calls = 0

    def compile(self, isr, genome, context):
        MockFrontendCompiler.calls += 1
        return CompilationBundle(
            compiler_id="mock_frontend",
            target_technology="mock_fe",
            manifests=[CompilationManifest(
                artifact_type=ArtifactType.SOURCE_CODE,
                domain="frontend",
                files={"index.html": f"<html>{genome.get_gene('api_design')}</html>"},
            )],
        )


class MockDatabaseCompiler:
    VERSION = "1.0.0"
    calls = 0

    def compile(self, isr, genome, context):
        MockDatabaseCompiler.calls += 1
        return CompilationBundle(
            compiler_id="mock_database",
            target_technology="mock_db",
            manifests=[CompilationManifest(
                artifact_type=ArtifactType.DATABASE_MIGRATION,
                domain="db",
                files={"schema.sql": "CREATE TABLE t;"},
            )],
        )


class MockDeployCompiler(DeploymentMetaCompiler):
    VERSION = "1.0.0"
    calls = 0

    def compile_system(self, bundle, context):
        MockDeployCompiler.calls += 1
        return CompilationBundle(
            compiler_id="mock_deploy",
            target_technology="mock_cicd",
            manifests=[CompilationManifest(
                artifact_type=ArtifactType.CI_CD_PIPELINE,
                domain="cicd",
                files={"deploy.yml": f"services: {sorted(bundle.bundles.keys())}"},
            )],
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
    return ArchitectureGenome(genome_id="gen42", intent_hash="abc123")


@pytest.fixture
def isr() -> UniversalISR:
    isr = UniversalISR(intent_hash="abc123", genome_hash="def456")
    isr.add_node(ISRNode(id="entity_order", type=NodeType.DATA_ENTITY))
    isr.add_node(ISRNode(
        id="api_orders",
        type=NodeType.API_ENDPOINT,
        semantic_attributes={"path": "/v1/orders"},
    ))
    return isr


def scoped_graph():
    resolver = BuildGraphResolver()
    resolver.register(CompilerNode(
        "mock_frontend", MockFrontendCompiler, [ArtifactType.SOURCE_CODE], [],
        consumed_genes=["api_design"],
    ))
    resolver.register(CompilerNode(
        "mock_database", MockDatabaseCompiler, [ArtifactType.DATABASE_MIGRATION], [],
        consumed_genes=["persistence_model"],
        consumed_node_types=[NodeType.DATA_ENTITY],
    ))
    resolver.register(CompilerNode(
        "mock_deploy", MockDeployCompiler, [ArtifactType.CI_CD_PIPELINE],
        [ArtifactType.SOURCE_CODE, ArtifactType.DATABASE_MIGRATION],
        consumed_genes=[],
        consumed_node_types=[],
    ))
    return resolver


def reset_calls():
    for cls in (MockFrontendCompiler, MockDatabaseCompiler, MockDeployCompiler):
        cls.calls = 0


class TestBuildGraphResolver:
    def test_plan_is_topologically_sorted(self, intent, genome, isr):
        resolver = scoped_graph()
        plan = resolver.resolve_execution_plan({ArtifactType.CI_CD_PIPELINE})
        assert plan.index("mock_frontend") < plan.index("mock_deploy")
        assert plan.index("mock_database") < plan.index("mock_deploy")
        assert plan[-1] == "mock_deploy"

    def test_backward_walk_finds_all_dependencies(self):
        resolver = scoped_graph()
        plan = resolver.resolve_execution_plan({ArtifactType.CI_CD_PIPELINE})
        assert set(plan) == {"mock_frontend", "mock_database", "mock_deploy"}

    def test_unknown_target_artifact_raises(self):
        resolver = scoped_graph()
        with pytest.raises(ValueError, match="No eligible compiler"):
            resolver.resolve_execution_plan({ArtifactType.SDK_CLIENT})

    def test_cycle_detection(self):
        resolver = BuildGraphResolver()
        resolver.register(CompilerNode("a", MockFrontendCompiler, [ArtifactType.SOURCE_CODE],
                                       [ArtifactType.CONFIGURATION]))
        resolver.register(CompilerNode("b", MockDatabaseCompiler, [ArtifactType.CONFIGURATION],
                                       [ArtifactType.SOURCE_CODE]))
        with pytest.raises(RuntimeError, match="Cyclic"):
            resolver.resolve_execution_plan({ArtifactType.SOURCE_CODE})

    def test_multiple_providers_of_same_artifact(self):
        resolver = BuildGraphResolver()
        resolver.register(CompilerNode("fe", MockFrontendCompiler, [ArtifactType.SOURCE_CODE], []))
        resolver.register(CompilerNode("db", MockDatabaseCompiler, [ArtifactType.DATABASE_MIGRATION], []))
        plan = resolver.resolve_execution_plan({ArtifactType.SOURCE_CODE, ArtifactType.DATABASE_MIGRATION})
        assert set(plan) == {"fe", "db"}

    def test_eligibility_filter(self):
        resolver = BuildGraphResolver()
        resolver.register(CompilerNode("fe", MockFrontendCompiler, [ArtifactType.SOURCE_CODE], []))
        resolver.register(CompilerNode("fe_alt", MockFrontendCompiler, [ArtifactType.SOURCE_CODE], []))
        resolver.register(CompilerNode("db", MockDatabaseCompiler, [ArtifactType.DATABASE_MIGRATION], []))
        resolver.register(CompilerNode("deploy", MockDeployCompiler, [ArtifactType.CI_CD_PIPELINE],
                                       [ArtifactType.SOURCE_CODE, ArtifactType.DATABASE_MIGRATION]))
        plan = resolver.resolve_execution_plan(
            {ArtifactType.CI_CD_PIPELINE},
            eligible_ids={"fe_alt", "db", "deploy"},
        )
        assert "fe" not in plan
        assert "fe_alt" in plan
        assert plan[-1] == "deploy"

    def test_ineligible_provider_of_required_artifact_raises(self):
        resolver = scoped_graph()
        with pytest.raises(ValueError, match="No eligible compiler"):
            resolver.resolve_execution_plan(
                {ArtifactType.CI_CD_PIPELINE},
                eligible_ids={"mock_frontend", "mock_deploy"},
            )

    def test_platform_graph_resolves_full_pipeline(self):
        resolver = build_platform_graph()
        plan = resolver.resolve_execution_plan({ArtifactType.CI_CD_PIPELINE})
        assert len(plan) == 9
        assert "github_actions_compose" == plan[-1]
        assert "fastapi_hexagonal" in plan
        assert "terraform_aws" in plan
        assert "pytest_layered" in plan


class TestEvolutionaryBuildCache:
    def test_key_is_deterministic(self):
        cache = EvolutionaryBuildCache()
        k1 = cache.compute_cache_key("c", "1.0.0", "i", "g", ["a", "b"])
        k2 = cache.compute_cache_key("c", "1.0.0", "i", "g", ["a", "b"])
        assert k1 == k2

    def test_key_sensitive_to_all_inputs(self):
        cache = EvolutionaryBuildCache()
        base = cache.compute_cache_key("c", "1.0.0", "i", "g", ["a"])
        assert base != cache.compute_cache_key("c2", "1.0.0", "i", "g", ["a"])
        assert base != cache.compute_cache_key("c", "1.0.1", "i", "g", ["a"])
        assert base != cache.compute_cache_key("c", "1.0.0", "i2", "g", ["a"])
        assert base != cache.compute_cache_key("c", "1.0.0", "i", "g2", ["a"])
        assert base != cache.compute_cache_key("c", "1.0.0", "i", "g", ["b"])

    def test_input_hashes_sorted_for_stability(self):
        cache = EvolutionaryBuildCache()
        assert cache.compute_cache_key("c", "1", "i", "g", ["b", "a"]) == \
            cache.compute_cache_key("c", "1", "i", "g", ["a", "b"])

    def test_put_get_roundtrip(self):
        cache = EvolutionaryBuildCache()
        bundle = CompilationBundle(compiler_id="x", target_technology="t")
        prov = ArtifactProvenance(
            artifact_hash="h", compiler_id="x", compiler_version="1",
            genome_id="g", genome_hash="gh", isr_hash="ih", intent_hash="it",
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        key = cache.compute_cache_key("x", "1", "ih", "gh", [])
        cache.put(key, bundle, prov)
        assert cache.get(key) is bundle
        assert cache.provenance_of(key) == prov

    def test_scoped_signatures_change_only_within_scope(self, genome, isr):
        s_full = isr_signature(isr, None)
        s_scoped = isr_signature(isr, [NodeType.DATA_ENTITY])
        assert s_full != s_scoped

        isr.add_node(ISRNode(id="api_new", type=NodeType.API_ENDPOINT))
        assert isr_signature(isr, [NodeType.DATA_ENTITY]) == s_scoped

        genome.set_gene("api_design", "grpc")
        assert genome_signature(genome, ["persistence_model"]) == \
            genome_signature(genome, ["persistence_model"])


class TestProvenanceOrchestrator:
    def test_incremental_compile_second_run_is_cache_hit(self, intent, genome, isr):
        reset_calls()
        orchestrator = ProvenanceOrchestrator(scoped_graph(), EvolutionaryBuildCache())
        system1 = orchestrator.compile_system(intent, genome, isr, {ArtifactType.CI_CD_PIPELINE})
        assert MockFrontendCompiler.calls == 1
        assert MockDatabaseCompiler.calls == 1
        assert MockDeployCompiler.calls == 1
        assert "mock_deploy" in system1.bundles

        system2 = orchestrator.compile_system(intent, genome, isr, {ArtifactType.CI_CD_PIPELINE})
        assert MockFrontendCompiler.calls == 1
        assert MockDatabaseCompiler.calls == 1
        assert MockDeployCompiler.calls == 1
        assert system2.get_all_files() == system1.get_all_files()

    def test_frontend_gene_change_does_not_recompile_database(self, intent, genome, isr):
        reset_calls()
        orchestrator = ProvenanceOrchestrator(scoped_graph(), EvolutionaryBuildCache())
        orchestrator.compile_system(intent, genome, isr, {ArtifactType.CI_CD_PIPELINE})

        genome.set_gene("api_design", "graphql")
        system = orchestrator.compile_system(intent, genome, isr, {ArtifactType.CI_CD_PIPELINE})
        assert MockFrontendCompiler.calls == 2  # recompiled
        assert MockDatabaseCompiler.calls == 1  # CACHE HIT — unaffected gene
        assert "graphql" in system.get_all_files()["mock_fe/frontend/index.html"]

    def test_database_gene_change_recompiles_only_database(self, intent, genome, isr):
        reset_calls()
        orchestrator = ProvenanceOrchestrator(scoped_graph(), EvolutionaryBuildCache())
        orchestrator.compile_system(intent, genome, isr, {ArtifactType.CI_CD_PIPELINE})

        genome.set_gene("persistence_model", "document")
        orchestrator.compile_system(intent, genome, isr, {ArtifactType.CI_CD_PIPELINE})
        assert MockDatabaseCompiler.calls == 2
        assert MockFrontendCompiler.calls == 1

    def test_isr_node_change_scoped_to_database(self, intent, genome, isr):
        reset_calls()
        orchestrator = ProvenanceOrchestrator(scoped_graph(), EvolutionaryBuildCache())
        orchestrator.compile_system(intent, genome, isr, {ArtifactType.CI_CD_PIPELINE})

        isr.add_node(ISRNode(id="api_new", type=NodeType.API_ENDPOINT))
        orchestrator.compile_system(intent, genome, isr, {ArtifactType.CI_CD_PIPELINE})
        assert MockDatabaseCompiler.calls == 1  # API node not consumed by DB scope
        assert MockFrontendCompiler.calls == 2

    def test_meta_compiler_depends_only_on_bundles(self, intent, genome, isr):
        reset_calls()
        orchestrator = ProvenanceOrchestrator(scoped_graph(), EvolutionaryBuildCache())
        orchestrator.compile_system(intent, genome, isr, {ArtifactType.CI_CD_PIPELINE})

        genome.set_gene("api_design", "grpc")
        orchestrator.compile_system(intent, genome, isr, {ArtifactType.CI_CD_PIPELINE})
        # Frontend recompiled -> its bundle changed -> deploy MUST recompile
        assert MockDeployCompiler.calls == 2

    def test_unchanged_bundles_keep_deploy_cached(self, intent, genome, isr):
        reset_calls()
        orchestrator = ProvenanceOrchestrator(scoped_graph(), EvolutionaryBuildCache())
        orchestrator.compile_system(intent, genome, isr, {ArtifactType.CI_CD_PIPELINE})

        isr.add_node(ISRNode(id="api_extra", type=NodeType.API_ENDPOINT))
        orchestrator.compile_system(intent, genome, isr, {ArtifactType.CI_CD_PIPELINE})
        # Frontend scope excludes API_ENDPOINT -> frontend cached -> bundle
        # unchanged -> deploy's bundle-only inputs unchanged -> deploy cached
        assert MockDeployCompiler.calls == 1

    def test_provenance_stamped_on_all_bundles(self, intent, genome, isr):
        orchestrator = ProvenanceOrchestrator(scoped_graph(), EvolutionaryBuildCache())
        system = orchestrator.compile_system(intent, genome, isr, {ArtifactType.CI_CD_PIPELINE})
        prov = system.global_metadata["provenance"]
        assert set(prov.keys()) == {"mock_frontend", "mock_database", "mock_deploy"}

        db_prov = prov["mock_database"]
        assert db_prov["compiler_id"] == "mock_database"
        assert db_prov["compiler_version"] == "1.0.0"
        assert db_prov["genome_id"] == "gen42"
        assert db_prov["intent_hash"] == "abc123"
        assert db_prov["isr_hash"]
        assert db_prov["genome_hash"]
        assert db_prov["artifact_hash"] == bundle_hash(system.bundles["mock_database"])

    def test_meta_compiler_provenance_has_input_dependencies(self, intent, genome, isr):
        orchestrator = ProvenanceOrchestrator(scoped_graph(), EvolutionaryBuildCache())
        system = orchestrator.compile_system(intent, genome, isr, {ArtifactType.CI_CD_PIPELINE})
        deploy_prov = system.global_metadata["provenance"]["mock_deploy"]
        assert len(deploy_prov["input_dependencies"]) == 2

    def test_provenance_immutable_across_cache_hits(self, intent, genome, isr):
        orchestrator = ProvenanceOrchestrator(scoped_graph(), EvolutionaryBuildCache())
        system1 = orchestrator.compile_system(intent, genome, isr, {ArtifactType.CI_CD_PIPELINE})
        system2 = orchestrator.compile_system(intent, genome, isr, {ArtifactType.CI_CD_PIPELINE})
        assert system1.global_metadata["provenance"] == system2.global_metadata["provenance"]

    def test_full_platform_pipeline_with_provenance(self, intent, genome, isr):
        orchestrator = ProvenanceOrchestrator(build_platform_graph(), EvolutionaryBuildCache())
        system = orchestrator.compile_system(intent, genome, isr, {ArtifactType.CI_CD_PIPELINE})
        assert "github_actions_compose" in system.bundles
        assert "fastapi_hexagonal" in system.bundles
        assert "terraform_aws" in system.bundles
        assert "pytest_layered" in system.bundles
        prov = system.global_metadata["provenance"]
        assert len(prov) == 9
        assert prov["github_actions_compose"]["genome_id"] == "gen42"


class TestGeneticWatermarks:
    def test_fastapi_watermark_injected(self, genome, isr):
        compiler = FastAPICompiler()
        main_code = compiler.compile(isr, genome, {}).manifests[0].files["app/main.py"]
        assert "evolution.genome_id" in main_code
        assert '"gen42"' in main_code
        assert "evolution.intent_hash" in main_code
        assert "evolution.architecture_style" in main_code
        assert '"modular_monolith"' in main_code

    def test_fastapi_watermark_falls_back(self, isr):
        compiler = FastAPICompiler()
        main_code = compiler.compile(isr, ArchitectureGenome(), {}).manifests[0].files["app/main.py"]
        assert '"unknown"' in main_code

    def test_terraform_watermark_tags(self, genome, isr):
        compiler = TerraformCompiler()
        main_tf = compiler.compile(isr, genome, {}).manifests[0].files["main.tf"]
        assert 'Genome = "gen42"' in main_tf
        assert 'Intent = "abc123"' in main_tf

    def test_terraform_watermark_defaults(self, isr):
        compiler = TerraformCompiler()
        main_tf = compiler.compile(isr, ArchitectureGenome(), {}).manifests[0].files["main.tf"]
        assert 'Genome = "app"' in main_tf
        assert 'Intent = "unknown"' in main_tf
