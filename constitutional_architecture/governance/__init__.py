"""
Phase 28 — Constitutional Governance subsystem.

The constitutional control plane for the platform. Enforces:
  - every significant action is governed by explicit policy
  - every architectural change is versioned and attributable
  - every autonomous action operates within delegated authority
  - every promotion requires verification and approval
  - every change is auditable and reconstructable
  - every approved change has a rollback path
  - every policy violation blocks execution by default
  - every exception is explicit, bounded, time-limited, revocable
"""

from constitutional_architecture.governance.schemas import (
    Actor,
    ActorType,
    ApprovalDecision,
    ApprovalRecord,
    ApprovalRequirement,
    ApprovalStatus,
    AuditEvent,
    ChangeLineage,
    Condition,
    ConditionOperator,
    ConstitutionISR,
    ConstitutionStatus,
    Constraint,
    Decision,
    EvaluationOutcome,
    ExceptionPolicy,
    ExceptionScope,
    ExceptionStatus,
    FailureMode,
    GovernanceDecision,
    GovernanceEvaluationRequest,
    GovernanceException,
    Invariant,
    InvariantSeverity,
    PolicyEvaluation,
    PolicyRule,
    PolicySetISR,
    PolicySetStatus,
    RuleEffect,
    TimeoutPolicy,
    ApproverType,
    content_hash,
)
from constitutional_architecture.governance.kernel import GovernanceKernel
from constitutional_architecture.governance.default_policies import (
    ALL_POLICY_PACKS,
    POLICY_PACK_001_ISR_INTEGRITY,
    POLICY_PACK_002_REVERSIBILITY,
    POLICY_PACK_003_VERIFICATION,
    POLICY_PACK_004_AUTONOMOUS_AUTHORITY,
    POLICY_PACK_005_AUDITABILITY,
    POLICY_PACK_006_APPROVALS,
)

__all__ = [
    "Actor", "ActorType", "ApprovalDecision", "ApprovalRecord",
    "ApprovalRequirement", "ApprovalStatus", "AuditEvent", "ChangeLineage",
    "Condition", "ConditionOperator", "ConstitutionISR", "ConstitutionStatus",
    "Constraint", "Decision", "EvaluationOutcome", "ExceptionPolicy",
    "ExceptionScope", "ExceptionStatus", "FailureMode", "GovernanceDecision",
    "GovernanceEvaluationRequest", "GovernanceException", "Invariant",
    "InvariantSeverity", "PolicyEvaluation", "PolicyRule", "PolicySetISR",
    "PolicySetStatus", "RuleEffect", "TimeoutPolicy", "ApproverType",
    "content_hash",
    "GovernanceKernel",
    "ALL_POLICY_PACKS", "POLICY_PACK_001_ISR_INTEGRITY",
    "POLICY_PACK_002_REVERSIBILITY", "POLICY_PACK_003_VERIFICATION",
    "POLICY_PACK_004_AUTONOMOUS_AUTHORITY", "POLICY_PACK_005_AUDITABILITY",
    "POLICY_PACK_006_APPROVALS",
]
