"""Phase 28 - Governance dashboard: a strictly read-only projection over
governance state. Emits a technology-agnostic view model; any rendering is a
compiler-backend concern. The dashboard holds no write capability by design —
giving it one would create a second enforcement point and violate the
kernel's single-PDP principle.

NOTE: named `governance_dashboard` (not `dashboard`) to avoid shadowing the
existing `constitutional_architecture/governance/dashboard/` package.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .audit import ComplianceReportLog, EvidenceLedger
from .exceptions import ExceptionRegistry
from .schemas import (
    AuditEvidenceISR,
    ComplianceReportISR,
    ConstitutionVersionISR,
    GovernanceExceptionISR,
)
from .versioning import VersionManager


@dataclass(frozen=True)
class GovernanceView:
    generated_at: datetime
    current_version: ConstitutionVersionISR | None
    version_history: tuple[ConstitutionVersionISR, ...]
    recent_evidence: tuple[AuditEvidenceISR, ...]
    recent_reports: tuple[ComplianceReportISR, ...]
    open_exceptions: tuple[GovernanceExceptionISR, ...]
    evidence_chain_intact: bool
    evidence_signed: bool
    # None => ledger is unsigned (signature verification N/A); True/False when
    # the ledger is the signing wrapper.
    evidence_signatures_valid: bool | None


class GovernanceDashboard:
    """Read-only projector. `project()` never mutates source subsystems."""

    def __init__(
        self,
        versions: VersionManager,
        evidence: EvidenceLedger,
        exceptions: ExceptionRegistry,
        reports: ComplianceReportLog,
        window: int = 20,
    ) -> None:
        self._versions = versions
        self._evidence = evidence
        self._exceptions = exceptions
        self._reports = reports
        self._window = window

    def project(self, now: datetime) -> GovernanceView:
        entries = self._evidence.entries
        return GovernanceView(
            generated_at=now,
            current_version=self._versions.current(),
            version_history=self._versions.history(),
            recent_evidence=entries[-self._window:],
            recent_reports=self._reports.latest(self._window),
            open_exceptions=self._exceptions.active(now),
            evidence_chain_intact=self._evidence.verify_chain(),
            evidence_signed=any(e.signature is not None for e in entries),
            evidence_signatures_valid=self._evidence.verify_signatures(),
        )
