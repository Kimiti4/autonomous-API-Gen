"""Independent B-04 lowering obligation oracle."""

from __future__ import annotations

from dataclasses import dataclass

from certification.bridges.b04_lowering_obligation_verifier import (
    verify_b04_lowering_for_revision,
)
from isr.core.revision import ISRRevision

INDEPENDENT_VERIFIER_B04 = (
    "certification.isr_independent_verification.b04_lowering_oracle.v1"
)


@dataclass(frozen=True)
class B04LoweringOracleReport:
    verifier_id: str
    passed: bool
    findings: tuple[str, ...]
    preserved_evidence: tuple[str, ...]


def run_b04_lowering_oracle(revision: ISRRevision) -> B04LoweringOracleReport:
    inner = verify_b04_lowering_for_revision(revision)
    return B04LoweringOracleReport(
        verifier_id=INDEPENDENT_VERIFIER_B04,
        passed=inner.passed,
        findings=inner.findings,
        preserved_evidence=inner.preserved_evidence,
    )
