import copy

import pytest

from constitutional_architecture.compilers.infrastructure.adapters import (
    AWSAdapter, GCPAdapter,
)
from constitutional_architecture.compilers.infrastructure.terraform.compiler import (
    TerraformCompiler,
)
from constitutional_architecture.core.models.genome import (
    ArchitectureGenome, DeploymentTopology, MessagingTopology, PersistenceModel,
)
from constitutional_architecture.core.models.isr import (
    ISRNode, NodeType, UniversalISR,
)


@pytest.fixture
def context_from_orchestrator():
    """Simulates the context passed by the Composite Orchestrator after Frontend/Backend compilation."""
    return {
        "backend_port": 8080,
        "requires_message_broker": True,
        "frontend_port": 3000,
    }


@pytest.fixture
def production_genome() -> ArchitectureGenome:
    g = ArchitectureGenome(genome_id="g_prod_1", intent_hash="123")
    g.set_gene("deployment_topology", DeploymentTopology.CONTAINERIZED)
    g.set_gene("persistence_model", PersistenceModel.RELATIONAL)
    g.set_gene("messaging_topology", MessagingTopology.ASYNC_EVENT_BUS)
    g.set_gene("observability_depth", 0.9)
    return g


@pytest.fixture
def empty_isr() -> UniversalISR:
    return UniversalISR(intent_hash="1", genome_hash="1")


class TestTerraformCompiler:
    def test_compiler_purity(self, production_genome, empty_isr, context_from_orchestrator):
        compiler = TerraformCompiler()
        snapshot = copy.deepcopy(empty_isr)
        compiler.compile(empty_isr, production_genome, context_from_orchestrator)
        assert empty_isr == snapshot

    def test_context_consumption_and_least_privilege(
        self, production_genome, empty_isr, context_from_orchestrator,
    ):
        compiler = TerraformCompiler()
        bundle = compiler.compile(empty_isr, production_genome, context_from_orchestrator)

        network_tf = bundle.manifests[0].files["network.tf"]

        assert "from_port   = 8080" in network_tf
        assert "to_port     = 8080" in network_tf
        assert 'cidr_blocks = ["10.0.1.0/24"]' in network_tf

    def test_gene_to_infrastructure_mapping(
        self, production_genome, empty_isr, context_from_orchestrator,
    ):
        compiler = TerraformCompiler()
        bundle = compiler.compile(empty_isr, production_genome, context_from_orchestrator)

        data_tf = bundle.manifests[0].files["data.tf"]

        assert 'resource "aws_db_instance"' in data_tf
        assert 'engine         = "postgres"' in data_tf
        assert 'resource "aws_sqs_queue"' in data_tf

    def test_observability_by_design_enforcement(
        self, production_genome, empty_isr, context_from_orchestrator,
    ):
        compiler = TerraformCompiler()
        bundle = compiler.compile(empty_isr, production_genome, context_from_orchestrator)

        compute_tf = bundle.manifests[0].files["compute.tf"]
        obs_tf = bundle.manifests[0].files["observability.tf"]

        assert 'value = "enabled" # Observability by Design' in compute_tf
        assert "retention_in_days = 329" in obs_tf

    def test_security_by_design_secrets_management(
        self, production_genome, empty_isr, context_from_orchestrator,
    ):
        compiler = TerraformCompiler()
        bundle = compiler.compile(empty_isr, production_genome, context_from_orchestrator)

        variables_tf = bundle.manifests[0].files["variables.tf"]
        assert "sensitive = true" in variables_tf

    def test_containerized_topology_generates_ecs(
        self, production_genome, empty_isr, context_from_orchestrator,
    ):
        compiler = TerraformCompiler()
        bundle = compiler.compile(empty_isr, production_genome, context_from_orchestrator)

        compute_tf = bundle.manifests[0].files["compute.tf"]
        assert 'resource "aws_ecs_cluster"' in compute_tf
        assert 'resource "aws_ecs_task_definition"' in compute_tf
        assert "awslogs" in compute_tf
        assert "aws_cloudwatch_log_group.backend.name" in compute_tf

    def test_backend_port_wired_into_task_definition(
        self, production_genome, empty_isr, context_from_orchestrator,
    ):
        compiler = TerraformCompiler()
        bundle = compiler.compile(empty_isr, production_genome, context_from_orchestrator)

        compute_tf = bundle.manifests[0].files["compute.tf"]
        assert "containerPort = 8080" in compute_tf

    def test_non_containerized_falls_back(self, empty_isr, context_from_orchestrator):
        g = ArchitectureGenome()
        g.set_gene("deployment_topology", DeploymentTopology.SINGLE_REGION)
        compiler = TerraformCompiler()
        bundle = compiler.compile(empty_isr, g, context_from_orchestrator)
        compute_tf = bundle.manifests[0].files["compute.tf"]
        assert "Fallback compute generation" in compute_tf

    def test_main_tf_uses_genome_id_backend_key(
        self, production_genome, empty_isr, context_from_orchestrator,
    ):
        compiler = TerraformCompiler()
        bundle = compiler.compile(empty_isr, production_genome, context_from_orchestrator)

        main_tf = bundle.manifests[0].files["main.tf"]
        assert 'key    = "g_prod_1/terraform.tfstate"' in main_tf
        assert 'backend "s3"' in main_tf

    def test_no_db_without_relational_gene(self, empty_isr, context_from_orchestrator):
        g = ArchitectureGenome(genome_id="g_no_db")
        g.set_gene("deployment_topology", DeploymentTopology.CONTAINERIZED)
        g.set_gene("persistence_model", PersistenceModel.KEY_VALUE)
        compiler = TerraformCompiler()
        bundle = compiler.compile(empty_isr, g, context_from_orchestrator)

        data_tf = bundle.manifests[0].files["data.tf"]
        assert 'resource "aws_db_instance"' not in data_tf

    def test_deterministic_output(
        self, production_genome, empty_isr, context_from_orchestrator,
    ):
        compiler = TerraformCompiler()
        bundle1 = compiler.compile(empty_isr, production_genome, context_from_orchestrator)
        bundle2 = compiler.compile(empty_isr, production_genome, context_from_orchestrator)
        assert bundle1.manifests[0].files == bundle2.manifests[0].files

    def test_returns_compilation_bundle(
        self, production_genome, empty_isr, context_from_orchestrator,
    ):
        compiler = TerraformCompiler()
        bundle = compiler.compile(empty_isr, production_genome, context_from_orchestrator)
        assert bundle.compiler_id == "terraform_aws"
        assert bundle.target_technology == "terraform"
        assert bundle.exposed_interfaces["tf_state_backend"] == "s3"
        assert bundle.exposed_interfaces["deployment_cmd"] == "terraform apply -auto-approve"

    def test_gcp_adapter_delegation(self, production_genome, empty_isr, context_from_orchestrator):
        compiler = TerraformCompiler(provider_adapter=GCPAdapter())
        bundle = compiler.compile(empty_isr, production_genome, context_from_orchestrator)

        files = bundle.manifests[0].files
        assert "google_compute_network" in files["network.tf"]
        assert "google_cloud_run_service" in files["compute.tf"]
        assert bundle.exposed_interfaces["cloud_provider"] == "google"

    def test_registry_integration(self, production_genome, empty_isr, context_from_orchestrator):
        from constitutional_architecture.core.registry.compiler_registry import (
            CompilerMetadata, CompilerRegistry,
        )
        registry = CompilerRegistry()
        registry.register(TerraformCompiler, CompilerMetadata(
            compiler_id="terraform_aws",
            target_technology="terraform",
            supported_domains=["infrastructure"],
            required_genes=["deployment_topology"],
        ))
        resolved = registry.resolve_compilers(production_genome, empty_isr)
        assert "terraform_aws" in resolved
        compiler = registry.get_compiler("terraform_aws")
        bundle = compiler.compile(empty_isr, production_genome, context_from_orchestrator)
        assert bundle.compiler_id == "terraform_aws"


class TestCloudProviderAdapters:
    def test_aws_adapter_least_privilege_ingress(self):
        adapter = AWSAdapter()
        hcl = adapter.generate_network({"genome_id": "app", "backend_port": 8000})
        assert "10.0.1.0/24" in hcl
        assert hcl.count("0.0.0.0/0") == 1

    def test_gcp_adapter_emits_gcp_resources(self):
        adapter = GCPAdapter()
        assert "google_compute_network" in adapter.generate_network({})
        assert "google_cloud_run_service" in adapter.generate_compute({})
        assert "google_sql_database_instance" in adapter.generate_database(
            {"genome_id": "app", "requires_database": True},
        )

    def test_gcp_no_db_when_not_required(self):
        adapter = GCPAdapter()
        hcl = adapter.generate_database({"requires_database": False})
        assert "google_sql_database_instance" not in hcl
