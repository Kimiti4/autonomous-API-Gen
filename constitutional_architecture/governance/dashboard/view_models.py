"""
Phase 28 — Governance Dashboard view models.

Presentation-layer dataclasses that decouple the UI from kernel payloads
(constitutional constraint 2.4: technology is replaceable). Redaction of
sensitive context keys happens here, once, for every view.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def redact(value: Any, redact_keys: tuple) -> Any:
    if isinstance(value, dict):
        return {
            k: ("[REDACTED]" if any(key in k.lower() for key in redact_keys) else redact(v, redact_keys))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v, redact_keys) for v in value]
    return value


@dataclass
class ConstitutionSummaryView:
    id: str
    name: str
    version: str
    status: str
    created_at: str
    created_by: str
    content_hash: str


@dataclass
class ConstitutionDetailView(ConstitutionSummaryView):
    policy_domains: List[str] = field(default_factory=list)
    invariants: List[dict] = field(default_factory=list)
    approval_requirements: List[dict] = field(default_factory=list)
    exception_policy: Optional[dict] = None
    parent_id: Optional[str] = None
    parent_version: Optional[str] = None
    effective_at: Optional[str] = None
    signature: Optional[str] = None


@dataclass
class PolicySetSummaryView:
    id: str
    name: str
    version: str
    status: str
    constitution_id: str
    created_at: str
    content_hash: str


@dataclass
class RuleView:
    id: str
    name: str
    effect: str
    priority: int
    subject_types: List[str]
    actions: List[str]
    conditions: List[dict]
    required_evidence: List[str]
    required_approvals: List[dict]
    constraints: List[dict]


@dataclass
class PolicySetDetailView(PolicySetSummaryView):
    rules: List[RuleView] = field(default_factory=list)


@dataclass
class EvaluationSummaryView:
    decision_id: str
    subject_type: str
    subject_id: str
    action: str
    actor_id: str
    decision: str
    reason: str
    environment: str
    created_at: str


@dataclass
class PolicyEvaluationView:
    policy_set_id: str
    policy_set_version: str
    rule_id: str
    rule_name: str
    outcome: str
    explanation: str


@dataclass
class EvidenceView:
    required: List[str]
    provided: List[str]
    missing: List[str]


@dataclass
class ApprovalView:
    approval_id: str
    status: str
    approver_id: str
    required: bool
    decision: Optional[str]
    decided_by: Optional[str]
    decided_at: Optional[str]
    comments: Optional[str]


@dataclass
class AuditEventView:
    event_id: str
    event_type: str
    actor_id: str
    subject_type: str
    subject_id: str
    action: str
    decision_id: Optional[str]
    timestamp: str
    event_hash: str
    previous_event_hash: str


@dataclass
class LineageLinkView:
    id: str
    parent_type: str
    parent_id: str
    child_type: str
    child_id: str
    change_type: str
    decision_ref: Optional[str]
    approval_refs: List[str]
    rollback_plan_ref: Optional[str]


@dataclass
class DecisionDossierView:
    decision_id: str
    request: dict
    decision: dict
    policy_evaluations: List[PolicyEvaluationView]
    evidence: EvidenceView
    approvals: List[ApprovalView]
    exceptions_applied: List[str]
    audit_events: List[AuditEventView]
    lineage: List[LineageLinkView]
    final_decision: Optional[str] = None


@dataclass
class HealthSummaryView:
    active_constitution: Optional[dict]
    active_policy_sets: List[dict]
    recent_evaluations: List[EvaluationSummaryView]
    recent_denials: int
    pending_approvals: int
    active_exceptions: int
    expiring_exceptions: int
    audit_chain_status: str
    audit_chain_events: int
    policy_error_count: int


@dataclass
class AuditIntegrityView:
    status: str
    verified_events: int
    first_invalid_event: Optional[dict]
    latest_event_hash: Optional[str]
    last_verified_at: str


@dataclass
class ApprovalSummaryView:
    id: str
    evaluation_id: str
    approver_id: str
    required: bool
    status: str
    created_at: str
    expires_at: Optional[str]
    subject: str
    action: str


@dataclass
class ApprovalDetailView(ApprovalSummaryView):
    decision_summary: Optional[dict]
    evidence: List[str]
    constraints: List[dict]
    comments: Optional[str]
    decided_at: Optional[str]
    decided_by: Optional[str]


@dataclass
class ExceptionSummaryView:
    id: str
    name: str
    status: str
    granted_by: str
    created_at: str
    expires_at: str
    use_count: int
    max_uses: Optional[int]


@dataclass
class ExceptionDetailView(ExceptionSummaryView):
    justification: str
    scope: dict
    audit_ref: str


@dataclass
class LineageTraceView:
    artifact_type: str
    artifact_id: str
    backward: List[LineageLinkView]
    forward: List[LineageLinkView]
    ancestors: List[LineageLinkView]
