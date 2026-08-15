"""
Phase 28 — Constitutional Governance: normative data model.

Task 28.1 — Governance Kernel Schema and Evaluation Contract.

Every later platform phase (self-evolution, learning, autonomous
organizations, marketplaces, distributed evolution, product generation)
evaluates its significant actions against this contract before executing.

All hashes are canonical: sha256 over json.dumps(..., sort_keys=True),
matching the platform's existing provenance convention.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, default=str)


def content_hash(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode()).hexdigest()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    REQUIRE_EVIDENCE = "REQUIRE_EVIDENCE"
    ALLOW_WITH_CONSTRAINTS = "ALLOW_WITH_CONSTRAINTS"


class ConstitutionStatus(str, Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    REVOKED = "REVOKED"


class InvariantSeverity(str, Enum):
    BLOCKING = "BLOCKING"
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    ADVISORY = "ADVISORY"


class PolicySetStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    REVOKED = "REVOKED"


class RuleEffect(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    REQUIRE_EVIDENCE = "REQUIRE_EVIDENCE"
    ALLOW_WITH_CONSTRAINTS = "ALLOW_WITH_CONSTRAINTS"


class FailureMode(str, Enum):
    DENY = "DENY"
    ESCALATE = "ESCALATE"
    ALLOW_WITH_EXCEPTION = "ALLOW_WITH_EXCEPTION"


class ConditionOperator(str, Enum):
    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    IN = "IN"
    NOT_IN = "NOT_IN"
    EXISTS = "EXISTS"
    NOT_EXISTS = "NOT_EXISTS"
    GREATER_THAN = "GREATER_THAN"
    LESS_THAN = "LESS_THAN"
    MATCHES = "MATCHES"


class ApproverType(str, Enum):
    HUMAN = "HUMAN"
    ROLE = "ROLE"
    ORGANIZATION = "ORGANIZATION"
    AUTONOMOUS_AGENT = "AUTONOMOUS_AGENT"
    FEDERATION_COUNCIL = "FEDERATION_COUNCIL"


class TimeoutPolicy(str, Enum):
    DENY_ON_TIMEOUT = "DENY_ON_TIMEOUT"
    ESCALATE_ON_TIMEOUT = "ESCALATE_ON_TIMEOUT"
    ALLOW_ON_TIMEOUT = "ALLOW_ON_TIMEOUT"


class ActorType(str, Enum):
    HUMAN = "HUMAN"
    SERVICE = "SERVICE"
    AUTONOMOUS_AGENT = "AUTONOMOUS_AGENT"
    ORGANIZATION = "ORGANIZATION"
    PLUGIN = "PLUGIN"
    EXTERNAL_SYSTEM = "EXTERNAL_SYSTEM"


class EvaluationOutcome(str, Enum):
    MATCHED_ALLOW = "MATCHED_ALLOW"
    MATCHED_DENY = "MATCHED_DENY"
    MATCHED_REQUIRE_APPROVAL = "MATCHED_REQUIRE_APPROVAL"
    MATCHED_REQUIRE_EVIDENCE = "MATCHED_REQUIRE_EVIDENCE"
    NOT_MATCHED = "NOT_MATCHED"
    ERROR = "ERROR"


class ApprovalDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ABSTAINED = "ABSTAINED"
    EXPIRED = "EXPIRED"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ABSTAINED = "ABSTAINED"
    EXPIRED = "EXPIRED"


class ExceptionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class Invariant(BaseModel):
    id: str
    name: str
    description: str = ""
    severity: InvariantSeverity = InvariantSeverity.MAJOR
    enforceable: bool = True
    rule_ref: Optional[str] = None


class ApprovalRequirement(BaseModel):
    approver_type: ApproverType = ApproverType.HUMAN
    approver_id: Optional[str] = None
    required: bool = True
    timeout_policy: TimeoutPolicy = TimeoutPolicy.DENY_ON_TIMEOUT
    timeout_duration: Optional[str] = None  # ISO-8601 duration, e.g. "PT48H"


class ExceptionPolicy(BaseModel):
    allow_exceptions: bool = True
    max_duration: Optional[str] = "P30D"
    requires_justification: bool = True


class Condition(BaseModel):
    field: str  # dotted path: actor.actor_id, context.parent_hash, ...
    operator: ConditionOperator = ConditionOperator.EQUALS
    value: Any = None


class Constraint(BaseModel):
    name: str
    enforced: bool = True
    value: Any = None


class Actor(BaseModel):
    actor_type: ActorType = ActorType.HUMAN
    actor_id: str
    roles: List[str] = Field(default_factory=list)
    delegated_authority: List[str] = Field(default_factory=list)


class ConstitutionISR(BaseModel):
    id: str
    version: str = "0.1.0"
    name: str
    description: str = ""
    status: ConstitutionStatus = ConstitutionStatus.DRAFT
    parent_id: Optional[str] = None
    parent_version: Optional[str] = None
    invariants: List[Invariant] = Field(default_factory=list)
    policy_domains: List[str] = Field(default_factory=list)
    approval_requirements: List[ApprovalRequirement] = Field(default_factory=list)
    exception_policy: ExceptionPolicy = Field(default_factory=ExceptionPolicy)
    effective_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utcnow)
    created_by: str = "governance_kernel"
    content_hash: str = ""
    signature: Optional[str] = None

    def recompute_hash(self) -> str:
        payload = {
            "id": self.id,
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "parent_id": self.parent_id,
            "parent_version": self.parent_version,
            "invariants": [i.model_dump() for i in self.invariants],
            "policy_domains": self.policy_domains,
            "approval_requirements": [
                a.model_dump() for a in self.approval_requirements
            ],
            "exception_policy": self.exception_policy.model_dump(),
        }
        self.content_hash = content_hash(payload)
        return self.content_hash


class PolicyRule(BaseModel):
    id: str
    name: str
    description: str = ""
    effect: RuleEffect
    priority: int = 100
    subject_types: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)
    conditions: List[Condition] = Field(default_factory=list)
    required_evidence: List[str] = Field(default_factory=list)
    required_approvals: List[ApprovalRequirement] = Field(default_factory=list)
    constraints: List[Constraint] = Field(default_factory=list)
    failure_mode: FailureMode = FailureMode.DENY


class PolicySetISR(BaseModel):
    id: str
    version: str = "0.1.0"
    name: str
    constitution_id: str
    constitution_version: str
    status: PolicySetStatus = PolicySetStatus.DRAFT
    policy_rules: List[PolicyRule] = Field(default_factory=list)
    applies_to: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    created_by: str = "governance_kernel"
    content_hash: str = ""

    def recompute_hash(self) -> str:
        payload = {
            "id": self.id,
            "version": self.version,
            "name": self.name,
            "constitution_id": self.constitution_id,
            "constitution_version": self.constitution_version,
            "policy_rules": [r.model_dump() for r in self.policy_rules],
            "applies_to": self.applies_to,
        }
        self.content_hash = content_hash(payload)
        return self.content_hash


class GovernanceEvaluationRequest(BaseModel):
    subject_type: str
    subject_id: str
    action: str
    actor: Actor
    context: Dict[str, Any] = Field(default_factory=dict)
    evidence_refs: List[str] = Field(default_factory=list)
    requested_exceptions: List[str] = Field(default_factory=list)


class PolicyEvaluation(BaseModel):
    policy_set_id: str
    policy_set_version: str
    rule_id: str
    rule_name: str
    outcome: EvaluationOutcome
    explanation: str = ""


class GovernanceDecision(BaseModel):
    decision: Decision
    reason: str = ""
    evaluated_policies: List[PolicyEvaluation] = Field(default_factory=list)
    required_approvals: List[ApprovalRequirement] = Field(default_factory=list)
    required_evidence: List[str] = Field(default_factory=list)
    constraints: List[Constraint] = Field(default_factory=list)
    exceptions_applied: List[str] = Field(default_factory=list)
    decision_hash: str = ""
    created_at: datetime = Field(default_factory=utcnow)

    def recompute_hash(self) -> str:
        payload = self.model_dump(exclude={"decision_hash", "created_at"})
        self.decision_hash = content_hash(payload)
        return self.decision_hash


class ApprovalRecord(BaseModel):
    id: str
    evaluation_id: str
    requirement: ApprovalRequirement
    approver_type: str
    approver_id: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    decision: Optional[ApprovalDecision] = None
    comments: Optional[str] = None
    approved_constraints: List[Constraint] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    decided_at: Optional[datetime] = None
    signature: Optional[str] = None


class AuditEvent(BaseModel):
    id: str
    event_type: str
    actor: Actor
    subject_type: str
    subject_id: str
    action: str
    decision_id: Optional[str] = None
    approval_ids: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utcnow)
    previous_event_hash: str = ""
    event_hash: str = ""

    def recompute_hash(self, previous_event_hash: str) -> str:
        self.previous_event_hash = previous_event_hash
        payload = self.model_dump(exclude={"event_hash"})
        self.event_hash = content_hash(payload)
        return self.event_hash


class ChangeLineage(BaseModel):
    id: str
    parent_artifact_type: str
    parent_artifact_id: str
    parent_artifact_hash: str
    child_artifact_type: str
    child_artifact_id: str
    child_artifact_hash: str
    change_type: str
    cause_ref: Optional[str] = None
    decision_ref: Optional[str] = None
    approval_refs: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    rollback_plan_ref: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class ExceptionScope(BaseModel):
    subject_types: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)
    subject_ids: List[str] = Field(default_factory=list)
    actor_ids: List[str] = Field(default_factory=list)
    max_uses: Optional[int] = None
    environment: Optional[str] = None

    def covers(self, request: "GovernanceEvaluationRequest") -> bool:
        if self.subject_types and request.subject_type not in self.subject_types:
            return False
        if self.actions and request.action not in self.actions:
            return False
        if self.subject_ids and request.subject_id not in self.subject_ids:
            return False
        if self.actor_ids and request.actor.actor_id not in self.actor_ids:
            return False
        if self.environment and request.context.get("environment") != self.environment:
            return False
        return True


class GovernanceException(BaseModel):
    id: str
    name: str
    justification: str
    scope: ExceptionScope
    granted_by: str
    granted_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime
    status: ExceptionStatus = ExceptionStatus.ACTIVE
    constraints: List[Constraint] = Field(default_factory=list)
    audit_ref: str = ""
    use_count: int = 0


# ===========================================================================
# Phase 28 — Constitutional Governance ISR extensions (additive closure block)
#
# These schemas give governance artifacts canonical representation so that
# governance can be expressed, evolved, ratified, and audited entirely
# through the ISR. They are additive and do not alter the existing
# ConstitutionISR / PolicyRule / ChangeLineage / GovernanceException models.
# ===========================================================================


class PolicyEffect(str, Enum):
    PERMIT = "permit"
    DENY = "deny"


class VotingRuleKind(str, Enum):
    UNANIMITY = "unanimity"
    SIMPLE_MAJORITY = "simple_majority"
    WEIGHTED_MAJORITY = "weighted_majority"


class VersionStatus(str, Enum):
    PROPOSED = "proposed"
    RATIFIED = "ratified"
    SUPERSEDED = "superseded"
    RETIRED = "retired"


class ChangeKind(str, Enum):
    AMENDMENT = "amendment"
    EMERGENCY_PATCH = "emergency_patch"
    RESTATEMENT = "restatement"


class ExceptionSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceOutcome(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    INDETERMINATE = "indeterminate"


class PolicyRuleISR(BaseModel):
    """Atomic governance rule; the element type PolicySetISR composites.

    Fail-closed by design: the default effect is DENY, so an underspecified
    rule can never accidentally permit.
    """

    rule_id: str
    subject: str
    action: str
    resource: str
    effect: PolicyEffect = PolicyEffect.DENY
    condition: str | None = None
    priority: int = 0
    provenance: str | None = None


class ApprovalStageISR(BaseModel):
    """One decision stage of an approval workflow (e.g. security review,
    architecture board). Weights apply only under WEIGHTED_MAJORITY."""

    stage_id: str
    approvers: list[str] = Field(default_factory=list)
    rule: VotingRuleKind = VotingRuleKind.SIMPLE_MAJORITY
    weights: dict[str, float] = Field(default_factory=dict)


class ApprovalWorkflowISR(BaseModel):
    """Ratification workflow. All stages must pass, in declared order.
    Deadlines and quorum shortfalls fail closed."""

    workflow_id: str
    purpose: str
    stages: list[ApprovalStageISR] = Field(default_factory=list)
    quorum: int = Field(default=1, ge=1)
    deadline: datetime | None = None
    escalation_target: str | None = None


class PolicyViolationISR(BaseModel):
    rule_ref: str
    subject: str
    action: str
    resource: str
    detail: str | None = None


class ComplianceReportISR(BaseModel):
    """Outcome of evaluating a subject against a PolicySetISR."""

    report_id: str
    policy_set_ref: str
    subject: str
    evaluated_at: datetime
    outcome: ComplianceOutcome
    violations: list[PolicyViolationISR] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class AuditEvidenceISR(BaseModel):
    """Immutable, chain-linked evidence record (tamper-evident ledger node).

    `chain_link` references the preceding evidence_id; `payload_hash` is the
    SHA-256 of the canonicalized payload including the chain link.
    """

    evidence_id: str
    recorded_at: datetime
    actor: str
    event_kind: str
    subject_ref: str
    payload_hash: str
    chain_link: str | None = None
    signature: str | None = None
    signer_id: str | None = None


class ChangeLineageISR(BaseModel):
    """DAG node recording one governance-relevant change and the workflow
    that authorized it."""

    lineage_id: str
    change_kind: ChangeKind
    parent_version_refs: list[str] = Field(default_factory=list)
    authorizing_workflow_ref: str
    summary: str
    created_at: datetime


class GovernanceExceptionISR(BaseModel):
    """A recorded, time-boxed deviation from policy. Immutable once granted;
    revocation is tracked as a separate audit fact so the historical record
    is never rewritten."""

    exception_id: str
    scope: str
    severity: ExceptionSeverity
    justification: str
    granted_by: str
    granted_at: datetime
    review_due: datetime
    expires_at: datetime | None = None


class ConstitutionVersionISR(BaseModel):
    """A ratifiable snapshot of the constitution.

    Lifecycle: PROPOSED -> RATIFIED -> SUPERSEDED (or RETIRED). Ratification
    requires an approved ApprovalWorkflowISR outcome; lineage_ref points at
    the ChangeLineageISR emitted on ratification.
    """

    version_id: str
    semver: str
    status: VersionStatus = VersionStatus.PROPOSED
    policy_set_ref: str
    proposed_by: str
    proposed_at: datetime
    predecessor_ref: str | None = None
    ratification_workflow_ref: str | None = None
    lineage_ref: str | None = None
    effective_at: datetime | None = None


def normalize_policy_set(policy_set: "PolicySetISR") -> dict:
    """Project an existing PolicySetISR into the canonical rules envelope.

    Used by the compatibility adapter (Phase 28 assumption 2): when a
    PolicySetISR already carries inline `policy_rules` (as the legacy
    schema does), this exposes a normalized `rules: list[PolicyRuleISR]`
    view so downstream consumers see a single canonical shape.
    """

    normalized = [
        PolicyRuleISR(
            rule_id=rule.id,
            subject=(
                "|".join(rule.subject_types) if rule.subject_types else "*"
            ),
            action=(
                "|".join(rule.actions) if rule.actions else "*"
            ),
            resource="*",
            effect=(
                PolicyEffect.PERMIT
                if rule.effect is RuleEffect.ALLOW
                else PolicyEffect.DENY
            ),
            priority=rule.priority,
            provenance=rule.name,
        ).model_dump()
        for rule in policy_set.policy_rules
    ]

    return {
        "policy_set_ref": policy_set.id,
        "policy_version": policy_set.version,
        "rules": normalized,
    }


# ===========================================================================
# Option (a) - Governance Chromosome Family ISR (additive)
#
# GovernanceDesignISR is the expressed governance ARCHITECTURE of a candidate:
# a bag of governance decisions (not implementation). The evolution engine
# operates on this ISR; the governance chromosome family is the genome-side
# producer. Shares the objective vocabulary with option-(d) operational scoring
# so the GovernanceFitnessBridge dimension-set consistency is preserved.
# ===========================================================================


class VersioningStrategyKind(str, Enum):
    SEMVER_CHAIN = "semver_chain"            # append-only strictly-increasing semver
    DATE_BASED = "date_based"                # date-stamped snapshots
    MONOTONIC_COUNTER = "monotonic_counter"  # simple incrementing versions


class GovernanceDesignISR(BaseModel):
    """A candidate's expressed governance architecture.

    Each field is the expressed value of one governance gene and primarily
    drives one governance fitness objective (independent evolvability).
    """

    model_config = ConfigDict(extra="ignore")

    design_id: str

    # Amendment-process rigor  -> ratification_rigor
    voting_rule: VotingRuleKind
    quorum: int = Field(default=1, ge=1)
    approval_stage_count: int = Field(default=1, ge=1)

    # Policy posture            -> policy_coverage
    policy_rule_count: int = Field(default=0, ge=0)
    fail_closed_default: bool = True

    # Exception control         -> exception_hygiene
    exception_max_severity: ExceptionSeverity = ExceptionSeverity.HIGH
    exception_review_required: bool = True

    # Audit mandate             -> audit_integrity
    audit_chaining_required: bool = True

    # Compliance mandate        -> compliance_posture
    compliance_evaluation_required: bool = True

    # Constitutional lifecycle  -> constitutional_currency
    versioning_strategy: VersioningStrategyKind = VersioningStrategyKind.SEMVER_CHAIN

