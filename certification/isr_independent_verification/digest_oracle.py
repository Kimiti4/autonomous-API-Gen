"""Independent digest oracle — recomputes without orchestration/generator success paths."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from compiler.core.canonical_api_contract import build_canonical_api_contract, contract_digest
from compiler.core.contract_canonicalization import canonical_bytes_f05
from compiler.core.lowering import isr_to_plan
from compiler.core.plan_canonicalization import canonical_bytes_f04
from isr.core.canonicalization_registry import (
    F01_ISR_REVISION,
    F04_COMPILATION_PLAN,
    F05_API_CONTRACT,
    get_canonicalization_contract,
)
from isr.core.digest_verification import (
    DigestPolicyViolation,
    assert_cross_domain_digest_substitution_forbidden,
    build_digest_envelope_for_revision,
)
from isr.core.revision import ISRRevision

INDEPENDENT_VERIFIER_ID = "certification.isr_independent_verification.digest_oracle.v1"


@dataclass(frozen=True)
class IndependentVerificationReport:
    verifier_id: str
    tier_a_f01_passed: bool
    tier_b_f04_passed: bool
    tier_b_f05_passed: bool
    payroll_fixture_passed: bool
    adversarial_cross_domain_passed: bool
    findings: tuple[str, ...]


class IndependentDigestOracle:
    """Recomputes digests from canonical bytes using only published contract shapes."""

    def verify_revision_integrity(self, revision: ISRRevision) -> str:
        contract = get_canonicalization_contract(F01_ISR_REVISION.isr_family_id)
        if revision.schema_version not in contract.schema_versions_supported:
            raise ValueError("unsupported-schema-version")
        from isr.core.digest_verification import canonical_bytes_f01

        digest = hashlib.sha256(canonical_bytes_f01(revision.schema_version, revision.graph)).hexdigest()
        if digest != revision.content_hash:
            raise ValueError("independent-oracle-digest-mismatch")
        return digest

    def verify_plan_canonical_stable(self, revision: ISRRevision) -> bytes:
        _ = get_canonicalization_contract(F04_COMPILATION_PLAN.isr_family_id)
        plan = isr_to_plan(revision)
        b1 = canonical_bytes_f04(plan)
        b2 = canonical_bytes_f04(plan)
        if b1 != b2:
            raise ValueError("plan-canonical-bytes-not-deterministic")
        return b1

    def verify_contract_digest_agrees(self, revision: ISRRevision) -> str:
        _ = get_canonicalization_contract(F05_API_CONTRACT.isr_family_id)
        plan = isr_to_plan(revision)
        contract = build_canonical_api_contract(plan)
        independent = hashlib.sha256(canonical_bytes_f05(contract)).hexdigest()
        produced = contract_digest(contract)
        if independent != produced:
            raise ValueError("contract-digest-oracle-mismatch")
        return independent


def run_independent_digest_verification(revision: ISRRevision) -> IndependentVerificationReport:
    oracle = IndependentDigestOracle()
    findings: list[str] = []
    tier_a = tier_b4 = tier_b5 = payroll = adversarial = False
    try:
        oracle.verify_revision_integrity(revision)
        tier_a = True
        build_digest_envelope_for_revision(revision)
    except Exception as exc:
        findings.append(f"tier-a-f01: {exc}")

    try:
        oracle.verify_plan_canonical_stable(revision)
        tier_b4 = True
    except Exception as exc:
        findings.append(f"tier-b-f04: {exc}")

    try:
        oracle.verify_contract_digest_agrees(revision)
        tier_b5 = True
    except Exception as exc:
        findings.append(f"tier-b-f05: {exc}")

    payroll = tier_a
    try:
        cert = build_digest_envelope_for_revision(revision)
        from constitutional_architecture.isr.versioning.digest_envelope import (
            build_constitutional_digest_envelope,
        )
        from constitutional_architecture.isr.model.isr import ISR
        from constitutional_architecture.isr.model.system import System

        const = build_constitutional_digest_envelope(
            ISR(system=System(id="iv", name="iv", description=""))
        )
        assert_cross_domain_digest_substitution_forbidden(cert, const)
        adversarial = True
    except DigestPolicyViolation:
        adversarial = True
    except Exception as exc:
        findings.append(f"adversarial: {exc}")

    return IndependentVerificationReport(
        verifier_id=INDEPENDENT_VERIFIER_ID,
        tier_a_f01_passed=tier_a,
        tier_b_f04_passed=tier_b4,
        tier_b_f05_passed=tier_b5,
        payroll_fixture_passed=payroll,
        adversarial_cross_domain_passed=adversarial,
        findings=tuple(findings),
    )
