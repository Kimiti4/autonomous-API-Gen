"""CP067 R1-W09 — ImplIR / Model C enforcement across subordinate ingress surfaces."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from certification.isr_independent_verification.implir_ingress_oracle import (
    run_implir_ingress_oracle,
)
from certification.orchestration.implir_ingress_guard import (
    ImplirIngressBlocked,
    IsrIngressAuthority,
    W09_EXPANDED_BOUNDARIES,
    assert_trusted_evolution_ingress,
    assert_trusted_factory_ingress,
    assert_trusted_maintenance_ingress,
    assert_trusted_marketplace_ingress,
)
from certification.orchestration.ingress_revision_integrity_gate import W08_W03_BOUNDARY_IDS
from certification.orchestration.ingress_trust_matrix import ingress_trust_matrix

INDEPENDENT_VERIFIER_W09 = (
    "certification.isr_independent_verification.w09_implir_enforcement_expansion.v1"
)


@dataclass(frozen=True)
class W09ImplirEnforcementReport:
    verifier_id: str
    w05_oracle_passed: bool
    expanded_boundaries: tuple[str, ...]
    matrix_implir_tagged: bool
    maintenance_write_blocked_for_implir: bool
    marketplace_implir_blocked: bool
    evolution_lifecycle_blocked: bool
    factory_governed_blocked: bool
    passed: bool
    findings: tuple[str, ...]


def _w05_passed() -> tuple[bool, tuple[str, ...]]:
    rep = run_implir_ingress_oracle()
    ok = (
        rep.isr_revision_orchestration_ok
        and rep.implir_orchestration_blocked
        and rep.publication_implir_blocked
        and not rep.findings
    )
    return ok, rep.findings


def _matrix_has_implir() -> tuple[bool, tuple[str, ...]]:
    rows = ingress_trust_matrix()
    findings: list[str] = []
    for row in rows:
        if "implir_model_c" not in row.mandatory_checks:
            findings.append(f"matrix-missing-implir:{row.boundary_id}")
        if row.boundary_id in W08_W03_BOUNDARY_IDS:
            if "revision_integrity_w03" not in row.mandatory_checks:
                findings.append(f"matrix-missing-w03:{row.boundary_id}")
    return not findings, tuple(findings)


def run_w09_implir_enforcement_expansion() -> W09ImplirEnforcementReport:
    findings: list[str] = []

    w05_ok, w05_findings = _w05_passed()
    if not w05_ok:
        findings.extend(f"w05:{f}" for f in w05_findings)

    matrix_ok, matrix_findings = _matrix_has_implir()
    if not matrix_ok:
        findings.extend(matrix_findings)

    maintenance_blocked = False
    try:
        assert_trusted_maintenance_ingress(
            IsrIngressAuthority.IMPLEMENTATION_IR.value,
            governed_lineage_ref="isr.core.revision:test",
            production_write_requested=True,
        )
        findings.append("maintenance-implir-should-block")
    except ImplirIngressBlocked:
        maintenance_blocked = True

    marketplace_blocked = False
    try:
        assert_trusted_marketplace_ingress(
            IsrIngressAuthority.IMPLEMENTATION_IR.value,
            governed_lineage_ref="isr.core.revision:test",
        )
        findings.append("marketplace-implir-should-block")
    except ImplirIngressBlocked:
        marketplace_blocked = True

    evolution_blocked = False
    try:
        assert_trusted_evolution_ingress(
            claim_governed_product_lifecycle=True,
        )
        findings.append("evolution-lifecycle-should-block")
    except ImplirIngressBlocked:
        evolution_blocked = True

    factory_blocked = False
    try:
        assert_trusted_factory_ingress(governed_production=True)
        findings.append("factory-should-block")
    except ImplirIngressBlocked:
        factory_blocked = True

    passed = (
        w05_ok
        and matrix_ok
        and maintenance_blocked
        and marketplace_blocked
        and evolution_blocked
        and factory_blocked
    )
    return W09ImplirEnforcementReport(
        verifier_id=INDEPENDENT_VERIFIER_W09,
        w05_oracle_passed=w05_ok,
        expanded_boundaries=W09_EXPANDED_BOUNDARIES,
        matrix_implir_tagged=matrix_ok,
        maintenance_write_blocked_for_implir=maintenance_blocked,
        marketplace_implir_blocked=marketplace_blocked,
        evolution_lifecycle_blocked=evolution_blocked,
        factory_governed_blocked=factory_blocked,
        passed=passed,
        findings=tuple(findings),
    )


def write_w09_implir_evidence(path: Path, report: W09ImplirEnforcementReport) -> None:
    payload = {
        "schema": "tiannara.cp067.w09_implir_enforcement_expansion",
        "verifier_id": report.verifier_id,
        "expanded_boundaries": list(report.expanded_boundaries),
        "w05_oracle_passed": report.w05_oracle_passed,
        "matrix_implir_tagged": report.matrix_implir_tagged,
        "maintenance_write_blocked_for_implir": report.maintenance_write_blocked_for_implir,
        "marketplace_implir_blocked": report.marketplace_implir_blocked,
        "evolution_lifecycle_blocked": report.evolution_lifecycle_blocked,
        "factory_governed_blocked": report.factory_governed_blocked,
        "passed": report.passed,
        "findings": list(report.findings),
        "cp068_admission": "CP068_CONDITIONAL_ISOLATED_TESTING_ONLY",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
