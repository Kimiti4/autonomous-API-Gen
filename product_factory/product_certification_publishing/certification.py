"""
Product certification engine.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Callable, Dict, List, Optional

from .models import (
    CertificationGate,
    CertificationStatus,
    GateResult,
    ProductCertificationPolicy,
    ProductCertificationReport,
    utcnow,
)


GateFunction = Callable[
    [str, str, Dict],
    GateResult,
]


class CertificationGateways:
    """
    Certification gateways.

    Each gateway returns evidence for one certification gate.

    Replace these with real test, security, performance, documentation,
    observability, deployment, licensing, marketplace, and learning
    certification adapters.
    """

    def __init__(
        self,
        tests: Optional[GateFunction] = None,
        security: Optional[GateFunction] = None,
        performance: Optional[GateFunction] = None,
        documentation: Optional[GateFunction] = None,
        observability: Optional[GateFunction] = None,
        deployment: Optional[GateFunction] = None,
        rollback: Optional[GateFunction] = None,
        licensing: Optional[GateFunction] = None,
        marketplace_policy: Optional[GateFunction] = None,
        learning_certification: Optional[GateFunction] = None,
    ) -> None:
        self.tests = tests
        self.security = security
        self.performance = performance
        self.documentation = documentation
        self.observability = observability
        self.deployment = deployment
        self.rollback = rollback
        self.licensing = licensing
        self.marketplace_policy = marketplace_policy
        self.learning_certification = learning_certification


class ProductCertificationEngine:
    """Certifies product versions for publication."""

    def __init__(
        self,
        policy: ProductCertificationPolicy,
        gateways: CertificationGateways,
    ) -> None:
        self.policy = policy
        self.gateways = gateways

        self.reports: Dict[str, ProductCertificationReport] = {}

    def certify_product(
        self,
        product_id: str,
        product_version: str,
        evidence: Dict,
        certified_by: str = "system",
    ) -> ProductCertificationReport:
        gates: List[GateResult] = []

        gates.append(self._run_gate(CertificationGate.TESTS, product_id, product_version, evidence))
        gates.append(self._run_gate(CertificationGate.SECURITY, product_id, product_version, evidence))
        gates.append(self._run_gate(CertificationGate.PERFORMANCE, product_id, product_version, evidence))
        gates.append(self._run_gate(CertificationGate.DOCUMENTATION, product_id, product_version, evidence))
        gates.append(self._run_gate(CertificationGate.OBSERVABILITY, product_id, product_version, evidence))
        gates.append(self._run_gate(CertificationGate.DEPLOYMENT, product_id, product_version, evidence))
        gates.append(self._run_gate(CertificationGate.ROLLBACK, product_id, product_version, evidence))
        gates.append(self._run_gate(CertificationGate.LICENSING, product_id, product_version, evidence))
        gates.append(self._run_gate(CertificationGate.MARKETPLACE_POLICY, product_id, product_version, evidence))
        gates.append(self._run_gate(CertificationGate.LEARNING_CERTIFICATION, product_id, product_version, evidence))

        failures = [gate for gate in gates if not gate.passed]

        if failures:
            status = CertificationStatus.NOT_CERTIFIED
            reasons = [gate.reason for gate in failures if gate.reason]
        else:
            status = CertificationStatus.CERTIFIED
            reasons = []

        expires_at = utcnow() + timedelta(
            days=self.policy.certification_ttl_days
        )

        report = ProductCertificationReport(
            product_id=product_id,
            product_version=product_version,
            status=status,
            gates=gates,
            reasons=reasons,
            certified_by=certified_by,
            expires_at=expires_at,
        )

        self.reports[report.id] = report

        return report

    def revoke_certification(
        self,
        report_id: str,
        reason: str,
        revoked_by: str = "system",
    ) -> ProductCertificationReport:
        report = self.reports.get(report_id)

        if not report:
            raise KeyError(f"Certification report not found: {report_id}")

        report.status = CertificationStatus.REVOKED
        report.revoked_at = utcnow()
        report.revocation_reason = reason
        report.certified_by = revoked_by

        return report

    def _run_gate(
        self,
        gate: CertificationGate,
        product_id: str,
        product_version: str,
        evidence: Dict,
    ) -> GateResult:
        gateway = getattr(self.gateways, gate.value.lower(), None)

        if not gateway:
            return GateResult(
                gate=gate,
                passed=False,
                severity="HIGH",
                reason=f"No gateway configured for gate: {gate.value}",
            )

        result = gateway(product_id, product_version, evidence)

        if not isinstance(result, GateResult):
            raise TypeError(
                f"Gateway for gate {gate.value} must return GateResult."
            )

        return result
