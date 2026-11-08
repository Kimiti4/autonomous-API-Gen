"""CP067-R10 / R1-W10 independent integration gate evidence aggregator."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from certification.isr_independent_verification.b04_lowering_oracle import (
    run_b04_lowering_oracle,
)
from certification.isr_independent_verification.canonicalization_oracle import (
    run_canonicalization_oracle,
)
from certification.isr_independent_verification.p0_closure_harness import (
    P0ClosureStage,
    run_p0_closure_harness,
)
from certification.isr_independent_verification.wave5_verification import (
    R5_MULTI_WORKLOAD_SLICE,
    run_wave5_independent_verification,
)
from certification.isr_independent_verification.wave6_http_verification import (
    run_wave6_http_ingress_verification,
)
from certification.isr_independent_verification.w07_bridge_semantic_evidence import (
    INDEPENDENT_VERIFIER_W07,
    run_w07_bridge_semantic_evidence,
)
from certification.isr_independent_verification.w09_implir_enforcement_expansion import (
    INDEPENDENT_VERIFIER_W09,
    run_w09_implir_enforcement_expansion,
)
from certification.isr_independent_verification.w03_revision_integrity_verification import (
    INDEPENDENT_VERIFIER_W03,
    run_w03_revision_integrity_verification,
)
from certification.isr_independent_verification.digest_oracle import (
    run_independent_digest_verification,
)
from certification.isr_independent_verification.plan_binding_oracle import (
    run_plan_binding_oracle,
)
from certification.isr_independent_verification.wave2_verification import _w04_passed
from certification.isr_independent_verification.implir_ingress_oracle import (
    run_implir_ingress_oracle,
)
from certification.isr_independent_verification.wave2_verification import _w05_passed
from certification.orchestration.ingress_trust_matrix import (
    EnforcementStatus,
    ingress_trust_matrix,
)
from certification.orchestration.workload_registry import get_workload_spec
from certification.payroll.candidate_fixture import payroll_isr_revision

INDEPENDENT_VERIFIER_W10_GATE = (
    "certification.isr_independent_verification.wave10_integration_gate.v1"
)

GOVERNANCE_EVIDENCE = (
    "release/evidence/cp067_p0_closure_human_ratification_2026-11-08.json",
    "release/evidence/cp067_isr002_supplement_ratification_2026-11-08.json",
    "release/evidence/cp067_isr004_supplement_ratification_2026-11-08.json",
)


class GateResult(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SLICE_ONLY = "SLICE_ONLY"


@dataclass(frozen=True)
class IntegrationGateRow:
    gate_id: str
    verifier_ref: str
    result: GateResult
    findings: tuple[str, ...]


@dataclass(frozen=True)
class Wave10IntegrationGateReport:
    verifier_id: str
    gates: tuple[IntegrationGateRow, ...]
    integration_gate_passed: bool
    cp068_admission: str
    governed_p0_all_closed_scoped: bool
    findings: tuple[str, ...]


def _governance_all_closed_scoped() -> tuple[bool, tuple[str, ...]]:
    findings: list[str] = []
    required = {
        "CP067-ISR-001",
        "CP067-ISR-002",
        "CP067-ISR-003",
        "CP067-ISR-004",
        "CP067-ISR-008",
    }
    closed: set[str] = set()
    for rel in GOVERNANCE_EVIDENCE:
        path = Path(rel)
        if not path.is_file():
            findings.append(f"missing-governance:{rel}")
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") != "RATIFIED":
            findings.append(f"not-ratified:{rel}")
            continue
        if "p0_register_decisions" in payload:
            for row in payload["p0_register_decisions"]:
                if row.get("governed_status_after_ratification") == "CLOSED_SCOPED":
                    closed.add(row["finding_id"])
        elif "finding_decision" in payload:
            fd = payload["finding_decision"]
            if fd.get("governed_status_after_supplement") == "CLOSED_SCOPED":
                closed.add(fd["finding_id"])
    missing = sorted(required - closed)
    if missing:
        findings.append(f"governance-not-closed:{','.join(missing)}")
    return len(missing) == 0, tuple(findings)


def run_wave10_integration_gate() -> Wave10IntegrationGateReport:
    findings: list[str] = []
    gates: list[IntegrationGateRow] = []

    digest = run_independent_digest_verification(payroll_isr_revision())
    digest_ok = (
        digest.tier_a_f01_passed
        and digest.tier_b_f04_passed
        and digest.tier_b_f05_passed
        and not digest.findings
    )
    gates.append(
        IntegrationGateRow(
            "W01-W02-F01-F05-DIGEST",
            "certification.isr_independent_verification.digest_oracle",
            GateResult.PASSED if digest_ok else GateResult.FAILED,
            digest.findings,
        )
    )

    for wid in R5_MULTI_WORKLOAD_SLICE:
        rev = get_workload_spec(wid).revision_fn()
        w04 = run_plan_binding_oracle(rev)
        w04_ok = _w04_passed(w04)
        gates.append(
            IntegrationGateRow(
                f"W04-PLAN-BINDING:{wid}",
                "certification.isr_independent_verification.plan_binding_oracle",
                GateResult.PASSED if w04_ok else GateResult.FAILED,
                w04.findings,
            )
        )
        b04 = run_b04_lowering_oracle(rev)
        gates.append(
            IntegrationGateRow(
                f"W06-B04-OBLIGATION:{wid}",
                "certification.isr_independent_verification.b04_lowering_oracle.v1",
                GateResult.PASSED if b04.passed else GateResult.FAILED,
                b04.findings,
            )
        )

    w05 = run_implir_ingress_oracle()
    w05_ok = _w05_passed(w05)
    gates.append(
        IntegrationGateRow(
            "W05-IMPLIR-POLICY",
            "certification.isr_independent_verification.implir_ingress_oracle",
            GateResult.PASSED if w05_ok else GateResult.FAILED,
            w05.findings,
        )
    )

    canon = run_canonicalization_oracle()
    gates.append(
        IntegrationGateRow(
            "W02-INVENTORY-F06",
            "certification.isr_independent_verification.canonicalization_oracle.v1",
            GateResult.PASSED if canon.passed else GateResult.FAILED,
            canon.findings,
        )
    )

    matrix = ingress_trust_matrix()
    impl = sum(1 for r in matrix if r.status is EnforcementStatus.IMPLEMENTED)
    w08_ok = len(matrix) >= 4 and impl >= 2
    gates.append(
        IntegrationGateRow(
            "W08-INGRESS-MATRIX",
            "certification.orchestration.ingress_trust_matrix",
            GateResult.PASSED if w08_ok else GateResult.SLICE_ONLY,
            () if w08_ok else (f"matrix-{len(matrix)}-impl-{impl}",),
        )
    )

    http = run_wave6_http_ingress_verification()
    gates.append(
        IntegrationGateRow(
            "W08-HTTP-ADVERSARIAL",
            http.verifier_id,
            GateResult.PASSED if http.passed else GateResult.FAILED,
            http.findings,
        )
    )

    w07 = run_w07_bridge_semantic_evidence()
    gates.append(
        IntegrationGateRow(
            "W07-ADR-R1-03-BRIDGE-EVIDENCE",
            INDEPENDENT_VERIFIER_W07,
            GateResult.PASSED if w07.passed else GateResult.FAILED,
            w07.findings,
        )
    )

    w09 = run_w09_implir_enforcement_expansion()
    gates.append(
        IntegrationGateRow(
            "W09-IMPLIR-ENFORCEMENT-EXPANSION",
            INDEPENDENT_VERIFIER_W09,
            GateResult.PASSED if w09.passed else GateResult.FAILED,
            w09.findings,
        )
    )

    w03 = run_w03_revision_integrity_verification()
    gates.append(
        IntegrationGateRow(
            "W03-REVISION-INTEGRITY-W08-SLICE",
            INDEPENDENT_VERIFIER_W03,
            GateResult.PASSED if w03.passed else GateResult.FAILED,
            w03.findings,
        )
    )

    w5 = run_wave5_independent_verification()
    gates.append(
        IntegrationGateRow(
            "W10-R5-SLICE",
            INDEPENDENT_VERIFIER_W10_GATE,
            GateResult.PASSED if w5.w10_integration_passed else GateResult.FAILED,
            w5.findings,
        )
    )

    p0_rows = run_p0_closure_harness()
    p0_by_id = {r.finding_id: r for r in p0_rows}
    iv_ok = all(
        p0_by_id[fid].stage
        in (P0ClosureStage.CLOSED_INDEPENDENTLY_VERIFIED, P0ClosureStage.PARTIAL_INDEPENDENTLY_VERIFIED)
        for fid in p0_by_id
    )
    gates.append(
        IntegrationGateRow(
            "P0-IV-HARNESS",
            "certification.isr_independent_verification.p0_closure_harness.v1",
            GateResult.PASSED if iv_ok else GateResult.FAILED,
            tuple(
                f"{r.finding_id}:{r.stage.value}"
                for r in p0_rows
                if r.stage is P0ClosureStage.OPEN
            ),
        )
    )

    gov_ok, gov_findings = _governance_all_closed_scoped()
    gates.append(
        IntegrationGateRow(
            "GOVERNANCE-P0-CLOSED-SCOPED",
            "release/evidence/cp067_*_ratification_*.json",
            GateResult.PASSED if gov_ok else GateResult.FAILED,
            gov_findings,
        )
    )

    critical_failed = any(
        g.result is GateResult.FAILED
        for g in gates
        if g.gate_id not in ("W08-INGRESS-MATRIX",)
    )
    integration_passed = not critical_failed and gov_ok

    if not integration_passed:
        for g in gates:
            if g.result is GateResult.FAILED:
                findings.append(f"gate-failed:{g.gate_id}")
            elif g.result is GateResult.SLICE_ONLY:
                findings.append(f"gate-slice:{g.gate_id}")

    return Wave10IntegrationGateReport(
        verifier_id=INDEPENDENT_VERIFIER_W10_GATE,
        gates=tuple(gates),
        integration_gate_passed=integration_passed,
        cp068_admission="CP068_CONDITIONAL_ISOLATED_TESTING_ONLY",
        governed_p0_all_closed_scoped=gov_ok,
        findings=tuple(findings),
    )


def write_wave10_integration_evidence(path: Path, report: Wave10IntegrationGateReport) -> None:
    payload = {
        "schema": "tiannara.cp067.w10_integration_gate",
        "verifier_id": report.verifier_id,
        "integration_gate_passed": report.integration_gate_passed,
        "governed_p0_all_closed_scoped": report.governed_p0_all_closed_scoped,
        "cp068_admission": report.cp068_admission,
        "workload_slice": list(R5_MULTI_WORKLOAD_SLICE),
        "gates": [
            {
                "gate_id": g.gate_id,
                "verifier_ref": g.verifier_ref,
                "result": g.result.value,
                "findings": list(g.findings),
            }
            for g in report.gates
        ],
        "findings": list(report.findings),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
