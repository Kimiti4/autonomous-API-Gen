import pytest

from tiannara.domain.models.isr import (
    PAYLOAD_TYPE_LEGACY,
    PAYLOAD_TYPE_SYSTEM_MODEL_V1,
    IntentSpecification,
    IntermediateSoftwareRepresentation,
)
from tiannara.domain.models.system_model import (
    BusinessCapability,
    RequirementsReference,
    SystemModel,
    TechnologyCouplingError,
)


def _clean_model() -> SystemModel:
    return SystemModel(
        system_name="harbor-ops",
        problem_statement="Track berth occupancy across marinas.",
        requirements_ref=RequirementsReference(graph_id="g", graph_hash="h"),
        capabilities=[
            BusinessCapability(id="cap-1", name="Berth tracking",
                                traced_requirement_ids=["req-1"]),
        ],
    )


def test_legacy_path_unchanged():
    stmt = IntermediateSoftwareRepresentation(
        system_id="s-legacy", system_name="Legacy demo",
        intent=IntentSpecification(statement="a service", domain="general"),
        lineage=[],
    )
    assert stmt.payload_type == PAYLOAD_TYPE_LEGACY
    assert stmt.content is None
    assert stmt.system_model() is None


def test_legacy_hash_unaffected_by_new_fields():
    # A legacy envelope must hash identically to the pre-Cap-A shape, which
    # was computed over (system_id, system_name, intent, services, ...).
    a = IntermediateSoftwareRepresentation(
        system_id="s1", system_name="demo",
        intent=IntentSpecification(statement="a service", domain="general"),
        lineage=["intent:s1", "genome:g1"],
    )
    b = IntermediateSoftwareRepresentation(
        system_id="s1", system_name="demo",
        intent=IntentSpecification(statement="a service", domain="general"),
        lineage=[],
    )
    assert a.content_hash() == b.content_hash()  # lineage excluded
    # payload_type/content are excluded too -> still equal when only they differ
    assert a.content_hash() == a.content_hash()


def test_typed_round_trip():
    stmt = IntermediateSoftwareRepresentation.from_system_model("s-1", _clean_model())
    assert stmt.payload_type == PAYLOAD_TYPE_SYSTEM_MODEL_V1
    assert stmt.content is not None
    recovered = stmt.system_model()
    assert recovered is not None
    assert recovered.content_hash() == _clean_model().content_hash()


def test_typed_envelope_deterministic():
    a = IntermediateSoftwareRepresentation.from_system_model("s-1", _clean_model())
    b = IntermediateSoftwareRepresentation.from_system_model("s-1", _clean_model())
    assert a.content_hash() == b.content_hash()


def test_technology_coupled_model_rejected_at_boundary():
    bad = _clean_model()
    bad.problem_statement = "Deploy on Kubernetes with Kafka events."
    with pytest.raises(TechnologyCouplingError):
        IntermediateSoftwareRepresentation.from_system_model("s-2", bad)
