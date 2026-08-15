import pytest

from constitutional_architecture.compilers.testing.pytest.compiler import PytestCompiler
from constitutional_architecture.core.models.genome import (
    ApplicationArchitecture, ArchitectureGenome,
)
from constitutional_architecture.core.models.isr import (
    EdgeType, ISREdge, ISRNode, NodeType, UniversalISR,
)


@pytest.fixture
def microservice_genome() -> ArchitectureGenome:
    g = ArchitectureGenome(genome_id="g1", intent_hash="1")
    g.set_gene("app_arch", ApplicationArchitecture.MICROSERVICES)
    return g


@pytest.fixture
def isr() -> UniversalISR:
    isr = UniversalISR(intent_hash="1", genome_hash="1")
    isr.add_node(ISRNode(
        id="entity_order",
        type=NodeType.DATA_ENTITY,
        semantic_attributes={"consistency": "strong"},
    ))
    isr.add_node(ISRNode(
        id="attr_order_total",
        type=NodeType.DATA_ATTRIBUTE,
        semantic_attributes={"required": True, "min_length": 1},
    ))
    isr.add_edge(ISREdge(
        source_id="entity_order", target_id="attr_order_total", type=EdgeType.HAS_ATTRIBUTE,
    ))
    isr.add_node(ISRNode(
        id="svc_orders",
        type=NodeType.SERVICE,
        semantic_attributes={"capability": "Orders", "security_classification": "restricted"},
    ))
    isr.add_node(ISRNode(
        id="api_orders",
        type=NodeType.API_ENDPOINT,
        semantic_attributes={"path": "/v1/orders", "protocol": "rest"},
    ))
    isr.add_edge(ISREdge(source_id="svc_orders", target_id="api_orders", type=EdgeType.EXPOSES))
    isr.add_node(ISRNode(
        id="svc_payments",
        type=NodeType.SERVICE,
        semantic_attributes={"capability": "Payments", "security_classification": "internal"},
    ))
    isr.add_edge(ISREdge(source_id="svc_orders", target_id="svc_payments", type=EdgeType.DEPENDS_ON))
    return isr


def files_of(bundle):
    return bundle.manifests[0].files


class TestPytestCompiler:
    def test_compiles_layered_suite(self, microservice_genome, isr):
        compiler = PytestCompiler()
        files = files_of(compiler.compile(isr, microservice_genome, {}))
        assert "tests/conftest.py" in files
        assert "tests/unit/test_domain_invariants.py" in files
        assert "tests/integration/test_api_security.py" in files

    def test_generates_contract_tests_for_microservices(self, microservice_genome, isr):
        compiler = PytestCompiler()
        files = files_of(compiler.compile(isr, microservice_genome, {}))
        assert "tests/contract/test_service_contracts.py" in files

    def test_generates_chaos_tests_for_resilience_posture(self, microservice_genome, isr):
        compiler = PytestCompiler()
        files = files_of(compiler.compile(isr, microservice_genome, {}))
        assert "tests/chaos/test_resilience.py" in files
        assert "circuit_breaker" in files["tests/chaos/test_resilience.py"]

    def test_no_contract_tests_for_monolith(self, isr):
        mono_genome = ArchitectureGenome(genome_id="g2", intent_hash="1")
        mono_genome.set_gene("app_arch", ApplicationArchitecture.MODULAR_MONOLITH)
        compiler = PytestCompiler()
        files = files_of(compiler.compile(isr, mono_genome, {}))
        assert "tests/contract/test_service_contracts.py" not in files

    def test_no_chaos_tests_for_fail_fast(self, isr):
        ff_genome = ArchitectureGenome(genome_id="g3", intent_hash="1")
        ff_genome.set_gene("app_arch", ApplicationArchitecture.MODULAR_MONOLITH)
        ff_genome.set_gene("resilience_posture", "fail_fast")
        compiler = PytestCompiler()
        files = files_of(compiler.compile(isr, ff_genome, {}))
        assert "tests/chaos/test_resilience.py" not in files

    def test_conftest_fixtures_per_entity(self, microservice_genome, isr):
        compiler = PytestCompiler()
        conftest = files_of(compiler.compile(isr, microservice_genome, {}))["tests/conftest.py"]
        assert "def order_factory()" in conftest
        assert "test-uuid-order" in conftest

    def test_property_tests_from_entity_attributes(self, microservice_genome, isr):
        compiler = PytestCompiler()
        props = files_of(compiler.compile(isr, microservice_genome, {}))[
            "tests/unit/test_domain_invariants.py"
        ]
        assert "from hypothesis import given, strategies as st" in props
        assert "test_order_order_total_invariant" in props
        assert "ISR constraint violation" in props

    def test_restricted_endpoint_requires_strict_auth(self, microservice_genome, isr):
        compiler = PytestCompiler()
        tests = files_of(compiler.compile(isr, microservice_genome, {}))[
            "tests/integration/test_api_security.py"
        ]
        assert "test_orders_requires_strict_auth" in tests
        assert "assert response.status_code in [401, 403]" in tests

    def test_zero_trust_genome_requires_authentication(self):
        isr = UniversalISR(intent_hash="1", genome_hash="1")
        isr.add_node(ISRNode(
            id="api_catalog",
            type=NodeType.API_ENDPOINT,
            semantic_attributes={"path": "/v1/catalog", "protocol": "rest"},
        ))
        genome = ArchitectureGenome()
        genome.set_gene("security_arch", "zero_trust")
        compiler = PytestCompiler()
        tests = files_of(compiler.compile(isr, genome, {}))[
            "tests/integration/test_api_security.py"
        ]
        assert "test_catalog_requires_authentication" in tests

    def test_contract_tests_cover_service_dependencies(self, microservice_genome, isr):
        compiler = PytestCompiler()
        contracts = files_of(compiler.compile(isr, microservice_genome, {}))[
            "tests/contract/test_service_contracts.py"
        ]
        assert "test_contract_orders_to_payments" in contracts
        assert "pact" in contracts

    def test_deterministic_output(self, microservice_genome, isr):
        compiler = PytestCompiler()
        bundle1 = compiler.compile(isr, microservice_genome, {})
        bundle2 = compiler.compile(isr, microservice_genome, {})
        assert files_of(bundle1) == files_of(bundle2)

    def test_returns_compilation_bundle(self, microservice_genome, isr):
        compiler = PytestCompiler()
        bundle = compiler.compile(isr, microservice_genome, {})
        assert bundle.compiler_id == "pytest_layered"
        assert bundle.target_technology == "pytest"
        assert bundle.manifests[0].metadata["layers"] == [
            "unit", "integration", "security", "contract", "chaos",
        ]

    def test_compiler_purity(self, microservice_genome, isr):
        import copy
        compiler = PytestCompiler()
        snapshot = copy.deepcopy(isr)
        compiler.compile(isr, microservice_genome, {})
        assert isr == snapshot
