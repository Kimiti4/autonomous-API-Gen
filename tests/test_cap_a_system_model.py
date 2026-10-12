import pytest

from tiannara.domain.models.system_model import (
    AbstractFieldType,
    DataModelSpec,
    FieldSpec,
    BusinessCapability,
    RequirementsReference,
    SystemModel,
    TechnologyCouplingError,
    scan_for_technology_coupling,
)


def _model(**overrides) -> SystemModel:
    base = dict(
        system_name="vessel-booking",
        problem_statement="Coordinate on-demand boat rides between marinas.",
        requirements_ref=RequirementsReference(graph_id="g-1", graph_hash="h-1"),
        capabilities=[
            BusinessCapability(
                id="cap-1", name="Ride booking", traced_requirement_ids=["req-1"]
            )
        ],
    )
    base.update(overrides)
    return SystemModel(**base)


def test_defaults_are_complete_and_deterministic():
    m = _model()
    assert m.security.encryption_in_transit_required is True
    assert len(m.operational_policies.observability_requirements) == 6
    assert m.content_hash() == _model().content_hash()


def test_hash_stable_across_construction_order():
    a = _model()
    b = SystemModel.model_validate(a.model_dump(mode="json"))
    assert a.content_hash() == b.content_hash()


def test_enumeration_field_requires_values():
    with pytest.raises(ValueError):
        FieldSpec(name="status", type=AbstractFieldType.ENUMERATION)


def test_technology_scan_detects_coupling():
    m = _model(problem_statement="Build it with FastAPI and PostgreSQL backends.")
    violations = scan_for_technology_coupling(m)
    tokens = {v.token for v in violations}
    assert {"fastapi", "postgresql"} <= tokens


def test_clean_model_passes_scan():
    assert scan_for_technology_coupling(_model()) == []


def test_data_model_round_trip():
    m = _model(
        data_models=[
            DataModelSpec(
                id="dm-1",
                name="Booking",
                owning_service_id="s-1",
                fields=[
                    FieldSpec(name="id", type=AbstractFieldType.IDENTIFIER),
                    FieldSpec(name="status", type=AbstractFieldType.ENUMERATION,
                              enumeration_values=["open", "closed"]),
                ],
            )
        ]
    )
    recovered = SystemModel.model_validate(m.model_dump(mode="json"))
    assert recovered.content_hash() == m.content_hash()



def test_typed_isr_hash_changes_when_system_model_payload_changes():
    from tiannara.domain.models.isr import IntermediateSoftwareRepresentation

    first_model = _model(
        capabilities=[
            BusinessCapability(
                id="cap-1", name="Workspace tenancy",
                traced_requirement_ids=["req-1"],
            )
        ]
    )
    second_model = _model(
        capabilities=[
            BusinessCapability(
                id="cap-1", name="Cross-workspace isolation",
                traced_requirement_ids=["req-1"],
            )
        ]
    )
    first = IntermediateSoftwareRepresentation.from_system_model(
        "taskflow", first_model, lineage=["source:fixed"]
    )
    second = IntermediateSoftwareRepresentation.from_system_model(
        "taskflow", second_model, lineage=["source:fixed"]
    )
    assert first.system_name == second.system_name
    assert first.content_hash() != second.content_hash()


def test_typed_isr_hash_is_stable_and_excludes_lineage():
    from tiannara.domain.models.isr import IntermediateSoftwareRepresentation

    model = _model()
    first = IntermediateSoftwareRepresentation.from_system_model(
        "taskflow", model, lineage=["source:first"]
    )
    second = IntermediateSoftwareRepresentation.from_system_model(
        "taskflow", model, lineage=["source:second"]
    )
    assert first.content_hash() == second.content_hash()
    assert first.system_model().content_hash() == model.content_hash()


def test_legacy_isr_hash_keeps_the_existing_envelope_algorithm():
    import hashlib
    from tiannara.domain.models.isr import IntermediateSoftwareRepresentation, IntentSpecification

    legacy = IntermediateSoftwareRepresentation(
        system_id="legacy-system",
        system_name="Legacy",
        intent=IntentSpecification(statement="Legacy intent", domain="test"),
        lineage=["lineage-does-not-hash"],
    )
    expected = hashlib.sha256(
        legacy.model_dump_json(exclude={"lineage"}).encode()
    ).hexdigest()
    assert legacy.content_hash() == expected
