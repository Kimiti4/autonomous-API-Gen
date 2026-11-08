"""Independent P0 closure evidence harness (CP067-R1 §20).

Does not self-certify: aggregates only independent oracle modules + bridge contracts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from certification.bridges.transformation_contracts import assert_trusted_bridge_allowed
from certification.isr_independent_verification.implir_ingress_oracle import (
    run_implir_ingress_oracle,
)
from certification.isr_independent_verification.plan_binding_oracle import (
    run_plan_binding_oracle,
)
from certification.isr_independent_verification.wave2_verification import _w05_passed
from certification.isr_independent_verification.b04_lowering_oracle import (
    run_b04_lowering_oracle,
)
from certification.isr_independent_verification.wave5_verification import (
    R5_MULTI_WORKLOAD_SLICE,
    run_wave5_independent_verification,
)
from certification.isr_independent_verification.canonicalization_oracle import (
    run_canonicalization_oracle,
)
from isr.core.canonicalization_inventory import inventory_complete, unsupported_family_ids
from isr.core.canonicalization_registry import registered_family_ids
from isr.core.digest_verification import (
    DigestPolicyViolation,
    assert_cross_domain_digest_substitution_forbidden,
    build_digest_envelope_for_revision,
)
class P0ClosureStage(str, Enum):
    OPEN = "OPEN"
    PARTIAL_INDEPENDENTLY_VERIFIED = "PARTIAL_INDEPENDENTLY_VERIFIED"
    CLOSED_INDEPENDENTLY_VERIFIED = "CLOSED_INDEPENDENTLY_VERIFIED"


@dataclass(frozen=True)
class P0ClosureRow:
    finding_id: str
    stage: P0ClosureStage
    independent_evidence: tuple[str, ...]
    blockers: tuple[str, ...]
    scope_note: str


INDEPENDENT_VERIFIER_P0 = "certification.isr_independent_verification.p0_closure_harness.v1"

def _evaluate_001() -> P0ClosureRow:
    blockers: list[str] = []
    evidence: list[str] = []
    for wid in R5_MULTI_WORKLOAD_SLICE:
        spec = __import__(
            "certification.orchestration.workload_registry",
            fromlist=["get_workload_spec"],
        ).get_workload_spec(wid)
        rep = run_plan_binding_oracle(spec.revision_fn())
        if rep.findings:
            blockers.append(f"oracle-f01:{wid}:{rep.findings}")
        else:
            evidence.append(f"f01-oracle:{wid}")
    try:
        from certification.payroll.candidate_fixture import payroll_isr_revision
        from constitutional_architecture.isr.versioning.digest_envelope import (
            build_constitutional_digest_envelope,
        )
        from constitutional_architecture.isr.model.isr import ISR
        from constitutional_architecture.isr.model.system import System

        cert = build_digest_envelope_for_revision(payroll_isr_revision())
        const = build_constitutional_digest_envelope(
            ISR(system=System(id="x", name="x", description=""))
        )
        try:
            assert_cross_domain_digest_substitution_forbidden(cert, const)
            blockers.append("cross-domain-should-raise")
        except DigestPolicyViolation:
            evidence.append("cross-domain-policy-fail-closed")
    except Exception as exc:
        blockers.append(f"cross-domain:{exc}")

    stage = (
        P0ClosureStage.CLOSED_INDEPENDENTLY_VERIFIED
        if not blockers
        else P0ClosureStage.PARTIAL_INDEPENDENTLY_VERIFIED
        if evidence
        else P0ClosureStage.OPEN
    )
    return P0ClosureRow(
        "CP067-ISR-001",
        stage,
        tuple(evidence),
        tuple(blockers),
        "Governed F-01 certification path; dual-domain policy; not universal ISR",
    )


def _evaluate_002() -> P0ClosureRow:
    blockers: list[str] = []
    evidence: list[str] = []
    try:
        c = assert_trusted_bridge_allowed("B-04")
        if c.lossiness.value != "LOSSY_EXPLICIT":
            blockers.append("b04-not-lossy-explicit")
        else:
            evidence.append("b04-contract-registered")
    except Exception as exc:
        blockers.append(str(exc))

    from certification.payroll.candidate_fixture import payroll_isr_revision
    from compiler.core.lowering import isr_to_plan
    from certification.orchestration.plan_binding_gate import assert_plan_binding_before_compile

    rev = payroll_isr_revision()
    plan = isr_to_plan(rev)
    assert_plan_binding_before_compile(rev, plan)
    evidence.append("plan-binding-gate-payroll")

    for wid in R5_MULTI_WORKLOAD_SLICE:
        spec = __import__(
            "certification.orchestration.workload_registry",
            fromlist=["get_workload_spec"],
        ).get_workload_spec(wid)
        b04 = run_b04_lowering_oracle(spec.revision_fn())
        if b04.passed:
            evidence.append(f"b04-obligation-oracle:{wid}")
        else:
            blockers.extend(b04.findings)

    scope = (
        "B-04 LOSSY + plan binding + obligation diff verifier; "
        "no inverse plan→ISR compile"
    )
    stage = (
        P0ClosureStage.CLOSED_INDEPENDENTLY_VERIFIED
        if not blockers
        else P0ClosureStage.PARTIAL_INDEPENDENTLY_VERIFIED
    )
    return P0ClosureRow(
        "CP067-ISR-002",
        stage,
        tuple(evidence),
        tuple(blockers),
        scope,
    )


def _evaluate_003_008() -> tuple[P0ClosureRow, P0ClosureRow]:
    w05 = run_implir_ingress_oracle()
    w5 = run_wave5_independent_verification()
    evidence: list[str] = []
    blockers: list[str] = []
    if _w05_passed(w05):
        evidence.append("implir-policy-oracle")
    else:
        blockers.extend(w05.findings)
    if w5.w05_policy_passed:
        evidence.append("wave5-policy")
    if not blockers:
        stage = P0ClosureStage.CLOSED_INDEPENDENTLY_VERIFIED
        scope = "Model C: trusted orchestration/publication blocked for ImplIR; F-01 path only"
    else:
        stage = P0ClosureStage.OPEN
        scope = "Ingress guard incomplete"
    row = P0ClosureRow(
        "CP067-ISR-003",
        stage,
        tuple(evidence),
        tuple(blockers),
        scope,
    )
    row8 = P0ClosureRow(
        "CP067-ISR-008",
        stage,
        tuple(evidence),
        tuple(blockers),
        "EngISR/ImplIR: trusted ingress blocked (Model C); heuristic path not trusted",
    )
    return row, row8


def _evaluate_004() -> P0ClosureRow:
    registered = set(registered_family_ids())
    evidence = [f"registered-contracts:{','.join(sorted(registered))}"]
    blockers: list[str] = []
    canon = run_canonicalization_oracle()
    if canon.passed:
        evidence.append("canonicalization-oracle-v1")
        evidence.append(f"inventory-registered:{canon.registered_count}")
        evidence.append(f"inventory-unsupported:{canon.unsupported_count}")
    else:
        blockers.extend(canon.findings)

    if inventory_complete():
        evidence.append("inventory-complete-17")
    else:
        blockers.append("inventory-incomplete")

    blockers.append("universal-canonicality-not-claimed")
    blockers.append(f"unsupported-families-explicit:{len(unsupported_family_ids())}")
    return P0ClosureRow(
        "CP067-ISR-004",
        P0ClosureStage.PARTIAL_INDEPENDENTLY_VERIFIED,
        tuple(evidence),
        tuple(blockers),
        f"CP067 F-01..F-17 inventory; {len(registered)} contracts; fail-closed gaps explicit",
    )


def run_p0_closure_harness() -> tuple[P0ClosureRow, ...]:
    r001 = _evaluate_001()
    r002 = _evaluate_002()
    r003, r008 = _evaluate_003_008()
    r004 = _evaluate_004()
    return (r001, r002, r003, r004, r008)


def _governance_ratification_fields() -> dict[str, object]:
    ratification = Path(
        "release/evidence/cp067_p0_closure_human_ratification_2026-11-08.json"
    )
    if not ratification.is_file():
        return {"governance_approval": False}
    payload = json.loads(ratification.read_text(encoding="utf-8"))
    if payload.get("status") != "RATIFIED":
        return {"governance_approval": False}
    return {
        "governance_approval": True,
        "governance_ratification_evidence": (
            "release/evidence/cp067_p0_closure_human_ratification_2026-11-08.json"
        ),
        "governance_ratification_timestamp": payload.get("approval_timestamp"),
    }


def write_p0_closure_evidence(path: Path, rows: tuple[P0ClosureRow, ...]) -> None:
    payload = {
        "schema": "tiannara.cp067.p0_closure_independent_proof",
        "verifier_id": INDEPENDENT_VERIFIER_P0,
        "cp068_admission": "CP068_CONDITIONAL_ISOLATED_TESTING_ONLY",
        **_governance_ratification_fields(),
        "findings": [
            {
                "finding_id": r.finding_id,
                "stage": r.stage.value,
                "scope_note": r.scope_note,
                "independent_evidence": list(r.independent_evidence),
                "blockers": list(r.blockers),
            }
            for r in rows
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
