"""
Policy decision engine for permissioned autonomy.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ..utils import deterministic_id, utcnow
from .models import (
    ActionDefinition,
    DelegationGrant,
    PermissionPolicy,
    PermissionRule,
    PolicyEffect,
    PolicyEvaluationDecision,
    PolicyEvaluationRequest,
    PolicyEvaluationResult,
    PolicyStatus,
)


class PolicyError(Exception):
    """Base error for policy operations."""


def default_action_catalog() -> List[ActionDefinition]:
    """Return the default governed action catalog."""

    return [
        ActionDefinition(
            action="civilization.organization.create",
            name="Create Organization",
            category="GOVERN",
            high_impact=False,
        ),
        ActionDefinition(
            action="civilization.organization.suspend",
            name="Suspend Organization",
            category="GOVERN",
            high_impact=True,
        ),
        ActionDefinition(
            action="civilization.organization.resume",
            name="Resume Organization",
            category="GOVERN",
            high_impact=True,
        ),
        ActionDefinition(
            action="civilization.agent.create",
            name="Create Agent",
            category="GOVERN",
            high_impact=False,
        ),
        ActionDefinition(
            action="civilization.task.create",
            name="Create Task",
            category="MUTATE",
            high_impact=False,
        ),
        ActionDefinition(
            action="civilization.task.run",
            name="Run Task",
            category="MUTATE",
            high_impact=False,
        ),
        ActionDefinition(
            action="civilization.task.finalize",
            name="Finalize Task",
            category="MUTATE",
            high_impact=False,
        ),
        ActionDefinition(
            action="federation.initiative.create",
            name="Create Federation Initiative",
            category="GOVERN",
            high_impact=False,
        ),
        ActionDefinition(
            action="federation.initiative.authorize",
            name="Authorize Federation Initiative",
            category="GOVERN",
            high_impact=True,
        ),
        ActionDefinition(
            action="federation.initiative.delegate",
            name="Delegate Federation Initiative Tasks",
            category="MUTATE",
            high_impact=False,
        ),
        ActionDefinition(
            action="federation.decision.vote",
            name="Cast Federation Council Vote",
            category="GOVERN",
            high_impact=False,
        ),
        ActionDefinition(
            action="reputation.certification.apply",
            name="Apply For Certification",
            category="GOVERN",
            high_impact=False,
        ),
        ActionDefinition(
            action="evolution.candidate.generate",
            name="Generate Evolution Candidate",
            category="MUTATE",
            high_impact=False,
        ),
        ActionDefinition(
            action="evolution.candidate.promote",
            name="Promote Evolution Candidate",
            category="PROMOTE",
            high_impact=True,
        ),
        ActionDefinition(
            action="deployment.deploy",
            name="Deploy System",
            category="DEPLOY",
            high_impact=True,
        ),
        ActionDefinition(
            action="oversight.dashboard.read",
            name="Read Oversight Dashboard",
            category="READ",
            high_impact=False,
        ),
        ActionDefinition(
            action="oversight.kill_switch.activate",
            name="Activate Kill Switch",
            category="GOVERN",
            high_impact=True,
        ),
    ]


class PolicyStore:
    """Versioned policy store."""

    def __init__(self) -> None:
        self.policies: Dict[str, PermissionPolicy] = {}
        self.active_policy_id: Optional[str] = None

    def create_policy(
        self,
        name: str,
        rules: List[PermissionRule],
    ) -> PermissionPolicy:
        created_at = utcnow().isoformat()

        version = len(self.policies) + 1

        policy_id = deterministic_id(
            "permission_policy",
            {
                "name": name,
                "version": version,
                "created_at": created_at,
            },
        )

        normalized_rules: List[PermissionRule] = []

        for index, rule in enumerate(rules):
            if not rule.id:
                rule.id = deterministic_id(
                    "permission_rule",
                    {
                        "policy_id": policy_id,
                        "rule_name": rule.name,
                        "index": index,
                    },
                )

            normalized_rules.append(rule)

        policy = PermissionPolicy(
            id=policy_id,
            version=version,
            name=name,
            status=PolicyStatus.DRAFT,
            rules=normalized_rules,
            created_at=created_at,
        )

        self.policies[policy_id] = policy

        return policy

    def activate_policy(self, policy_id: str) -> PermissionPolicy:
        policy = self.policies.get(policy_id)

        if not policy:
            raise PolicyError(f"Policy not found: {policy_id}")

        if self.active_policy_id:
            current = self.policies.get(self.active_policy_id)

            if current:
                current.status = PolicyStatus.RETIRED

        policy.status = PolicyStatus.ACTIVE
        policy.activated_at = utcnow().isoformat()

        self.active_policy_id = policy_id

        return policy

    def get_policy(self, policy_id: str) -> PermissionPolicy:
        policy = self.policies.get(policy_id)

        if not policy:
            raise PolicyError(f"Policy not found: {policy_id}")

        return policy

    def get_active_policy(self) -> Optional[PermissionPolicy]:
        if not self.active_policy_id:
            return None

        return self.policies.get(self.active_policy_id)


class PolicyEngine:
    """Policy decision point for permissioned autonomy."""

    def __init__(
        self,
        action_catalog: Optional[List[ActionDefinition]] = None,
        oversight_engine=None,
    ) -> None:
        catalog = action_catalog or default_action_catalog()

        self.action_catalog: Dict[str, ActionDefinition] = {
            action.action: action
            for action in catalog
        }

        self.store = PolicyStore()

        self.delegations: Dict[str, DelegationGrant] = {}

        self.oversight = oversight_engine

    # ------------------------------------------------------------------
    # Policy administration
    # ------------------------------------------------------------------

    def create_policy(
        self,
        name: str,
        rules: List[PermissionRule],
    ) -> PermissionPolicy:
        return self.store.create_policy(name=name, rules=rules)

    def activate_policy(self, policy_id: str) -> PermissionPolicy:
        return self.store.activate_policy(policy_id)

    def get_active_policy(self) -> Optional[PermissionPolicy]:
        return self.store.get_active_policy()

    def bootstrap_default_policy(self) -> PermissionPolicy:
        """Create and activate a least-privilege baseline policy."""

        active = self.store.get_active_policy()

        if active:
            return active

        rules = [
            PermissionRule(
                name="Allow Read Actions",
                effect=PolicyEffect.ALLOW,
                actions=["category:READ"],
                subjects=["*"],
                priority=10,
                description="Read actions are generally safe.",
            ),
            PermissionRule(
                name="Allow Recommend Actions",
                effect=PolicyEffect.ALLOW,
                actions=["category:RECOMMEND"],
                subjects=["*"],
                priority=20,
                description="Recommendations are evidence-producing actions.",
            ),
            PermissionRule(
                name="Require Approval For Mutations",
                effect=PolicyEffect.REQUIRE_APPROVAL,
                actions=["category:MUTATE"],
                subjects=["*"],
                priority=30,
                description="Mutating actions require approval by default.",
            ),
            PermissionRule(
                name="Require Approval For Governance Actions",
                effect=PolicyEffect.REQUIRE_APPROVAL,
                actions=["category:GOVERN"],
                subjects=["*"],
                priority=40,
                description="Governance actions require approval by default.",
            ),
            PermissionRule(
                name="Require Approval For Promotions",
                effect=PolicyEffect.REQUIRE_APPROVAL,
                actions=["category:PROMOTE"],
                subjects=["*"],
                priority=50,
                description="Promotion actions require approval.",
            ),
            PermissionRule(
                name="Require Approval For Deployments",
                effect=PolicyEffect.REQUIRE_APPROVAL,
                actions=["category:DEPLOY"],
                subjects=["*"],
                priority=60,
                description="Deployment actions require approval.",
            ),
        ]

        policy = self.store.create_policy(
            name="Baseline Permissioned Autonomy Policy",
            rules=rules,
        )

        return self.store.activate_policy(policy.id)

    # ------------------------------------------------------------------
    # Delegations
    # ------------------------------------------------------------------

    def grant_delegation(
        self,
        grantor: str,
        grantee: str,
        actions: List[str],
        expires_at: str,
        scope: Optional[Dict] = None,
        max_uses: Optional[int] = None,
    ) -> DelegationGrant:
        created_at = utcnow().isoformat()

        delegation_id = deterministic_id(
            "delegation_grant",
            {
                "grantor": grantor,
                "grantee": grantee,
                "actions": actions,
                "expires_at": expires_at,
                "created_at": created_at,
                "delegation_count": len(self.delegations),
            },
        )

        delegation = DelegationGrant(
            id=delegation_id,
            grantor=grantor,
            grantee=grantee,
            actions=actions,
            scope=scope or {},
            expires_at=expires_at,
            max_uses=max_uses,
            created_at=created_at,
        )

        self.delegations[delegation_id] = delegation

        return delegation

    def revoke_delegation(self, delegation_id: str) -> DelegationGrant:
        delegation = self.delegations.get(delegation_id)

        if not delegation:
            raise PolicyError(f"Delegation not found: {delegation_id}")

        delegation.revoked = True

        return delegation

    def record_delegation_use(self, delegation_id: str) -> DelegationGrant:
        delegation = self.delegations.get(delegation_id)

        if not delegation:
            raise PolicyError(f"Delegation not found: {delegation_id}")

        delegation.use_count += 1

        return delegation

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        request: PolicyEvaluationRequest,
        policy: Optional[PermissionPolicy] = None,
    ) -> PolicyEvaluationResult:
        evaluated_policy = policy or self.store.get_active_policy()

        timestamp = utcnow().isoformat()

        if not evaluated_policy:
            return PolicyEvaluationResult(
                decision=PolicyEvaluationDecision.DENY,
                reason="No active permission policy.",
                timestamp=timestamp,
            )

        action_definition = self.action_catalog.get(request.action)

        action_category = (
            action_definition.category
            if action_definition
            else "GOVERN"
        )

        high_impact = request.high_impact

        if not high_impact and action_definition:
            high_impact = action_definition.high_impact

        kill_switch_active = request.kill_switch_active

        if kill_switch_active is None:
            kill_switch_active = False

            if self.oversight and hasattr(self.oversight, "kill_switch"):
                kill_switch_active = bool(self.oversight.kill_switch.enabled)

        if kill_switch_active and action_category != "READ":
            return PolicyEvaluationResult(
                decision=PolicyEvaluationDecision.DENY,
                reason="Kill switch is active. Non-read actions are blocked.",
                evaluated_policy_id=evaluated_policy.id,
                evaluated_policy_version=evaluated_policy.version,
                timestamp=timestamp,
            )

        matched_rule_ids: List[str] = []

        allow_matched = False
        require_approval_matched = False

        rules = sorted(
            evaluated_policy.rules,
            key=lambda rule: rule.priority,
        )

        for rule in rules:
            if not self._rule_matches(rule, request, action_definition):
                continue

            if rule.id:
                matched_rule_ids.append(rule.id)

            if rule.effect == PolicyEffect.DENY:
                return PolicyEvaluationResult(
                    decision=PolicyEvaluationDecision.DENY,
                    reason=f"Denied by policy rule: {rule.name}",
                    matched_rule_ids=matched_rule_ids,
                    evaluated_policy_id=evaluated_policy.id,
                    evaluated_policy_version=evaluated_policy.version,
                    timestamp=timestamp,
                )

            if rule.effect == PolicyEffect.REQUIRE_APPROVAL:
                if request.approval_refs:
                    allow_matched = True
                else:
                    require_approval_matched = True

            if rule.effect == PolicyEffect.ALLOW:
                allow_matched = True

        delegation, is_active = self._find_delegation_with_status(request)

        if delegation:
            if is_active:
                return PolicyEvaluationResult(
                    decision=PolicyEvaluationDecision.ALLOW,
                    reason="Allowed by active delegation.",
                    applied_delegation_id=delegation.id,
                    evaluated_policy_id=evaluated_policy.id,
                    evaluated_policy_version=evaluated_policy.version,
                    timestamp=timestamp,
                )

            return PolicyEvaluationResult(
                decision=PolicyEvaluationDecision.DENY,
                reason="Delegation exists but is not active.",
                matched_rule_ids=matched_rule_ids,
                evaluated_policy_id=evaluated_policy.id,
                evaluated_policy_version=evaluated_policy.version,
                timestamp=timestamp,
            )

        if high_impact and (allow_matched or require_approval_matched):
            return PolicyEvaluationResult(
                decision=PolicyEvaluationDecision.REQUIRE_APPROVAL,
                reason="High-impact action requires approval evidence.",
                matched_rule_ids=matched_rule_ids,
                required_approvals=["high_impact_approval"],
                evaluated_policy_id=evaluated_policy.id,
                evaluated_policy_version=evaluated_policy.version,
                timestamp=timestamp,
            )

        if require_approval_matched:
            return PolicyEvaluationResult(
                decision=PolicyEvaluationDecision.REQUIRE_APPROVAL,
                reason="Policy requires approval for this action.",
                matched_rule_ids=matched_rule_ids,
                required_approvals=["policy_approval"],
                evaluated_policy_id=evaluated_policy.id,
                evaluated_policy_version=evaluated_policy.version,
                timestamp=timestamp,
            )

        if allow_matched:
            return PolicyEvaluationResult(
                decision=PolicyEvaluationDecision.ALLOW,
                reason="Allowed by policy.",
                matched_rule_ids=matched_rule_ids,
                evaluated_policy_id=evaluated_policy.id,
                evaluated_policy_version=evaluated_policy.version,
                timestamp=timestamp,
            )

        return PolicyEvaluationResult(
            decision=PolicyEvaluationDecision.DENY,
            reason="No matching allow rule or active delegation.",
            matched_rule_ids=matched_rule_ids,
            evaluated_policy_id=evaluated_policy.id,
            evaluated_policy_version=evaluated_policy.version,
            timestamp=timestamp,
        )

    def simulate(
        self,
        request: PolicyEvaluationRequest,
        policy_id: Optional[str] = None,
    ) -> PolicyEvaluationResult:
        if policy_id:
            policy = self.store.get_policy(policy_id)
        else:
            policy = self.store.get_active_policy()

        return self.evaluate(request, policy=policy)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rule_matches(
        self,
        rule: PermissionRule,
        request: PolicyEvaluationRequest,
        action_definition: Optional[ActionDefinition],
    ) -> bool:
        if not self._action_matches(rule.actions, request.action, action_definition):
            return False

        if not self._subject_matches(rule.subjects, request):
            return False

        condition = rule.condition

        if condition:
            if (
                condition.high_impact is not None
                and request.high_impact != condition.high_impact
            ):
                return False

            if condition.autonomy_levels is not None:
                if request.autonomy_level not in condition.autonomy_levels:
                    return False

            if condition.subject_roles is not None:
                if not set(condition.subject_roles).intersection(request.roles):
                    return False

            if condition.subject_types is not None:
                if request.subject_type not in condition.subject_types:
                    return False

            if condition.require_approval_refs and not request.approval_refs:
                return False

            if condition.context_equals:
                for key, expected in condition.context_equals.items():
                    if request.context.get(key) != expected:
                        return False

        return True

    def _action_matches(
        self,
        patterns: List[str],
        action: str,
        action_definition: Optional[ActionDefinition],
    ) -> bool:
        for pattern in patterns:
            if pattern == "*":
                return True

            if pattern == action:
                return True

            if pattern.startswith("category:"):
                category = pattern.split(":", 1)[1]

                if action_definition and action_definition.category == category:
                    return True

                continue

            if pattern.endswith(".*"):
                prefix = pattern[:-2]

                if action.startswith(prefix + "."):
                    return True

                continue

            if pattern.endswith("*"):
                prefix = pattern[:-1]

                if action.startswith(prefix):
                    return True

                continue

        return False

    def _subject_matches(
        self,
        subjects: List[str],
        request: PolicyEvaluationRequest,
    ) -> bool:
        if not subjects:
            return False

        subject_key = f"{request.subject_type}:{request.subject_id}"

        for pattern in subjects:
            if pattern == "*":
                return True

            if pattern == subject_key:
                return True

            if pattern == request.subject_id:
                return True

            if pattern == f"{request.subject_type}:*":
                return True

            if pattern.startswith("role:"):
                role = pattern.split(":", 1)[1]

                if role in request.roles:
                    return True

        return False

    def _find_delegation_with_status(
        self,
        request: PolicyEvaluationRequest,
    ) -> tuple:
        """Find any delegation matching grantee + action, return (delegation, is_active)."""

        for delegation in self.delegations.values():
            if delegation.grantee != request.subject_id:
                continue

            action_definition = self.action_catalog.get(request.action)

            if not self._action_matches(
                delegation.actions,
                request.action,
                action_definition,
            ):
                continue

            is_active = self._is_delegation_active(delegation, request)

            return delegation, is_active

        return None, False

    def _is_delegation_active(
        self,
        delegation: DelegationGrant,
        request: PolicyEvaluationRequest,
    ) -> bool:
        now = utcnow()

        if delegation.revoked:
            return False

        expires_at = self._parse_timestamp(delegation.expires_at)

        if expires_at <= now:
            return False

        if (
            delegation.max_uses is not None
            and delegation.use_count >= delegation.max_uses
        ):
            return False

        scope = delegation.scope or {}

        if scope.get("subject_type") and scope["subject_type"] != request.subject_type:
            return False

        if scope.get("resource_type") and scope["resource_type"] != request.resource_type:
            return False

        if scope.get("resource_id") and scope["resource_id"] != request.resource_id:
            return False

        return True

    def _parse_timestamp(self, value: str):
        from datetime import datetime, timezone

        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return utcnow()

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed
