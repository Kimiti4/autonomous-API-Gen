"""Phase 28 - End-to-end integration: propose -> vote -> ratify -> report ->
dashboard; plus GovernedKernel delegate-contract preservation."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from constitutional_architecture.governance.audit import (
    AuditEvidenceRecorder,
    ComplianceReportLog,
)
from constitutional_architecture.governance.governance_dashboard import GovernanceDashboard
from constitutional_architecture.governance.exceptions import ExceptionRegistry
from constitutional_architecture.governance.integration import GovernedKernel
from constitutional_architecture.governance.schemas import (
    ChangeKind,
    ComplianceOutcome,
    ComplianceReportISR,
    VotingRuleKind,
    ApprovalStageISR,
    ApprovalWorkflowISR,
)
from constitutional_architecture.governance.versioning import (
    InMemoryConstitutionVersionRepository,
    VersionManager,
    VersioningError,
)
from constitutional_architecture.governance.voting import Ballot, VoteOutcome, VotingSystem

T0 = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)
T1 = T0 + timedelta(hours=1)
T2 = T0 + timedelta(hours=2)


def workflow(workflow_id: str) -> ApprovalWorkflowISR:
    return ApprovalWorkflowISR(
        workflow_id=workflow_id, purpose="ratification",
        stages=[ApprovalStageISR(stage_id="board", approvers=["a", "b", "c"],
                                 rule=VotingRuleKind.SIMPLE_MAJORITY)],
        quorum=2)


def vote(votes: dict[str, bool], stage_id: str = "board") -> list[Ballot]:
    return [Ballot(f"b-{v}", stage_id, v, approve, T0) for v, approve in votes.items()]


def test_end_to_end_constitutional_amendment():
    recorder = AuditEvidenceRecorder()
    versions = VersionManager(InMemoryConstitutionVersionRepository(), evidence=recorder)
    voting, exceptions, reports = VotingSystem(), ExceptionRegistry(), ComplianceReportLog()
    dashboard = GovernanceDashboard(versions, recorder, exceptions, reports)

    # Genesis: propose -> approve -> ratify.
    v1 = versions.propose(semver="1.0.0", policy_set_ref="ps-1", proposed_by="architect",
                          change_kind=ChangeKind.RESTATEMENT, summary="genesis", now=T0)
    approved = voting.conduct_vote(workflow("wf-1"),
                                   vote({"a": True, "b": True, "c": False}), T0)
    assert approved.approved
    versions.ratify(version_id=v1.version_id, outcome=approved, now=T1)

    # Compliance report references the latest evidence.
    reports.append(ComplianceReportISR(
        report_id="cr-1", policy_set_ref="ps-1", subject="marketplace",
        evaluated_at=T1, outcome=ComplianceOutcome.COMPLIANT,
        evidence_refs=[recorder.entries[-1].evidence_id]))

    view = dashboard.project(now=T1)
    assert view.current_version.version_id == v1.version_id
    assert view.current_version.ratification_workflow_ref == "wf-1"
    assert view.recent_reports[0].report_id == "cr-1"
    assert view.evidence_chain_intact

    # Denied amendment: ratification must fail and the head must not move.
    v2 = versions.propose(semver="1.1.0", policy_set_ref="ps-2", proposed_by="architect",
                          change_kind=ChangeKind.AMENDMENT, summary="expansion", now=T2)
    denied = voting.conduct_vote(workflow("wf-2"),
                                 vote({"a": True, "b": False, "c": False}), T2)
    assert not denied.approved
    with pytest.raises(VersioningError, match="approved_vote"):
        versions.ratify(version_id=v2.version_id, outcome=denied, now=T2)
    assert versions.current().version_id == v1.version_id
    assert len(versions.lineage()) == 1  # no lineage for the denied change


class StubKernel:
    def __init__(self):
        self.requests = []

    def evaluate(self, request):
        self.requests.append(request)
        return {"decision": "permit"}


def test_governed_kernel_preserves_delegate_contract():
    stub, recorder = StubKernel(), AuditEvidenceRecorder()
    governed = GovernedKernel(stub, evidence=recorder)
    request = SimpleNamespace(request_id="rq-1")

    assert governed.evaluate(request) == {"decision": "permit"}
    assert stub.requests == [request]
    assert len(recorder.entries) == 1
    assert recorder.entries[0].event_kind == "decision"
    assert recorder.verify_chain()


def test_amendment_authorization_is_fail_closed():
    stub, recorder = StubKernel(), AuditEvidenceRecorder()
    versions = VersionManager(InMemoryConstitutionVersionRepository())
    governed = GovernedKernel(stub, evidence=recorder, versions=versions)

    # No ratified head -> denied regardless of request content.
    assert not governed.amendment_authorized(
        SimpleNamespace(context={"ratified_version_ref": "anything"}))

    v1 = versions.propose(semver="1.0.0", policy_set_ref="ps-1", proposed_by="a",
                          change_kind=ChangeKind.RESTATEMENT, summary="s", now=T0)
    versions.ratify(version_id=v1.version_id,
                    outcome=VoteOutcome("wf-1", True, T0, "test"), now=T0)

    assert governed.amendment_authorized(
        SimpleNamespace(context={"ratified_version_ref": v1.version_id}))
    assert not governed.amendment_authorized(SimpleNamespace(context={}))
