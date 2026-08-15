"""
Tests for Phase 22.4 permissioned autonomy and policy enforcement.
"""

from datetime import timedelta

import pytest

from civilization.policy.engine import PolicyEngine
from civilization.policy.enforcement import (
    PolicyApprovalRequiredError,
    PolicyDeniedError,
    PolicyEnforcer,
)
from civilization.policy.models import (
    PermissionRule,
    PolicyEffect,
    PolicyEvaluationRequest,
    PolicyStatus,
)
from civilization.utils import utcnow


def build_engine_with_baseline_policy() -> PolicyEngine:
    engine = PolicyEngine()
    engine.bootstrap_default_policy()
    return engine


def test_read_action_allowed_by_baseline_policy():
    engine = build_engine_with_baseline_policy()

    request = PolicyEvaluationRequest(
        subject_type="AGENT",
        subject_id="agent_1",
        roles=["reviewer"],
        action="oversight.dashboard.read",
    )

    result = engine.evaluate(request)

    assert result.decision.value == "ALLOW"


def test_mutation_requires_approval_by_baseline_policy():
    engine = build_engine_with_baseline_policy()

    request = PolicyEvaluationRequest(
        subject_type="ORGANIZATION",
        subject_id="organization_1",
        action="civilization.task.create",
    )

    result = engine.evaluate(request)

    assert result.decision.value == "REQUIRE_APPROVAL"


def test_high_impact_action_requires_approval():
    engine = build_engine_with_baseline_policy()

    request = PolicyEvaluationRequest(
        subject_type="ORGANIZATION",
        subject_id="organization_1",
        action="evolution.candidate.promote",
    )

    result = engine.evaluate(request)

    assert result.decision.value == "REQUIRE_APPROVAL"


def test_kill_switch_blocks_non_read_actions():
    engine = build_engine_with_baseline_policy()

    request = PolicyEvaluationRequest(
        subject_type="ORGANIZATION",
        subject_id="organization_1",
        action="civilization.task.create",
        kill_switch_active=True,
    )

    result = engine.evaluate(request)

    assert result.decision.value == "DENY"


def test_kill_switch_allows_read_actions():
    engine = build_engine_with_baseline_policy()

    request = PolicyEvaluationRequest(
        subject_type="ORGANIZATION",
        subject_id="organization_1",
        action="oversight.dashboard.read",
        kill_switch_active=True,
    )

    result = engine.evaluate(request)

    assert result.decision.value == "ALLOW"


def test_deny_rule_overrides_allow_rule():
    engine = PolicyEngine()

    policy = engine.create_policy(
        name="Deny Override Policy",
        rules=[
            PermissionRule(
                name="Allow Task Create",
                effect=PolicyEffect.ALLOW,
                actions=["civilization.task.create"],
                subjects=["organization:organization_1"],
                priority=10,
            ),
            PermissionRule(
                name="Deny Task Create",
                effect=PolicyEffect.DENY,
                actions=["civilization.task.create"],
                subjects=["organization:organization_1"],
                priority=20,
            ),
        ],
    )

    engine.activate_policy(policy.id)

    request = PolicyEvaluationRequest(
        subject_type="ORGANIZATION",
        subject_id="organization_1",
        action="civilization.task.create",
    )

    result = engine.evaluate(request)

    assert result.decision.value == "DENY"


def test_delegation_allows_action_and_records_use():
    engine = build_engine_with_baseline_policy()
    enforcer = PolicyEnforcer(engine)

    expires_at = (utcnow() + timedelta(hours=1)).isoformat()

    delegation = engine.grant_delegation(
        grantor="human_operator",
        grantee="agent_1",
        actions=["civilization.task.create"],
        expires_at=expires_at,
        scope={
            "subject_type": "ORGANIZATION",
        },
        max_uses=1,
    )

    request = PolicyEvaluationRequest(
        subject_type="ORGANIZATION",
        subject_id="organization_1",
        action="civilization.task.create",
    )

    request.subject_id = "agent_1"

    result = enforcer.enforce(request)

    assert result.decision.value == "ALLOW"
    assert result.applied_delegation_id == delegation.id

    refreshed = engine.delegations[delegation.id]

    assert refreshed.use_count == 1


def test_expired_delegation_is_denied():
    engine = build_engine_with_baseline_policy()

    expired_time = (utcnow() - timedelta(hours=1)).isoformat()

    engine.grant_delegation(
        grantor="human_operator",
        grantee="agent_1",
        actions=["civilization.task.create"],
        expires_at=expired_time,
    )

    request = PolicyEvaluationRequest(
        subject_type="AGENT",
        subject_id="agent_1",
        action="civilization.task.create",
    )

    result = engine.evaluate(request)

    assert result.decision.value == "DENY"


def test_enforcer_raises_when_approval_required():
    engine = build_engine_with_baseline_policy()
    enforcer = PolicyEnforcer(engine)

    request = PolicyEvaluationRequest(
        subject_type="ORGANIZATION",
        subject_id="organization_1",
        action="civilization.task.create",
    )

    with pytest.raises(PolicyApprovalRequiredError):
        enforcer.enforce(request)


def test_enforcer_raises_when_denied():
    engine = build_engine_with_baseline_policy()
    enforcer = PolicyEnforcer(engine)

    request = PolicyEvaluationRequest(
        subject_type="ORGANIZATION",
        subject_id="organization_1",
        action="civilization.task.create",
        kill_switch_active=True,
    )

    with pytest.raises(PolicyDeniedError):
        enforcer.enforce(request)


def test_revoked_delegation_is_denied():
    engine = build_engine_with_baseline_policy()

    expires_at = (utcnow() + timedelta(hours=1)).isoformat()

    delegation = engine.grant_delegation(
        grantor="human_operator",
        grantee="agent_1",
        actions=["civilization.task.create"],
        expires_at=expires_at,
    )

    engine.revoke_delegation(delegation.id)

    request = PolicyEvaluationRequest(
        subject_type="AGENT",
        subject_id="agent_1",
        action="civilization.task.create",
    )

    result = engine.evaluate(request)

    assert result.decision.value == "DENY"


def test_max_uses_delegation_exhausted():
    engine = build_engine_with_baseline_policy()

    expires_at = (utcnow() + timedelta(hours=1)).isoformat()

    delegation = engine.grant_delegation(
        grantor="human_operator",
        grantee="agent_1",
        actions=["civilization.task.create"],
        expires_at=expires_at,
        max_uses=2,
    )

    request = PolicyEvaluationRequest(
        subject_type="AGENT",
        subject_id="agent_1",
        action="civilization.task.create",
    )

    result1 = engine.evaluate(request)
    assert result1.decision.value == "ALLOW"

    engine.record_delegation_use(delegation.id)
    engine.record_delegation_use(delegation.id)

    result2 = engine.evaluate(request)
    assert result2.decision.value == "DENY"


def test_no_match_results_in_deny():
    engine = PolicyEngine()

    policy = engine.create_policy(
        name="Restrictive Policy",
        rules=[
            PermissionRule(
                name="Allow Specific Agent",
                effect=PolicyEffect.ALLOW,
                actions=["civilization.task.create"],
                subjects=["agent:agent_1"],
                priority=10,
            ),
        ],
    )

    engine.activate_policy(policy.id)

    request = PolicyEvaluationRequest(
        subject_type="AGENT",
        subject_id="agent_2",
        action="civilization.task.create",
    )

    result = engine.evaluate(request)

    assert result.decision.value == "DENY"


def test_policy_simulation_with_inactive_policy():
    engine = PolicyEngine()

    policy = engine.create_policy(
        name="Simulation Policy",
        rules=[
            PermissionRule(
                name="Allow All Reads",
                effect=PolicyEffect.ALLOW,
                actions=["category:READ"],
                subjects=["*"],
                priority=10,
            ),
        ],
    )

    assert policy.status == PolicyStatus.DRAFT

    request = PolicyEvaluationRequest(
        subject_type="AGENT",
        subject_id="agent_1",
        action="oversight.dashboard.read",
    )

    result = engine.simulate(request, policy_id=policy.id)

    assert result.decision.value == "ALLOW"


def test_no_active_policy_denies():
    engine = PolicyEngine()

    request = PolicyEvaluationRequest(
        subject_type="AGENT",
        subject_id="agent_1",
        action="oversight.dashboard.read",
    )

    result = engine.evaluate(request)

    assert result.decision.value == "DENY"
    assert "No active" in result.reason


def test_action_wildcard_matching():
    engine = PolicyEngine()

    policy = engine.create_policy(
        name="Wildcard Policy",
        rules=[
            PermissionRule(
                name="Allow Civilization Tasks",
                effect=PolicyEffect.ALLOW,
                actions=["civilization.task.*"],
                subjects=["*"],
                priority=10,
            ),
        ],
    )

    engine.activate_policy(policy.id)

    request = PolicyEvaluationRequest(
        subject_type="ORGANIZATION",
        subject_id="org_1",
        action="civilization.task.create",
    )

    result = engine.evaluate(request)

    assert result.decision.value == "ALLOW"


def test_category_pattern_matching():
    engine = build_engine_with_baseline_policy()

    request = PolicyEvaluationRequest(
        subject_type="AGENT",
        subject_id="agent_1",
        action="reputation.certification.apply",
    )

    result = engine.evaluate(request)

    assert result.decision.value == "REQUIRE_APPROVAL"


def test_subject_role_matching():
    engine = PolicyEngine()

    policy = engine.create_policy(
        name="Role-Based Policy",
        rules=[
            PermissionRule(
                name="Allow for Architects",
                effect=PolicyEffect.ALLOW,
                actions=["civilization.task.run"],
                subjects=["role:software_architect"],
                priority=10,
            ),
        ],
    )

    engine.activate_policy(policy.id)

    request = PolicyEvaluationRequest(
        subject_type="AGENT",
        subject_id="agent_1",
        roles=["software_architect"],
        action="civilization.task.run",
    )

    result = engine.evaluate(request)

    assert result.decision.value == "ALLOW"


def test_condition_high_impact_filter():
    engine = PolicyEngine()

    policy = engine.create_policy(
        name="Conditional Policy",
        rules=[
            PermissionRule(
                name="Allow Low-Impact Reads",
                effect=PolicyEffect.ALLOW,
                actions=["category:READ"],
                subjects=["*"],
                condition={"high_impact": False},
                priority=10,
            ),
        ],
    )

    engine.activate_policy(policy.id)

    low_impact_request = PolicyEvaluationRequest(
        subject_type="AGENT",
        subject_id="agent_1",
        action="oversight.dashboard.read",
        high_impact=False,
    )

    result = engine.evaluate(low_impact_request)

    assert result.decision.value == "ALLOW"

    high_impact_request = PolicyEvaluationRequest(
        subject_type="AGENT",
        subject_id="agent_1",
        action="oversight.dashboard.read",
        high_impact=True,
    )

    result = engine.evaluate(high_impact_request)

    assert result.decision.value == "DENY"


def test_approval_refs_allow_high_impact_action():
    engine = build_engine_with_baseline_policy()

    request = PolicyEvaluationRequest(
        subject_type="ORGANIZATION",
        subject_id="organization_1",
        action="evolution.candidate.promote",
        approval_refs=["approval:governance_123"],
    )

    result = engine.evaluate(request)

    assert result.decision.value == "REQUIRE_APPROVAL"


def test_delegation_with_scope_filter():
    engine = build_engine_with_baseline_policy()

    expires_at = (utcnow() + timedelta(hours=1)).isoformat()

    engine.grant_delegation(
        grantor="human_operator",
        grantee="agent_1",
        actions=["civilization.task.create"],
        expires_at=expires_at,
        scope={
            "subject_type": "ORGANIZATION",
            "resource_type": "TASK",
        },
    )

    matching_request = PolicyEvaluationRequest(
        subject_type="ORGANIZATION",
        subject_id="agent_1",
        action="civilization.task.create",
        resource_type="TASK",
    )

    result = engine.evaluate(matching_request)

    assert result.decision.value == "ALLOW"

    non_matching_request = PolicyEvaluationRequest(
        subject_type="FEDERATION",
        subject_id="agent_1",
        action="civilization.task.create",
        resource_type="TASK",
    )

    result = engine.evaluate(non_matching_request)

    assert result.decision.value == "DENY"


def test_deactivate_retires_old_policy():
    engine = PolicyEngine()

    first_policy = engine.create_policy(
        name="First Policy",
        rules=[
            PermissionRule(
                name="Allow All",
                effect=PolicyEffect.ALLOW,
                actions=["*"],
                subjects=["*"],
                priority=10,
            ),
        ],
    )

    engine.activate_policy(first_policy.id)

    second_policy = engine.create_policy(
        name="Second Policy",
        rules=[
            PermissionRule(
                name="Deny All",
                effect=PolicyEffect.DENY,
                actions=["*"],
                subjects=["*"],
                priority=10,
            ),
        ],
    )

    engine.activate_policy(second_policy.id)

    assert first_policy.status == PolicyStatus.RETIRED

    request = PolicyEvaluationRequest(
        subject_type="AGENT",
        subject_id="agent_1",
        action="oversight.dashboard.read",
    )

    result = engine.evaluate(request)

    assert result.decision.value == "DENY"
