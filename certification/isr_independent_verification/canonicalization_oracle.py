"""Independent CP067 F-01…F-17 inventory oracle (CP067-ISR-004)."""

from __future__ import annotations

from dataclasses import dataclass

from isr.core.canonicalization_inventory import (
    CP067_FAMILY_CANONICALIZATION_INVENTORY,
    assert_inventory_aligned_with_registry,
    inventory_complete,
    unsupported_family_ids,
)
from isr.core.canonicalization_registry import get_canonicalization_contract

INDEPENDENT_VERIFIER_CANON = (
    "certification.isr_independent_verification.canonicalization_oracle.v1"
)


@dataclass(frozen=True)
class CanonicalizationOracleReport:
    verifier_id: str
    passed: bool
    registered_count: int
    unsupported_count: int
    inventory_complete: bool
    findings: tuple[str, ...]


def run_canonicalization_oracle() -> CanonicalizationOracleReport:
    findings: list[str] = []
    if not inventory_complete():
        findings.append("inventory-not-17")
    try:
        assert_inventory_aligned_with_registry()
    except ValueError as exc:
        findings.append(str(exc))

    for entry in CP067_FAMILY_CANONICALIZATION_INVENTORY:
        if entry.status.value == "REGISTERED":
            try:
                get_canonicalization_contract(entry.isr_family_id)
            except ValueError:
                findings.append(f"missing-contract:{entry.isr_family_id}")

    for fid in unsupported_family_ids():
        try:
            get_canonicalization_contract(fid)
            findings.append(f"unsupported-should-not-register:{fid}")
        except ValueError:
            pass

    try:
        get_canonicalization_contract("nonexistent.family")
        findings.append("fail-closed-broken")
    except ValueError:
        pass

    registered = sum(
        1 for e in CP067_FAMILY_CANONICALIZATION_INVENTORY if e.status.value == "REGISTERED"
    )
    return CanonicalizationOracleReport(
        verifier_id=INDEPENDENT_VERIFIER_CANON,
        passed=not findings,
        registered_count=registered,
        unsupported_count=len(unsupported_family_ids()),
        inventory_complete=inventory_complete(),
        findings=tuple(findings),
    )
