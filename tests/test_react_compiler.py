import copy

import pytest

from constitutional_architecture.compilers.frontend.react.compiler import ReactCompiler
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.isr import (
    EdgeType, ISREdge, ISRNode, NodeType, UniversalISR,
)


@pytest.fixture
def sample_isr() -> UniversalISR:
    isr = UniversalISR(intent_hash="123", genome_hash="456")

    isr.add_node(ISRNode(id="entity_invoice", type=NodeType.DATA_ENTITY))
    isr.add_node(ISRNode(id="svc_billing", type=NodeType.SERVICE))
    isr.add_node(ISRNode(id="api_billing", type=NodeType.API_ENDPOINT))
    isr.add_edge(ISREdge(source_id="svc_billing", target_id="api_billing", type=EdgeType.EXPOSES))

    isr.add_node(ISRNode(
        id="sec_zero_trust",
        type=NodeType.SECURITY_POLICY,
        semantic_attributes={"model": "zero_trust"},
    ))
    isr.add_edge(ISREdge(source_id="sec_zero_trust", target_id="svc_billing", type=EdgeType.SECURES))

    isr.add_node(ISRNode(id="fe_dashboard", type=NodeType.FRONTEND_VIEW))

    return isr


class TestReactCompiler:
    def test_compiler_purity(self, sample_isr):
        compiler = ReactCompiler()
        snapshot = copy.deepcopy(sample_isr)
        compiler.compile(sample_isr, ArchitectureGenome(), {})
        assert sample_isr == snapshot

    def test_deterministic_file_generation(self, sample_isr):
        compiler = ReactCompiler()
        bundle = compiler.compile(sample_isr, ArchitectureGenome(), {})
        files = bundle.manifests[0].files
        assert "src/types/domain.ts" in files
        assert "src/api/client.ts" in files
        assert "src/App.tsx" in files

    def test_security_policy_injection(self, sample_isr):
        compiler = ReactCompiler()
        bundle = compiler.compile(sample_isr, ArchitectureGenome(), {})
        code = bundle.manifests[0].files["src/pages/BillingPage.tsx"]
        assert "zero_trust" in code.lower()

    def test_api_client_generation(self, sample_isr):
        compiler = ReactCompiler()
        bundle = compiler.compile(sample_isr, ArchitectureGenome(), {})
        api_code = bundle.manifests[0].files["src/api/client.ts"]
        assert "api_billing" in api_code
        assert "axios" in api_code

    def test_typescript_types_generated(self, sample_isr):
        compiler = ReactCompiler()
        bundle = compiler.compile(sample_isr, ArchitectureGenome(), {})
        types_code = bundle.manifests[0].files["src/types/domain.ts"]
        assert "Invoice" in types_code

    def test_exposed_interfaces(self, sample_isr):
        compiler = ReactCompiler()
        bundle = compiler.compile(sample_isr, ArchitectureGenome(), {})
        assert bundle.exposed_interfaces["frontend_port"] == 3000
        assert bundle.exposed_interfaces["frontend_build_cmd"] == "npm run build"

    def test_returns_compilation_bundle(self, sample_isr):
        compiler = ReactCompiler()
        bundle = compiler.compile(sample_isr, ArchitectureGenome(), {})
        assert bundle.compiler_id == "react_vite"
        assert bundle.target_technology == "react"
        assert len(bundle.manifests) == 1
