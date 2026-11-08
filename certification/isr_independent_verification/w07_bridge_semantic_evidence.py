"""CP067 R1-W07 — ADR-R1-03 minimum bridge registry + semantic evidence slice."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from certification.bridges.lossiness_policy import trusted_promotion_allowed
from certification.bridges.transformation_contracts import (
    ADR_R1_03_MINIMUM_BRIDGE_IDS,
    LossinessClass,
    assert_trusted_bridge_allowed,
    get_bridge_contract,
)
from certification.isr_independent_verification.b04_lowering_oracle import (
    run_b04_lowering_oracle,
)
from certification.payroll.candidate_fixture import payroll_isr_revision
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.system import System
from constitutional_architecture.isr.versioning.digest_envelope import (
    build_constitutional_digest_envelope,
)
from isr.core.digest_verification import (
    DigestPolicyViolation,
    assert_cross_domain_digest_substitution_forbidden,
    build_digest_envelope_for_revision,
)

INDEPENDENT_VERIFIER_W07 = (
    "certification.isr_independent_verification.w07_bridge_semantic_evidence.v1"
)


@dataclass(frozen=True)
class W07BridgeSemanticEvidenceReport:
    verifier_id: str
    minimum_bridge_ids: tuple[str, ...]
    contracts_complete: bool
    b04_oracle_passed: bool
    b07_fail_closed_enforced: bool
    unsupported_bridges_untrusted: bool
    passed: bool
    findings: tuple[str, ...]


def _registry_complete(findings: list[str]) -> bool:
    ok = True
    for bridge_id in ADR_R1_03_MINIMUM_BRIDGE_IDS:
        try:
            contract = get_bridge_contract(bridge_id)
        except ValueError:
            findings.append(f"missing-contract:{bridge_id}")
            ok = False
            continue
        if not contract.verification_method:
            findings.append(f"missing-verification-method:{bridge_id}")
            ok = False
        if contract.failure_behavior != "FAIL_CLOSED":
            findings.append(f"unexpected-failure-behavior:{bridge_id}")
            ok = False
    return ok


def _unsupported_untrusted(findings: list[str]) -> bool:
    ok = True
    for bridge_id in ("B-07", "B-08", "B-09"):
        contract = get_bridge_contract(bridge_id)
        if contract.trusted_compile_allowed:
            findings.append(f"unsupported-marked-trusted:{bridge_id}")
            ok = False
        if bridge_id in ("B-07", "B-09"):
            if contract.lossiness is not LossinessClass.UNSUPPORTED_FAIL_CLOSED:
                findings.append(f"expected-unsupported-fail-closed:{bridge_id}")
                ok = False
        if not trusted_promotion_allowed(contract) and contract.trusted_compile_allowed:
            findings.append(f"promotion-policy-violation:{bridge_id}")
            ok = False
    return ok


def _verify_b07_cross_domain(findings: list[str]) -> bool:
    cert = build_digest_envelope_for_revision(payroll_isr_revision())
    const = build_constitutional_digest_envelope(
        ISR(system=System(id="x", name="x", description=""))
    )
    try:
        assert_cross_domain_digest_substitution_forbidden(cert, const)
        findings.append("b07-cross-domain-should-raise")
        return False
    except DigestPolicyViolation:
        return True


def _verify_b04_oracle(findings: list[str]) -> bool:
    rep = run_b04_lowering_oracle(payroll_isr_revision())
    if not rep.passed:
        findings.extend(f"b04-oracle:{f}" for f in rep.findings)
        return False
    try:
        assert_trusted_bridge_allowed("B-04")
    except ValueError as exc:
        findings.append(str(exc))
        return False
    return True


def run_w07_bridge_semantic_evidence() -> W07BridgeSemanticEvidenceReport:
    findings: list[str] = []
    contracts_ok = _registry_complete(findings)
    unsupported_ok = _unsupported_untrusted(findings)
    b07_ok = _verify_b07_cross_domain(findings)
    b04_ok = _verify_b04_oracle(findings)
    passed = contracts_ok and unsupported_ok and b07_ok and b04_ok
    return W07BridgeSemanticEvidenceReport(
        verifier_id=INDEPENDENT_VERIFIER_W07,
        minimum_bridge_ids=ADR_R1_03_MINIMUM_BRIDGE_IDS,
        contracts_complete=contracts_ok,
        b04_oracle_passed=b04_ok,
        b07_fail_closed_enforced=b07_ok,
        unsupported_bridges_untrusted=unsupported_ok,
        passed=passed,
        findings=tuple(findings),
    )


def write_w07_bridge_evidence(path: Path, report: W07BridgeSemanticEvidenceReport) -> None:
    contracts = {
        bid: {
            "lossiness": get_bridge_contract(bid).lossiness.value,
            "trusted_compile_allowed": get_bridge_contract(bid).trusted_compile_allowed,
            "verification_method": get_bridge_contract(bid).verification_method,
            "failure_behavior": get_bridge_contract(bid).failure_behavior,
        }
        for bid in report.minimum_bridge_ids
    }
    payload = {
        "schema": "tiannara.cp067.w07_bridge_semantic_evidence",
        "verifier_id": report.verifier_id,
        "adr_r1_03_minimum_set": list(report.minimum_bridge_ids),
        "contracts": contracts,
        "contracts_complete": report.contracts_complete,
        "b04_oracle_passed": report.b04_oracle_passed,
        "b07_fail_closed_enforced": report.b07_fail_closed_enforced,
        "unsupported_bridges_untrusted": report.unsupported_bridges_untrusted,
        "passed": report.passed,
        "findings": list(report.findings),
        "cp068_admission": "CP068_CONDITIONAL_ISOLATED_TESTING_ONLY",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
