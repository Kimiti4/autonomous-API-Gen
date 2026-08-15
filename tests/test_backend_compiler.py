import copy

import pytest

from constitutional_architecture.compilers.backend.fastapi.compiler import FastAPICompiler
from constitutional_architecture.core.models.genome import (
    ArchitectureGenome, MessagingTopology, PersistenceModel, SecurityModel,
)
from constitutional_architecture.core.models.isr import (
    EdgeType, ISREdge, ISRNode, NodeType, UniversalISR,
)


@pytest.fixture
def secure_isr() -> UniversalISR:
    isr = UniversalISR(intent_hash="abc", genome_hash="def")

    isr.add_node(ISRNode(id="entity_patient_record", type=NodeType.DATA_ENTITY))
    isr.add_node(ISRNode(id="entity_invoice", type=NodeType.DATA_ENTITY,
                         semantic_attributes={"fields": {"amount": "float"}}))

    isr.add_node(ISRNode(
        id="svc_medical",
        type=NodeType.SERVICE,
        semantic_attributes={"capability": "Medical", "security_classification": "restricted"},
    ))
    isr.add_node(ISRNode(
        id="svc_billing",
        type=NodeType.SERVICE,
        semantic_attributes={"capability": "Billing"},
    ))

    isr.add_node(ISRNode(
        id="sec_policy",
        type=NodeType.SECURITY_POLICY,
        semantic_attributes={"model": "zero_trust"},
    ))
    isr.add_edge(ISREdge(source_id="sec_policy", target_id="svc_medical", type=EdgeType.SECURES))

    return isr


@pytest.fixture
def zero_trust_genome() -> ArchitectureGenome:
    g = ArchitectureGenome()
    g.set_gene("security_model", SecurityModel.ZERO_TRUST)
    g.set_gene("persistence_model", PersistenceModel.RELATIONAL)
    g.set_gene("messaging_topology", MessagingTopology.ASYNC_EVENT_BUS)
    return g


class TestFastAPICompiler:
    def test_compiler_purity(self, secure_isr, zero_trust_genome):
        compiler = FastAPICompiler()
        snapshot = copy.deepcopy(secure_isr)
        compiler.compile(secure_isr, zero_trust_genome, {})
        assert secure_isr == snapshot

    def test_hexagonal_structure_generation(self, secure_isr, zero_trust_genome):
        compiler = FastAPICompiler()
        bundle = compiler.compile(secure_isr, zero_trust_genome, {})
        files = bundle.manifests[0].files

        assert "app/domain/patientrecord.py" in files
        assert "app/domain/invoice.py" in files
        assert "app/api/routers/medical.py" in files
        assert "app/api/routers/billing.py" in files
        assert "app/infrastructure/persistence/sqlalchemy_repo.py" in files
        assert "app/core/logging.py" in files
        assert "app/core/config.py" in files
        assert "app/main.py" in files
        assert "app/application/medical_usecase.py" in files
        assert "app/application/billing_usecase.py" in files

    def test_security_by_design_injection(self, secure_isr, zero_trust_genome):
        compiler = FastAPICompiler()
        bundle = compiler.compile(secure_isr, zero_trust_genome, {})
        files = bundle.manifests[0].files
        router_code = files["app/api/routers/medical.py"]
        deps_code = files["app/api/deps.py"]

        assert "verify_zero_trust_identity" in deps_code
        assert "Depends(verify_zero_trust_identity)" in router_code

    def test_unrestricted_service_uses_default_auth(self, secure_isr, zero_trust_genome):
        compiler = FastAPICompiler()
        bundle = compiler.compile(secure_isr, zero_trust_genome, {})
        billing_router = bundle.manifests[0].files["app/api/routers/billing.py"]
        assert "Depends(get_current_user)" in billing_router

    def test_rbac_security_generation(self, secure_isr):
        compiler = FastAPICompiler()
        rbac_genome = ArchitectureGenome()
        rbac_genome.set_gene("security_model", SecurityModel.RBAC)
        bundle = compiler.compile(secure_isr, rbac_genome, {})
        deps_code = bundle.manifests[0].files["app/api/deps.py"]
        assert "require_role" in deps_code
        assert "get_current_active_user" in deps_code

    def test_observability_middleware_injection(self, secure_isr, zero_trust_genome):
        compiler = FastAPICompiler()
        bundle = compiler.compile(secure_isr, zero_trust_genome, {})
        main_code = bundle.manifests[0].files["app/main.py"]

        assert "setup_observability" in main_code
        logging_code = bundle.manifests[0].files["app/core/logging.py"]
        assert "opentelemetry" in logging_code
        assert "structlog" in logging_code

    def test_persistence_adapter_from_genome(self, secure_isr, zero_trust_genome):
        compiler = FastAPICompiler()
        bundle = compiler.compile(secure_isr, zero_trust_genome, {})
        files = bundle.manifests[0].files

        assert "app/infrastructure/persistence/sqlalchemy_repo.py" in files

    def test_document_persistence_adapter(self, secure_isr):
        compiler = FastAPICompiler()
        doc_genome = ArchitectureGenome()
        doc_genome.set_gene("persistence_model", PersistenceModel.DOCUMENT)
        bundle = compiler.compile(secure_isr, doc_genome, {})
        files = bundle.manifests[0].files

        assert "app/infrastructure/persistence/mongo_repo.py" in files
        assert "app/infrastructure/persistence/sqlalchemy_repo.py" not in files

    def test_orchestration_context_exposure(self, secure_isr, zero_trust_genome):
        compiler = FastAPICompiler()
        bundle = compiler.compile(secure_isr, zero_trust_genome, {})

        assert bundle.exposed_interfaces["backend_port"] == 8000
        assert bundle.exposed_interfaces["backend_protocol"] == "http"
        assert bundle.exposed_interfaces["requires_message_broker"] is True
        assert bundle.exposed_interfaces["db_type"] == "relational"
        assert bundle.exposed_interfaces["security_model"] == "zero_trust"

    def test_no_message_broker_when_not_needed(self, secure_isr):
        compiler = FastAPICompiler()
        genome = ArchitectureGenome()
        genome.set_gene("messaging_topology", MessagingTopology.POINT_TO_POINT)
        bundle = compiler.compile(secure_isr, genome, {})
        assert bundle.exposed_interfaces["requires_message_broker"] is False

    def test_deterministic_output(self, secure_isr, zero_trust_genome):
        compiler = FastAPICompiler()
        bundle1 = compiler.compile(secure_isr, zero_trust_genome, {})
        bundle2 = compiler.compile(secure_isr, zero_trust_genome, {})
        assert bundle1.manifests[0].files == bundle2.manifests[0].files

    def test_returns_compilation_bundle(self, secure_isr, zero_trust_genome):
        compiler = FastAPICompiler()
        bundle = compiler.compile(secure_isr, zero_trust_genome, {})
        assert bundle.compiler_id == "fastapi_hexagonal"
        assert bundle.target_technology == "python_fastapi"
        assert len(bundle.manifests) == 1

    def test_registry_integration(self, secure_isr, zero_trust_genome):
        from constitutional_architecture.core.registry.compiler_registry import (
            CompilerMetadata, CompilerRegistry,
        )
        registry = CompilerRegistry()
        registry.register(FastAPICompiler, CompilerMetadata(
            compiler_id="fastapi_hexagonal",
            target_technology="python_fastapi",
            supported_domains=["backend"],
            required_genes=["app_arch"],
        ))
        resolved = registry.resolve_compilers(zero_trust_genome, secure_isr)
        assert "fastapi_hexagonal" in resolved
        compiler = registry.get_compiler("fastapi_hexagonal")
        bundle = compiler.compile(secure_isr, zero_trust_genome, {})
        assert bundle.compiler_id == "fastapi_hexagonal"
