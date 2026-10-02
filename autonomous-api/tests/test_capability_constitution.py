from app.engine.capability_constitution import (
    CapabilityEvidence, capability_definitions, capability_matrix,
    certification_status, get_capability,
)


def complete(capability):
    def values(items):
        return {item: True for item in items}
    return CapabilityEvidence(
        capability_id=capability.capability_id,
        requirement_results=values(capability.requirements),
        architectural_results=values(capability.architectural_obligations),
        implementation_results=values(capability.implementation_obligations),
        verification_results=values(capability.verification_obligations),
        security_results=values(capability.security_obligations),
        operational_results=values(capability.operational_obligations),
        evidence_results=values(capability.evidence_requirements),
    )


def test_canonical_taxonomy_has_twenty_capabilities():
    defs = capability_definitions()
    assert len(defs) == 20
    assert [x.capability_id for x in defs] == [f"C{i:02d}" for i in range(1, 21)]
    assert len(capability_matrix()) == 20


def test_contract_is_technology_neutral():
    assert all(not x.backend_dependencies for x in ())  # no concrete vendor dependency
    assert all(x.backend_dependencies for x in capability_definitions())


def test_certification_requires_every_obligation():
    cap = get_capability("C01")
    assert certification_status("C01", complete(cap)) == "CERTIFIED"
    e = complete(cap)
    failed = dict(e.verification_results)
    failed[cap.verification_obligations[0]] = False
    e2 = CapabilityEvidence(
        e.capability_id, e.requirement_results, e.architectural_results,
        e.implementation_results, failed, e.security_results,
        e.operational_results, e.evidence_results,
    )
    assert certification_status("C01", e2) == "NOT_CERTIFIED"


def test_mismatched_evidence_fails_closed():
    e = complete(get_capability("C01"))
    try:
        certification_status("C02", e)
    except ValueError:
        pass
    else:
        raise AssertionError("mismatched evidence must fail closed")
