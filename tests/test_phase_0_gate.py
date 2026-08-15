"""
Phase 0 Exit Gate Verification — proves the ConstitutionValidator
rejects architecturally invalid changes at runtime.

Tests:
  1. Rejecting Technology Coupling  — ISR node with forbidden terms
  2. Rejecting Impure Compilers    — backend that mutates the ISR
  3. Security by Design             — service without SecurityPolicy dep
  4. Cycle Detection                — cyclic ISR dependency graph
"""

import copy

import pytest

from constitutional_architecture.compiler.contract import CompilationArtifact, CompilerBackend
from constitutional_architecture.core.governance import GovernanceRules
from constitutional_architecture.core.models.universal_isr import ISRNode, NodeType, UniversalISR
from constitutional_architecture.validators import ConstitutionalViolation, ConstitutionValidator


# ==============================================================================
# Test 1: Rejecting Technology Coupling
# ==============================================================================

def test_rejects_technology_coupling():
    """An engineer attempts to add a DB node with a forbidden technology term."""
    isr = UniversalISR()
    invalid_node = ISRNode(
        id="user_db",
        type=NodeType.DATA_ENTITY,
        attributes={"engine": "postgres", "version": "14"},
    )
    isr.add_node(invalid_node)

    validator = ConstitutionValidator()
    with pytest.raises(ConstitutionalViolation, match="forbidden technology coupling"):
        validator.validate_isr_mutation(isr)


def test_accepts_technology_agnostic_isr():
    """A clean ISR with no forbidden terms passes the gate."""
    isr = UniversalISR()
    clean_node = ISRNode(
        id="user_data",
        type=NodeType.DATA_ENTITY,
        attributes={"consistency": "strong", "retention_days": 90},
    )
    isr.add_node(clean_node)

    validator = ConstitutionValidator()
    validator.validate_isr_mutation(isr)  # should not raise


# ==============================================================================
# Test 2: Rejecting Impure Compilers
# ==============================================================================

class BadReactCompiler(CompilerBackend):
    """A deliberately impure compiler that mutates the ISR during compilation."""

    def compile(self, isr, target_profile, constraints):
        isr.metadata["last_compiled_by"] = "react_backend"
        return CompilationArtifact(
            backend_name="react",
            target_profile=target_profile,
            files={"App.tsx": "export default function App() { return null; }"},
            metadata={},
        )


class PureCompiler(CompilerBackend):
    """A well-behaved compiler that does not mutate the ISR."""

    def compile(self, isr, target_profile, constraints):
        return CompilationArtifact(
            backend_name="test",
            target_profile=target_profile,
            files={"output.txt": "hello"},
            metadata={"compiled": True},
        )


def test_rejects_impure_compiler():
    """A compiler that mutates the ISR metadata must be rejected."""
    isr = UniversalISR()
    isr.add_node(ISRNode(id="svc", type=NodeType.SERVICE, attributes={}))
    isr.add_node(ISRNode(id="sec", type=NodeType.SECURITY_POLICY, attributes={}))
    isr.nodes["svc"].dependencies.append("sec")

    validator = ConstitutionValidator()
    with pytest.raises(ConstitutionalViolation, match="illegally mutated"):
        validator.validate_compiler_purity(BadReactCompiler(), isr)


def test_accepts_pure_compiler():
    """A pure compiler that does not mutate the ISR passes."""
    isr = UniversalISR()
    isr.add_node(ISRNode(id="svc", type=NodeType.SERVICE, attributes={}))
    isr.add_node(ISRNode(id="sec", type=NodeType.SECURITY_POLICY, attributes={}))
    isr.nodes["svc"].dependencies.append("sec")

    validator = ConstitutionValidator()
    validator.validate_compiler_purity(PureCompiler(), isr)  # should not raise


# ==============================================================================
# Test 3: Security by Design
# ==============================================================================

def test_rejects_missing_security_policy():
    """An API endpoint without a SecurityPolicy dependency must be rejected."""
    isr = UniversalISR()
    isr.add_node(ISRNode(
        id="public_api",
        type=NodeType.API_ENDPOINT,
        attributes={"rate_limit": "100/min"},
        dependencies=["some_service"],
    ))
    isr.add_node(ISRNode(
        id="some_service",
        type=NodeType.SERVICE,
        attributes={},
    ))

    validator = ConstitutionValidator()
    with pytest.raises(ConstitutionalViolation, match="Security by Design"):
        validator.validate_isr_mutation(isr)


def test_accepts_secure_api():
    """An API endpoint with a SecurityPolicy dependency passes."""
    isr = UniversalISR()
    isr.add_node(ISRNode(id="api", type=NodeType.API_ENDPOINT, attributes={}))
    isr.add_node(ISRNode(id="auth", type=NodeType.SECURITY_POLICY, attributes={}))
    isr.nodes["api"].dependencies.append("auth")

    validator = ConstitutionValidator()
    validator.validate_isr_mutation(isr)  # should not raise


# ==============================================================================
# Test 4: Cycle Detection
# ==============================================================================

def test_rejects_cyclic_dependencies():
    """An ISR with a cycle in its dependency graph must be rejected."""
    isr = UniversalISR()
    isr.add_node(ISRNode(id="a", type=NodeType.DOMAIN, attributes={}))
    isr.add_node(ISRNode(id="b", type=NodeType.DOMAIN, attributes={}))
    isr.add_node(ISRNode(id="c", type=NodeType.DOMAIN, attributes={}))
    isr.nodes["a"].dependencies.append("b")
    isr.nodes["b"].dependencies.append("c")
    isr.nodes["c"].dependencies.append("a")  # cycle: a -> b -> c -> a

    validator = ConstitutionValidator()
    with pytest.raises(ConstitutionalViolation, match="cyclic"):
        validator.validate_isr_mutation(isr)


def test_accepts_acyclic_graph():
    """An ISR without cycles passes."""
    isr = UniversalISR()
    isr.add_node(ISRNode(id="a", type=NodeType.DOMAIN, attributes={}))
    isr.add_node(ISRNode(id="b", type=NodeType.DOMAIN, attributes={}))
    isr.add_node(ISRNode(id="c", type=NodeType.DOMAIN, attributes={}))
    isr.nodes["a"].dependencies.append("b")
    isr.nodes["b"].dependencies.append("c")

    validator = ConstitutionValidator()
    validator.validate_isr_mutation(isr)  # should not raise


# ==============================================================================
# Test 5: GovernanceRules Static Methods
# ==============================================================================

class TestGovernanceRules:
    def test_is_technology_agnostic_true(self):
        assert GovernanceRules.is_technology_agnostic({"consistency": "strong"})

    def test_is_technology_agnostic_false(self):
        assert not GovernanceRules.is_technology_agnostic({"db": "postgres"})

    def test_nested_scan(self):
        assert not GovernanceRules.is_technology_agnostic({
            "config": {"database": "mongodb"},
        })

    def test_security_by_design_true(self):
        nodes = {
            "api": ISRNode(id="api", type=NodeType.API_ENDPOINT, dependencies=["auth"]),
            "auth": ISRNode(id="auth", type=NodeType.SECURITY_POLICY),
        }
        assert GovernanceRules.has_security_by_design(nodes)

    def test_security_by_design_false(self):
        nodes = {
            "api": ISRNode(id="api", type=NodeType.API_ENDPOINT, dependencies=[]),
        }
        assert not GovernanceRules.has_security_by_design(nodes)


# ==============================================================================
# Test 6: UniversalISR Model
# ==============================================================================

class TestUniversalISR:
    def test_add_node(self):
        isr = UniversalISR()
        node = ISRNode(id="n1", type=NodeType.DOMAIN)
        isr.add_node(node)
        assert isr.nodes["n1"] == node

    def test_add_duplicate_node_raises(self):
        isr = UniversalISR()
        isr.add_node(ISRNode(id="n1", type=NodeType.DOMAIN))
        with pytest.raises(ValueError, match="already exists"):
            isr.add_node(ISRNode(id="n1", type=NodeType.DOMAIN))

    def test_node_type_values(self):
        assert NodeType.DOMAIN.value == "Domain"
        assert NodeType.SERVICE.value == "Service"
        assert NodeType.API_ENDPOINT.value == "APIEndpoint"
        assert NodeType.SECURITY_POLICY.value == "SecurityPolicy"
        assert NodeType.DATA_ENTITY.value == "DataEntity"
