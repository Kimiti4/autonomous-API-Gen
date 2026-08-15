"""
Backend certification engine.
"""

from __future__ import annotations

import logging
from typing import Optional

from ..errors import ISRValidationError
from ..models import ValidationIssue, ValidationReport, utcnow
from ..registry import BackendRegistry
from ..validation import validate_compilation_output, validate_isr_payload
from .models import (
    BackendCertificationReport,
    BackendCertificationRequest,
    CertificationEvent,
    CertificationStatus,
)
from .testing import (
    default_test_isr,
    run_backend_contract_tests,
    run_determinism_test,
)


class BackendCertificationEngine:
    """Certifies compiler backends."""

    def __init__(self, registry: BackendRegistry) -> None:
        self.registry = registry
        self.reports: dict[str, BackendCertificationReport] = {}
        self.events: list[CertificationEvent] = []
        self.logger = logging.getLogger("compiler.sdk.certification")

    def certify(
        self,
        request: BackendCertificationRequest,
    ) -> BackendCertificationReport:
        """Certify a backend."""

        manifest = self.registry.get_manifest(
            request.backend_id,
            request.backend_version,
        )

        backend = self.registry.get_backend(
            request.backend_id,
            request.backend_version,
        )

        test_isr = request.test_isr or default_test_isr()

        isr_report = validate_isr_payload(test_isr)

        if not isr_report.valid:
            raise ISRValidationError(
                "Certification test ISR is invalid.",
                isr_report,
            )

        contract_passed, contract_results, sample_output = (
            run_backend_contract_tests(
                backend,
                test_isr,
            )
        )

        determinism = run_determinism_test(
            backend,
            test_isr,
        )

        if sample_output is not None:
            output_report = validate_compilation_output(sample_output)
        else:
            output_report = ValidationReport(
                valid=False,
                issues=[
                    ValidationIssue(
                        severity="ERROR",
                        code="NO_SAMPLE_OUTPUT",
                        message="Backend produced no sample output.",
                    )
                ],
            )

        validation_passed = output_report.valid

        if contract_passed and determinism.passed and validation_passed:
            status = CertificationStatus.CERTIFIED
        else:
            status = CertificationStatus.FAILED

        report = BackendCertificationReport(
            backend_id=manifest.backend_id,
            backend_version=manifest.version,
            status=status,
            contract_tests=contract_results,
            contract_tests_passed=contract_passed,
            determinism=determinism,
            determinism_passed=determinism.passed,
            validation_passed=validation_passed,
            issues=output_report.issues,
            certified_at=utcnow().isoformat(),
        )

        key = self._key(manifest.backend_id, manifest.version)

        self.reports[key] = report

        if status == CertificationStatus.CERTIFIED:
            self._emit_event(
                "backend_certified",
                manifest.backend_id,
                manifest.version,
            )
        else:
            self._emit_event(
                "backend_certification_failed",
                manifest.backend_id,
                manifest.version,
            )

        return report

    def list_reports(self) -> list[BackendCertificationReport]:
        """List certification reports."""
        return list(self.reports.values())

    def get_report(
        self,
        backend_id: str,
        version: Optional[str] = None,
    ) -> Optional[BackendCertificationReport]:
        """Get a certification report."""

        key = self._resolve_report_key(backend_id, version)

        if not key:
            return None

        return self.reports.get(key)

    def revoke(
        self,
        backend_id: str,
        version: Optional[str] = None,
        reason: str = "",
    ) -> Optional[BackendCertificationReport]:
        """Revoke a certification."""

        key = self._resolve_report_key(backend_id, version)

        if not key:
            return None

        report = self.reports.get(key)

        if not report:
            return None

        report.status = CertificationStatus.REVOKED
        report.revoked_at = utcnow().isoformat()
        report.revocation_reason = reason

        self._emit_event(
            "backend_certification_revoked",
            report.backend_id,
            report.backend_version,
            {
                "reason": reason,
            },
        )

        return report

    def _key(self, backend_id: str, backend_version: str) -> str:
        return f"{backend_id}@{backend_version}"

    def _resolve_report_key(
        self,
        backend_id: str,
        version: Optional[str],
    ) -> Optional[str]:
        if version:
            key = self._key(backend_id, version)

            if key in self.reports:
                return key

            return None

        candidates = [
            key
            for key in self.reports
            if key.startswith(f"{backend_id}@")
        ]

        if not candidates:
            return None

        return sorted(candidates)[-1]

    def _emit_event(
        self,
        event_type: str,
        backend_id: str,
        backend_version: str,
        details: Optional[dict] = None,
    ) -> None:
        event = CertificationEvent(
            event_type=event_type,
            backend_id=backend_id,
            backend_version=backend_version,
            timestamp=utcnow().isoformat(),
            details=details or {},
        )

        self.events.append(event)
        self.logger.info(event.model_dump_json())