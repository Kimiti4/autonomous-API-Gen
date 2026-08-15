"""
Phase 28 — Policy Compiler and Policy Set Manager.

Transforms high-level constitutional rules into enforceable PolicyRule
definitions, validates their consistency, and produces machine-evaluable
policy artifacts (Milestone 1). Policy sets are bound to a constitution
and become immutable once activated.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from constitutional_architecture.governance.schemas import (
    ApprovalRequirement,
    Condition,
    ConditionOperator,
    Constraint,
    PolicyRule,
    PolicySetISR,
    PolicySetStatus,
    RuleEffect,
    FailureMode,
)

_SUPPORTED_OPERATORS = {op.value for op in ConditionOperator}
_SUPPORTED_EFFECTS = {eff.value for eff in RuleEffect}
_KNOWN_FIELD_PREFIXES = ("actor.", "context.", "subject.")


class PolicyCompilationError(ValueError):
    pass


class PolicyCompiler:
    """Validates and compiles declarative rule definitions."""

    def compile_rule(self, definition: Dict[str, Any]) -> PolicyRule:
        try:
            rule = PolicyRule(
                id=definition["id"],
                name=definition.get("name", definition["id"]),
                description=definition.get("description", ""),
                effect=RuleEffect(definition["effect"]),
                priority=definition.get("priority", 100),
                subject_types=list(definition.get("subject_types", [])),
                actions=list(definition.get("actions", [])),
                conditions=[
                    Condition(
                        field=cond["field"],
                        operator=ConditionOperator(cond["operator"]),
                        value=cond.get("value"),
                    )
                    for cond in definition.get("conditions", [])
                ],
                required_evidence=list(definition.get("required_evidence", [])),
                required_approvals=[
                    ApprovalRequirement(**req)
                    for req in definition.get("required_approvals", [])
                ],
                constraints=[
                    Constraint(**c) for c in definition.get("constraints", [])
                ],
                failure_mode=FailureMode(
                    definition.get("failure_mode", "DENY")
                ),
            )
        except KeyError as exc:
            raise PolicyCompilationError(
                f"Rule definition missing required field: {exc}"
            ) from exc
        self.validate_rule(rule)
        return rule

    def validate_rule(self, rule: PolicyRule) -> None:
        if not rule.subject_types:
            raise PolicyCompilationError(f"Rule {rule.id} has no subject_types.")
        if not rule.actions:
            raise PolicyCompilationError(f"Rule {rule.id} has no actions.")
        for condition in rule.conditions:
            if condition.operator.value not in _SUPPORTED_OPERATORS:
                raise PolicyCompilationError(
                    f"Rule {rule.id} uses unknown operator "
                    f"{condition.operator}."
                )
            if not condition.field.startswith(_KNOWN_FIELD_PREFIXES):
                raise PolicyCompilationError(
                    f"Rule {rule.id} condition field {condition.field} "
                    "must start with actor., context., or subject."
                )
        if rule.effect is RuleEffect.REQUIRE_APPROVAL and not rule.required_approvals:
            raise PolicyCompilationError(
                f"Rule {rule.id} is REQUIRE_APPROVAL but has no approvals."
            )
        if rule.effect is RuleEffect.REQUIRE_EVIDENCE and not rule.required_evidence:
            raise PolicyCompilationError(
                f"Rule {rule.id} is REQUIRE_EVIDENCE but has no evidence list."
            )

    def consistency_report(self, rules: List[PolicyRule]) -> List[str]:
        """Advisory report: flags rules shadowed by deny rules."""
        findings: List[str] = []
        for rule in rules:
            if rule.effect is RuleEffect.ALLOW:
                for other in rules:
                    if other is rule or other.effect is not RuleEffect.DENY:
                        continue
                    overlap = set(rule.subject_types) & set(other.subject_types)
                    if overlap and set(rule.actions) & set(other.actions):
                        findings.append(
                            f"allow rule {rule.id} is shadowed by deny rule "
                            f"{other.id} (deny wins by design)"
                        )
        return findings


class PolicySetManager:
    """Versioned store for policy sets bound to constitutions."""

    def __init__(self, compiler: Optional[PolicyCompiler] = None) -> None:
        self.compiler = compiler or PolicyCompiler()
        self._policy_sets: Dict[str, PolicySetISR] = {}
        self._versions: Dict[str, Dict[str, PolicySetISR]] = {}
        self._immutable: set[str] = set()

    def create(
        self,
        name: str,
        constitution_id: str,
        constitution_version: str,
        *,
        rule_definitions: Optional[List[Dict[str, Any]]] = None,
        applies_to: Optional[List[str]] = None,
        created_by: str = "governance_kernel",
    ) -> PolicySetISR:
        rules = (
            [self.compiler.compile_rule(d) for d in rule_definitions]
            if rule_definitions
            else []
        )
        policy_set = PolicySetISR(
            id=f"policy_set_{uuid.uuid4().hex[:10]}",
            name=name,
            constitution_id=constitution_id,
            constitution_version=constitution_version,
            policy_rules=rules,
            applies_to=applies_to or [],
            created_by=created_by,
        )
        policy_set.recompute_hash()
        self._versions.setdefault(policy_set.id, {})[policy_set.version] = policy_set
        self._policy_sets[policy_set.id] = policy_set
        return policy_set

    def get(self, policy_set_id: str) -> PolicySetISR:
        return self._policy_sets[policy_set_id]

    def activate(self, policy_set_id: str) -> PolicySetISR:
        policy_set = self._policy_sets[policy_set_id]
        if policy_set.status is PolicySetStatus.REVOKED:
            raise ValueError("A revoked policy set cannot be activated.")
        policy_set.status = PolicySetStatus.ACTIVE
        self._immutable.add(policy_set_id)
        return policy_set

    def deprecate(self, policy_set_id: str) -> PolicySetISR:
        policy_set = self._policy_sets[policy_set_id]
        policy_set.status = PolicySetStatus.DEPRECATED
        return policy_set

    def revoke(self, policy_set_id: str) -> PolicySetISR:
        policy_set = self._policy_sets[policy_set_id]
        policy_set.status = PolicySetStatus.REVOKED
        return policy_set

    def rules_for(
        self,
        subject_type: str,
        action: str,
        *,
        active_only: bool = True,
    ) -> List[Tuple["PolicySetISR", PolicyRule]]:
        candidates: List[Tuple["PolicySetISR", PolicyRule]] = []
        for policy_set in self._policy_sets.values():
            if active_only and policy_set.status is not PolicySetStatus.ACTIVE:
                continue
            for rule in policy_set.policy_rules:
                if (
                    subject_type in rule.subject_types
                    and action in rule.actions
                ):
                    candidates.append((policy_set, rule))
        candidates.sort(key=lambda pr: (pr[1].priority, pr[1].id))
        return candidates

    def active_sets(self) -> List[PolicySetISR]:
        return sorted(
            (
                p
                for p in self._policy_sets.values()
                if p.status is PolicySetStatus.ACTIVE
            ),
            key=lambda p: p.id,
        )

    def fingerprint(self, policy_set_id: str) -> str:
        return self._policy_sets[policy_set_id].content_hash

    def is_immutable(self, policy_set_id: str) -> bool:
        return policy_set_id in self._immutable

    def export_policy_sets(self) -> List[Dict[str, Any]]:
        return [p.model_dump() for p in sorted(self._policy_sets.values(), key=lambda p: p.id)]
