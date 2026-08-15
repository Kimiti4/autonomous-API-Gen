import pytest

from constitutional_architecture.compilers.runtime_policy.compiler import (
    RuntimePolicyCompiler,
)
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.isr import (
    EdgeType, ISREdge, ISRNode, NodeType, UniversalISR,
)


@pytest.fixture
def genome() -> ArchitectureGenome:
    return ArchitectureGenome(genome_id="g1", intent_hash="1")


@pytest.fixture
def isr() -> UniversalISR:
    isr = UniversalISR(intent_hash="1", genome_hash="1")
    isr.add_node(ISRNode(
        id="sec_policy_zero_trust",
        type=NodeType.SECURITY_POLICY,
        semantic_attributes={
            "model": "zero_trust",
            "encryption_at_rest": True,
            "audit_logging": True,
        },
    ))
    isr.add_node(ISRNode(
        id="svc_billing",
        type=NodeType.SERVICE,
        semantic_attributes={"capability": "Billing", "security_classification": "restricted"},
    ))
    isr.add_node(ISRNode(
        id="api_billing",
        type=NodeType.API_ENDPOINT,
        semantic_attributes={"path": "/v1/billing", "protocol": "rest"},
    ))
    isr.add_edge(ISREdge(source_id="svc_billing", target_id="api_billing", type=EdgeType.EXPOSES))
    isr.add_node(ISRNode(
        id="api_catalog",
        type=NodeType.API_ENDPOINT,
        semantic_attributes={"path": "/v1/catalog", "protocol": "rest"},
    ))
    return isr


def files_of(bundle):
    return bundle.manifests[0].files


class TestRuntimePolicyCompiler:
    def test_compiles_policy_manifests(self, genome, isr):
        compiler = RuntimePolicyCompiler()
        files = files_of(compiler.compile(isr, genome, {}))
        assert "policies/authz.rego" in files
        assert "policies/rate_limit.yaml" in files

    def test_zero_trust_rego_requires_identity(self, genome, isr):
        compiler = RuntimePolicyCompiler()
        rego = files_of(compiler.compile(isr, genome, {}))["policies/authz.rego"]
        assert "package authz" in rego
        assert "default allow = false" in rego
        assert "input.authenticated == true" in rego

    def test_perimeter_model_trusts_internal_network(self, genome, isr):
        for node in isr.nodes.values():
            if node.type == NodeType.SECURITY_POLICY:
                node.semantic_attributes["model"] = "perimeter"
        compiler = RuntimePolicyCompiler()
        rego = files_of(compiler.compile(isr, genome, {}))["policies/authz.rego"]
        assert 'input.network == "internal"' in rego
        assert "input.authenticated" not in rego

    def test_rbac_fallback_denies_by_default(self, genome, isr):
        for node in isr.nodes.values():
            if node.type == NodeType.SECURITY_POLICY:
                node.semantic_attributes["model"] = "rbac"
        compiler = RuntimePolicyCompiler()
        rego = files_of(compiler.compile(isr, genome, {}))["policies/authz.rego"]
        assert "default allow = false" in rego
        assert 'input.role == "admin"' in rego

    def test_strict_compliance_requires_audit_id(self, genome, isr):
        isr.add_node(ISRNode(
            id="op_policy_circuit_breaker",
            type=NodeType.OPERATIONAL_POLICY,
            semantic_attributes={"auditability_level": "strict_compliance"},
        ))
        compiler = RuntimePolicyCompiler()
        rego = files_of(compiler.compile(isr, genome, {}))["policies/authz.rego"]
        assert 'input.audit_id != ""' in rego

    def test_rate_limits_per_endpoint(self, genome, isr):
        compiler = RuntimePolicyCompiler()
        limits = files_of(compiler.compile(isr, genome, {}))["policies/rate_limit.yaml"]
        assert 'value: "/v1/billing"' in limits
        assert 'value: "/v1/catalog"' in limits

    def test_restricted_endpoint_gets_tighter_limit(self, genome, isr):
        compiler = RuntimePolicyCompiler()
        limits = files_of(compiler.compile(isr, genome, {}))["policies/rate_limit.yaml"]
        billing = limits.split('value: "/v1/billing"')[1].split("requests_per_unit:")[1].split()[0]
        assert billing == "10"

    def test_deterministic_output(self, genome, isr):
        compiler = RuntimePolicyCompiler()
        bundle1 = compiler.compile(isr, genome, {})
        bundle2 = compiler.compile(isr, genome, {})
        assert files_of(bundle1) == files_of(bundle2)

    def test_returns_compilation_bundle(self, genome, isr):
        compiler = RuntimePolicyCompiler()
        bundle = compiler.compile(isr, genome, {})
        assert bundle.compiler_id == "runtime_policy_v1"
        assert bundle.target_technology == "opa_envoy"
        assert bundle.manifests[0].metadata["enforcement_points"] == ["opa", "envoy", "kong"]
