import copy

import pytest

from constitutional_architecture.compilers.database.postgres.compiler import PostgresCompiler
from constitutional_architecture.core.models.genome import (
    ArchitectureGenome, TenancyStrategy,
)
from constitutional_architecture.core.models.isr import (
    EdgeType, ISREdge, ISRNode, NodeType, UniversalISR,
)


@pytest.fixture
def multi_tenant_isr() -> UniversalISR:
    isr = UniversalISR(intent_hash="1", genome_hash="1")

    isr.add_node(ISRNode(id="entity_customer", type=NodeType.DATA_ENTITY))
    isr.add_node(ISRNode(
        id="attr_email",
        type=NodeType.DATA_ATTRIBUTE,
        semantic_attributes={"name": "email", "sql_type": "VARCHAR(255)"},
    ))
    isr.add_edge(ISREdge(source_id="entity_customer", target_id="attr_email", type=EdgeType.HAS_ATTRIBUTE))

    return isr


@pytest.fixture
def relational_isr() -> UniversalISR:
    isr = UniversalISR(intent_hash="1", genome_hash="1")

    isr.add_node(ISRNode(id="entity_order", type=NodeType.DATA_ENTITY))
    isr.add_node(ISRNode(
        id="attr_status",
        type=NodeType.DATA_ATTRIBUTE,
        semantic_attributes={"name": "status", "sql_type": "VARCHAR(32)"},
    ))
    isr.add_node(ISRNode(id="entity_customer", type=NodeType.DATA_ENTITY))

    isr.add_edge(ISREdge(source_id="entity_order", target_id="attr_status", type=EdgeType.HAS_ATTRIBUTE))
    isr.add_edge(ISREdge(source_id="entity_order", target_id="entity_customer", type=EdgeType.RELATES_TO))

    return isr


@pytest.fixture
def multi_tenant_genome() -> ArchitectureGenome:
    g = ArchitectureGenome(genome_id="g1", intent_hash="1")
    g.set_gene("tenancy_strategy", TenancyStrategy.MULTI_TENANT_SHARED)
    return g


@pytest.fixture
def single_tenant_genome() -> ArchitectureGenome:
    g = ArchitectureGenome(genome_id="g1", intent_hash="1")
    g.set_gene("tenancy_strategy", TenancyStrategy.SINGLE_TENANT)
    return g


class TestPostgresCompiler:
    def test_compiler_purity(self, multi_tenant_isr, multi_tenant_genome):
        compiler = PostgresCompiler()
        snapshot = copy.deepcopy(multi_tenant_isr)
        compiler.compile(multi_tenant_isr, multi_tenant_genome, {})
        assert multi_tenant_isr == snapshot

    def test_schema_compiled_directly_from_isr(self, multi_tenant_isr, multi_tenant_genome):
        compiler = PostgresCompiler()
        bundle = compiler.compile(multi_tenant_isr, multi_tenant_genome, {})

        schema_sql = bundle.manifests[0].files["schema.sql"]

        assert "CREATE TABLE customer" in schema_sql
        assert "email VARCHAR(255)" in schema_sql
        assert "tenant_id UUID NOT NULL" in schema_sql

    def test_security_by_design_rls_generation(self, multi_tenant_isr, multi_tenant_genome):
        compiler = PostgresCompiler()
        bundle = compiler.compile(multi_tenant_isr, multi_tenant_genome, {})

        rls_sql = bundle.manifests[0].files["rls_policies.sql"]

        assert "ENABLE ROW LEVEL SECURITY" in rls_sql
        assert "tenant_isolation_policy" in rls_sql
        assert "customer" in rls_sql

    def test_single_tenant_no_rls_no_tenant_id(self, multi_tenant_isr, single_tenant_genome):
        compiler = PostgresCompiler()
        bundle = compiler.compile(multi_tenant_isr, single_tenant_genome, {})

        files = bundle.manifests[0].files
        assert "rls_policies.sql" not in files
        assert "tenant_id" not in files["schema.sql"]

    def test_foreign_keys_from_relates_to(self, relational_isr, multi_tenant_genome):
        compiler = PostgresCompiler()
        bundle = compiler.compile(relational_isr, multi_tenant_genome, {})

        schema_sql = bundle.manifests[0].files["schema.sql"]
        assert "customer_id UUID REFERENCES customer(id)" in schema_sql

    def test_alembic_migration_generated(self, multi_tenant_isr, multi_tenant_genome):
        compiler = PostgresCompiler()
        bundle = compiler.compile(multi_tenant_isr, multi_tenant_genome, {})

        migration = bundle.manifests[0].files["alembic/versions/001_initial_schema.py"]
        assert "from alembic import op" in migration
        assert "def upgrade()" in migration
        assert "schema.sql" in migration

    def test_attribute_nullability(self, multi_tenant_isr, multi_tenant_genome):
        isr = copy.deepcopy(multi_tenant_isr)
        isr.add_node(ISRNode(
            id="attr_phone",
            type=NodeType.DATA_ATTRIBUTE,
            semantic_attributes={"name": "phone", "sql_type": "VARCHAR(20)", "optional": True},
        ))
        isr.add_edge(ISREdge(source_id="entity_customer", target_id="attr_phone", type=EdgeType.HAS_ATTRIBUTE))

        compiler = PostgresCompiler()
        bundle = compiler.compile(isr, multi_tenant_genome, {})

        schema_sql = bundle.manifests[0].files["schema.sql"]
        assert "phone VARCHAR(20) NULL" in schema_sql
        assert "email VARCHAR(255) NOT NULL" in schema_sql

    def test_deterministic_output(self, multi_tenant_isr, multi_tenant_genome):
        compiler = PostgresCompiler()
        bundle1 = compiler.compile(multi_tenant_isr, multi_tenant_genome, {})
        bundle2 = compiler.compile(multi_tenant_isr, multi_tenant_genome, {})
        assert bundle1.manifests[0].files == bundle2.manifests[0].files

    def test_returns_compilation_bundle(self, multi_tenant_isr, multi_tenant_genome):
        compiler = PostgresCompiler()
        bundle = compiler.compile(multi_tenant_isr, multi_tenant_genome, {})
        assert bundle.compiler_id == "postgres_alembic"
        assert bundle.target_technology == "postgresql"
        assert bundle.exposed_interfaces["db_connection_string_env"] == "DATABASE_URL"
        assert bundle.manifests[0].artifact_type.value == "database_migration"
        assert bundle.manifests[0].metadata["engine"] == "postgresql"
        assert bundle.manifests[0].metadata["migration_tool"] == "alembic"

    def test_registry_integration(self, multi_tenant_isr, multi_tenant_genome):
        from constitutional_architecture.core.registry.compiler_registry import (
            CompilerMetadata, CompilerRegistry,
        )
        registry = CompilerRegistry()
        registry.register(PostgresCompiler, CompilerMetadata(
            compiler_id="postgres_alembic",
            target_technology="postgresql",
            supported_domains=["database"],
            required_genes=["persistence_model"],
        ))
        resolved = registry.resolve_compilers(multi_tenant_genome, multi_tenant_isr)
        assert "postgres_alembic" in resolved
        compiler = registry.get_compiler("postgres_alembic")
        bundle = compiler.compile(multi_tenant_isr, multi_tenant_genome, {})
        assert bundle.compiler_id == "postgres_alembic"

    def test_policy_extraction_from_governed_by(self, multi_tenant_isr, multi_tenant_genome):
        isr = copy.deepcopy(multi_tenant_isr)
        isr.add_node(ISRNode(id="retention_5yr", type=NodeType.RETENTION_POLICY,
                             semantic_attributes={"duration_days": 1825}))
        isr.add_edge(ISREdge(source_id="entity_customer", target_id="retention_5yr", type=EdgeType.GOVERNED_BY))

        compiler = PostgresCompiler()
        bundle = compiler.compile(isr, multi_tenant_genome, {})
        assert bundle is not None
