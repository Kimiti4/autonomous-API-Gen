"""D05 regression: the constitutional test compiler never emits vacuous layers.

The compiler previously wrote a chaos suite containing only ``assert True`` and
a pact contract suite containing only ``assert pact is not None``. Both passed
without exercising a candidate. They are now declared unsupported in the
manifest and not emitted at all.
"""

from __future__ import annotations

import pytest

from constitutional_architecture.compilers.testing.pytest.compiler import PytestCompiler
from constitutional_architecture.core.models.genome import (
    ApplicationArchitecture, ArchitectureGenome,
)
from constitutional_architecture.core.models.isr import (
    EdgeType, ISREdge, ISRNode, NodeType, UniversalISR,
)


def _genome(app_arch: ApplicationArchitecture, posture: str) -> ArchitectureGenome:
    genome = ArchitectureGenome(genome_id="d05", intent_hash="1")
    genome.set_gene("app_arch", app_arch)
    genome.set_gene("resilience_posture", posture)
    return genome


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
        source_id="entity_order",
        target_id="attr_order_total",
        type=EdgeType.HAS_ATTRIBUTE,
    ))
    isr.add_node(ISRNode(
        id="api_orders",
        type=NodeType.API_ENDPOINT,
        semantic_attributes={"path": "/v1/orders", "protocol": "rest"},
    ))
    return isr


def _manifest(isr: UniversalISR, genome: ArchitectureGenome):
    return PytestCompiler().compile(isr, genome, {}).manifests[0]


@pytest.mark.parametrize(
    ("app_arch", "posture"),
    [
        (ApplicationArchitecture.MICROSERVICES, "circuit_breaker"),
        (ApplicationArchitecture.EVENT_DRIVEN, "circuit_breaker"),
        (ApplicationArchitecture.MODULAR_MONOLITH, "fail_fast"),
    ],
)
def test_no_generated_file_contains_a_vacuous_assertion(isr, app_arch, posture):
    manifest = _manifest(isr, _genome(app_arch, posture))

    for path, content in manifest.files.items():
        assert "assert True" not in content, path
        assert "assert pact is not None" not in content, path
        assert "assert Provider(" not in content, path


def test_contract_layer_is_declared_but_not_emitted(isr):
    manifest = _manifest(
        isr, _genome(ApplicationArchitecture.MICROSERVICES, "fail_fast"),
    )

    assert "tests/contract/test_service_contracts.py" not in manifest.files
    assert "pact" in manifest.metadata["unsupported_layers"]["contract"]
    assert "contract" not in manifest.metadata["layers"]


def test_chaos_layer_is_declared_but_not_emitted(isr):
    manifest = _manifest(
        isr, _genome(ApplicationArchitecture.MODULAR_MONOLITH, "circuit_breaker"),
    )

    assert "tests/chaos/test_resilience.py" not in manifest.files
    assert "circuit-breaker" in manifest.metadata["unsupported_layers"]["chaos"]
    assert "chaos" not in manifest.metadata["layers"]


def test_event_driven_circuit_breaker_declares_both_gaps(isr):
    manifest = _manifest(
        isr, _genome(ApplicationArchitecture.EVENT_DRIVEN, "circuit_breaker"),
    )

    assert set(manifest.metadata["unsupported_layers"]) == {"contract", "chaos"}


def test_fail_fast_monolith_declares_no_gaps(isr):
    manifest = _manifest(
        isr, _genome(ApplicationArchitecture.MODULAR_MONOLITH, "fail_fast"),
    )

    assert manifest.metadata["unsupported_layers"] == {}


def test_declared_layers_are_exactly_the_emitted_files(isr):
    manifest = _manifest(
        isr, _genome(ApplicationArchitecture.MICROSERVICES, "circuit_breaker"),
    )

    assert manifest.metadata["layers"] == ["unit", "integration", "security"]
    assert set(manifest.files) == {
        "tests/conftest.py",
        "tests/unit/test_domain_invariants.py",
        "tests/integration/test_api_security.py",
    }


def test_security_tests_assert_on_observable_responses(isr):
    manifest = _manifest(
        isr, _genome(ApplicationArchitecture.MODULAR_MONOLITH, "fail_fast"),
    )

    security = manifest.files["tests/integration/test_api_security.py"]
    assert "status_code" in security
    assert "assert" in security
