"""Phase 28 - GovernanceDashboard projection verification."""

from datetime import datetime, timedelta, timezone

from constitutional_architecture.governance.audit import (
    AuditEvidenceRecorder,
    ComplianceReportLog,
)
from constitutional_architecture.governance.governance_dashboard import GovernanceDashboard
from constitutional_architecture.governance.exceptions import ExceptionRegistry
from constitutional_architecture.governance.schemas import (
    ChangeKind,
    ComplianceOutcome,
    ComplianceReportISR,
    ExceptionSeverity,
    GovernanceExceptionISR,
)
from constitutional_architecture.governance.versioning import (
    InMemoryConstitutionVersionRepository,
    VersionManager,
)
from constitutional_architecture.governance.voting import VoteOutcome

NOW = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)


def build_dashboard():
    recorder = AuditEvidenceRecorder()
    manager = VersionManager(InMemoryConstitutionVersionRepository(), evidence=recorder)
    exceptions = ExceptionRegistry()
    reports = ComplianceReportLog()
    dashboard = GovernanceDashboard(manager, recorder, exceptions, reports)

    v1 = manager.propose(semver="1.0.0", policy_set_ref="ps-1", proposed_by="architect",
                         change_kind=ChangeKind.RESTATEMENT, summary="genesis", now=NOW)
    manager.ratify(version_id=v1.version_id,
                   outcome=VoteOutcome("wf-1", True, NOW, "test"), now=NOW)

    exceptions.register(GovernanceExceptionISR(
        exception_id="ge-active", scope="svc:a", severity=ExceptionSeverity.MEDIUM,
        justification="j", granted_by="admin", granted_at=NOW,
        review_due=NOW + timedelta(days=30)))
    exceptions.register(GovernanceExceptionISR(
        exception_id="ge-expired", scope="svc:b", severity=ExceptionSeverity.LOW,
        justification="j", granted_by="admin", granted_at=NOW - timedelta(days=10),
        review_due=NOW, expires_at=NOW - timedelta(days=1)))

    reports.append(ComplianceReportISR(
        report_id="cr-1", policy_set_ref="ps-1", subject="marketplace",
        evaluated_at=NOW, outcome=ComplianceOutcome.COMPLIANT))
    return dashboard, manager


def test_projection_reflects_governance_state():
    dashboard, manager = build_dashboard()
    view = dashboard.project(now=NOW)
    assert view.current_version.version_id == manager.current().version_id
    assert len(view.version_history) == 1
    assert len(view.recent_reports) == 1
    assert view.recent_reports[0].report_id == "cr-1"
    assert view.evidence_chain_intact


def test_expired_exceptions_excluded_from_projection():
    dashboard, _ = build_dashboard()
    view = dashboard.project(now=NOW)
    assert [e.exception_id for e in view.open_exceptions] == ["ge-active"]


def test_projection_is_read_only_and_stable():
    dashboard, manager = build_dashboard()
    first = dashboard.project(now=NOW)
    second = dashboard.project(now=NOW)
    assert first.current_version == second.current_version
    assert len(manager.history()) == 1  # projection did not mutate state
