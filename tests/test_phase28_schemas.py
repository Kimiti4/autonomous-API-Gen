"""Phase 28 - ISR governance schema validation and serialization."""

from datetime import datetime, timezone

import pytest

from constitutional_architecture.governance.schemas import (
    ApprovalStageISR,
    ApprovalWorkflowISR,
    AuditEvidenceISR,
    ChangeKind,
    ChangeLineageISR,
    ComplianceOutcome,
    ComplianceReportISR,
    ConstitutionVersionISR,
    ExceptionSeverity,
    GovernanceExceptionISR,
    PolicyEffect,
    PolicyRuleISR,
    PolicyViolationISR,
    VersionStatus,
    VotingRuleKind,
)

NOW = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)


def test_policy_rule_defaults_to_deny():
    """Fail-closed: an underspecified rule must never permit."""
    rule = PolicyRuleISR(rule_id="r1", subject="agent:*", action="deploy", resource="prod:*")
    assert rule.effect is PolicyEffect.DENY


def test_workflow_requires_positive_quorum():
    with pytest.raises(Exception):
        ApprovalWorkflowISR(workflow_id="w1", purpose="p", stages=[], quorum=0)


@pytest.mark.parametrize(
    ("model", "kwargs"),
    [
        (PolicyRuleISR, dict(rule_id="r1", subject="s", action="a", resource="r")),
        (ApprovalStageISR, dict(stage_id="st1")),
        (ApprovalWorkflowISR, dict(workflow_id="w1", purpose="p")),
        (PolicyViolationISR, dict(rule_ref="r1", subject="s", action="a", resource="r")),
        (ComplianceReportISR, dict(report_id="cr1", policy_set_ref="ps1", subject="s",
                                   evaluated_at=NOW, outcome=ComplianceOutcome.COMPLIANT)),
        (AuditEvidenceISR, dict(evidence_id="ev1", recorded_at=NOW, actor="a",
                                event_kind="decision", subject_ref="s", payload_hash="h")),
        (ChangeLineageISR, dict(lineage_id="cl1", change_kind=ChangeKind.AMENDMENT,
                                authorizing_workflow_ref="w1", summary="s", created_at=NOW)),
        (GovernanceExceptionISR, dict(exception_id="ge1", scope="svc:x",
                                      severity=ExceptionSeverity.HIGH, justification="j",
                                      granted_by="admin", granted_at=NOW, review_due=NOW)),
        (ConstitutionVersionISR, dict(version_id="cv1", semver="1.0.0",
                                      policy_set_ref="ps1", proposed_by="architect",
                                      proposed_at=NOW, status=VersionStatus.PROPOSED)),
    ],
)
def test_round_trip_serialization(model, kwargs):
    instance = model(**kwargs)
    assert model.model_validate(instance.model_dump()) == instance
