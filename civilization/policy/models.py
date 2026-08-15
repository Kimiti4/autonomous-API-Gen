"""
Models for permissioned autonomy and policy enforcement.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PolicyEffect(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class PolicyStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class PolicyEvaluationDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class ActionDefinition(BaseModel):
    """Definition of a governed action."""

    action: str
    name: str

    description: str = ""

    category: str = "GOVERN"

    high_impact: bool = False
    governable: bool = True


class PermissionCondition(BaseModel):
    """Conditions under which a permission rule applies."""

    high_impact: Optional[bool] = None

    autonomy_levels: Optional[List[str]] = None

    subject_roles: Optional[List[str]] = None
    subject_types: Optional[List[str]] = None

    require_approval_refs: bool = False

    context_equals: Dict[str, Any] = Field(default_factory=dict)


class PermissionRule(BaseModel):
    """A permission rule inside a policy."""

    id: Optional[str] = None

    name: str

    effect: PolicyEffect

    actions: List[str] = Field(default_factory=list)

    subjects: List[str] = Field(default_factory=list)

    condition: Optional[PermissionCondition] = None

    priority: int = Field(default=100, ge=0, le=10_000)

    description: str = ""


class PermissionPolicy(BaseModel):
    """Versioned permission policy."""

    id: Optional[str] = None

    version: int = 1

    name: str

    status: PolicyStatus = PolicyStatus.DRAFT

    rules: List[PermissionRule] = Field(default_factory=list)

    created_at: str
    activated_at: Optional[str] = None


class DelegationGrant(BaseModel):
    """Time-bound delegation of authority."""

    id: Optional[str] = None

    grantor: str
    grantee: str

    actions: List[str] = Field(default_factory=list)

    scope: Dict[str, Any] = Field(default_factory=dict)

    expires_at: str

    max_uses: Optional[int] = Field(default=None, ge=1)

    use_count: int = 0

    revoked: bool = False

    created_at: str


class PolicyEvaluationRequest(BaseModel):
    """Request to evaluate whether an action is allowed."""

    subject_type: str
    subject_id: str

    roles: List[str] = Field(default_factory=list)

    action: str

    resource_type: Optional[str] = None
    resource_id: Optional[str] = None

    high_impact: bool = False

    autonomy_level: Optional[str] = None

    kill_switch_active: Optional[bool] = None

    approval_refs: List[str] = Field(default_factory=list)

    context: Dict[str, Any] = Field(default_factory=dict)


class PolicyEvaluationResult(BaseModel):
    """Result of policy evaluation."""

    decision: PolicyEvaluationDecision

    reason: str

    matched_rule_ids: List[str] = Field(default_factory=list)

    applied_delegation_id: Optional[str] = None

    required_approvals: List[str] = Field(default_factory=list)

    constraints: Dict[str, Any] = Field(default_factory=dict)

    evaluated_policy_id: Optional[str] = None
    evaluated_policy_version: Optional[int] = None

    timestamp: str
