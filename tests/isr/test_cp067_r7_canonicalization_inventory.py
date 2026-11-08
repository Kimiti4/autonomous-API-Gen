from __future__ import annotations

from certification.isr_independent_verification.canonicalization_oracle import (
    INDEPENDENT_VERIFIER_CANON,
    run_canonicalization_oracle,
)
from isr.core.canonicalization_inventory import (
    CP067_FAMILY_CANONICALIZATION_INVENTORY,
    CP067_FAMILY_COUNT,
    assert_inventory_aligned_with_registry,
    inventory_complete,
)
from isr.core.canonicalization_registry import F06_CONSTITUTIONAL_ISR, get_canonicalization_contract


def test_cp067_inventory_has_seventeen_families():
    assert inventory_complete()
    assert len(CP067_FAMILY_CANONICALIZATION_INVENTORY) == CP067_FAMILY_COUNT


def test_inventory_matches_canonicalization_registry():
    assert_inventory_aligned_with_registry()


def test_f06_constitutional_contract_registered():
    c = get_canonicalization_contract(F06_CONSTITUTIONAL_ISR.isr_family_id)
    assert c.authority_domain == "constitutional.isr"
    assert c.canonicalization_id == "constitutional.isr.serializer"


def test_canonicalization_oracle_passes():
    report = run_canonicalization_oracle()
    assert report.verifier_id == INDEPENDENT_VERIFIER_CANON
    assert report.passed
    assert report.registered_count == 5
    assert report.unsupported_count == 12
