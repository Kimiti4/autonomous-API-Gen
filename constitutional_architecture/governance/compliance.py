"""
Phase 28 — Compliance Engine (Policy Decision Point).

Evaluates proposed actions against active policies (Milestone 2) and
produces ALLOW / DENY / REQUIRE_APPROVAL / REQUIRE_EVIDENCE /
ALLOW_WITH_CONSTRAINTS decisions with explanations.

Semantics (fail closed, deterministic):
  - rules match on (subject_type, action), evaluated in (priority, id) order
  - any MATCHED_DENY overrides everything   -> DENY
  - else missing required evidence          -> REQUIRE_EVIDENCE
  - else unsatisfied required approvals     -> REQUIRE_APPROVAL
  - else constraints present                -> ALLOW_WITH_CONSTRAINTS
  - else                                    -> ALLOW
  - active exceptions matching the request suppress matched deny rules and
    are reported in exceptions_applied
"""

from __future__ import annotations

import re
from typing import Any, List, Optional, Tuple

from constitutional_architecture.governance.exception_manager import (
    GovernanceExceptionManager,
)
from constitutional_architecture.governance.policy_compiler import PolicySetManager
from constitutional_architecture.governance.schemas import (
    ApprovalRequirement,
    Condition,
    ConditionOperator,
    Constraint,
    Decision,
    EvaluationOutcome,
    GovernanceDecision,
    GovernanceEvaluationRequest,
    PolicyEvaluation,
    PolicyRule,
    RuleEffect,
)


class ComplianceEngine:
    """The Policy Decision Point of the governance kernel."""

    def __init__(
        self,
        policy_sets: PolicySetManager,
        exceptions: GovernanceExceptionManager,
    ) -> None:
        self.policy_sets = policy_sets
        self.exceptions = exceptions

    def evaluate(self, request: GovernanceEvaluationRequest) -> GovernanceDecision:
        rules = self.policy_sets.rules_for(request.subject_type, request.action)
        evaluations: List[PolicyEvaluation] = []
        denied_by: List[PolicyRule] = []
        matched_approval: Optional[PolicyRule] = None
        matched_evidence: Optional[PolicyRule] = None
        matched_constraints: Optional[PolicyRule] = None
        matched_allow: bool = False
        applicable_exceptions = self.exceptions.applicable_to(
            request, rule_ids={rule.id for _, rule in rules}
        )
        applied_exception_ids = sorted(ex.id for ex in applicable_exceptions)
        for exception in applicable_exceptions:
            self.exceptions.record_use(exception.id)

        for policy_set, rule in rules:
            matched, explanation = self._evaluate_rule(rule, request)
            evaluations.append(
                PolicyEvaluation(
                    policy_set_id=policy_set.id,
                    policy_set_version=policy_set.version,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    outcome=matched,
                    explanation=explanation,
                )
            )
            if matched is EvaluationOutcome.MATCHED_DENY:
                suppressed = any(
                    ex.scope.covers(request)
                    for ex in applicable_exceptions
                )
                if suppressed:
                    evaluations[-1].explanation += " [suppressed by exception]"
                    continue
                denied_by.append(rule)
            elif matched is EvaluationOutcome.MATCHED_REQUIRE_APPROVAL:
                if matched_approval is None:
                    matched_approval = rule
            elif matched is EvaluationOutcome.MATCHED_REQUIRE_EVIDENCE:
                if matched_evidence is None:
                    matched_evidence = rule
            elif matched is EvaluationOutcome.MATCHED_ALLOW:
                matched_allow = True
                matched_constraints = rule if rule.constraints else matched_constraints

        decision, reason, approvals, evidence, constraints = self._resolve(
            request,
            denied_by=denied_by,
            matched_approval=matched_approval,
            matched_evidence=matched_evidence,
            matched_constraints=matched_constraints,
            matched_allow=matched_allow,
        )
        result = GovernanceDecision(
            decision=decision,
            reason=reason,
            evaluated_policies=evaluations,
            required_approvals=approvals,
            required_evidence=evidence,
            constraints=constraints,
            exceptions_applied=applied_exception_ids,
        )
        result.recompute_hash()
        return result

    def _evaluate_rule(
        self, rule: PolicyRule, request: GovernanceEvaluationRequest
    ) -> Tuple[EvaluationOutcome, str]:
        for condition in rule.conditions:
            satisfied, detail = self._eval_condition(condition, request)
            if not satisfied:
                return EvaluationOutcome.NOT_MATCHED, (
                    f"condition {condition.field} not satisfied ({detail})"
                )
        if rule.effect is RuleEffect.DENY:
            return EvaluationOutcome.MATCHED_DENY, f"deny rule {rule.name} matched"
        if rule.effect is RuleEffect.REQUIRE_APPROVAL:
            return (
                EvaluationOutcome.MATCHED_REQUIRE_APPROVAL,
                f"requires approval: {rule.name}",
            )
        if rule.effect is RuleEffect.REQUIRE_EVIDENCE:
            return (
                EvaluationOutcome.MATCHED_REQUIRE_EVIDENCE,
                f"requires evidence: {rule.name}",
            )
        if rule.effect is RuleEffect.ALLOW_WITH_CONSTRAINTS:
            return EvaluationOutcome.MATCHED_ALLOW, f"allow with constraints: {rule.name}"
        return EvaluationOutcome.MATCHED_ALLOW, f"allow rule {rule.name} matched"

    def _resolve(
        self,
        request: GovernanceEvaluationRequest,
        *,
        denied_by: List[PolicyRule],
        matched_approval: Optional[PolicyRule],
        matched_evidence: Optional[PolicyRule],
        matched_constraints: Optional[PolicyRule],
        matched_allow: bool,
    ) -> Tuple[Decision, str, List[ApprovalRequirement], List[str], List[Constraint]]:
        if denied_by:
            names = "; ".join(rule.name for rule in denied_by)
            return (
                Decision.DENY,
                f"denied by: {names}",
                [],
                [],
                [],
            )
        if matched_evidence is not None:
            missing = [
                e
                for e in matched_evidence.required_evidence
                if e not in request.evidence_refs
            ]
            if missing:
                return (
                    Decision.REQUIRE_EVIDENCE,
                    f"missing required evidence: {', '.join(missing)}",
                    [],
                    sorted(missing),
                    [],
                )
        if matched_approval is not None:
            return (
                Decision.REQUIRE_APPROVAL,
                f"approval required by {matched_approval.name}",
                self._unique_approvals(matched_approval.required_approvals),
                [],
                matched_approval.constraints,
            )
        if matched_constraints is not None and matched_constraints.constraints:
            return (
                Decision.ALLOW_WITH_CONSTRAINTS,
                f"allowed with constraints by {matched_constraints.name}",
                [],
                [],
                matched_constraints.constraints,
            )
        if not matched_allow:
            return Decision.ALLOW, "no policy matched; allow by default", [], [], []
        return Decision.ALLOW, "allowed by policy", [], [], []

    def _unique_approvals(
        self, approvals: List[ApprovalRequirement]
    ) -> List[ApprovalRequirement]:
        seen: set[Tuple[str, str]] = set()
        unique: List[ApprovalRequirement] = []
        for req in approvals:
            key = (req.approver_type.value, req.approver_id or "")
            if key not in seen:
                seen.add(key)
                unique.append(req)
        return unique

    def _eval_condition(
        self, condition: Condition, request: GovernanceEvaluationRequest
    ) -> Tuple[bool, str]:
        actual = self._resolve_field(condition.field, request)
        expected = self._resolve_value(condition.value, request)
        op = condition.operator
        if op is ConditionOperator.EXISTS:
            return (condition.value is True) == (actual is not None), (
                "exists" if actual is not None else "missing"
            )
        if op is ConditionOperator.NOT_EXISTS:
            return actual is None, "not exists" if actual is None else "present"
        if actual is None:
            return False, f"{condition.field} is missing"
        try:
            if op is ConditionOperator.EQUALS:
                ok = actual == expected
            elif op is ConditionOperator.NOT_EQUALS:
                ok = actual != expected
            elif op is ConditionOperator.IN:
                ok = actual in (expected or [])
            elif op is ConditionOperator.NOT_IN:
                ok = actual not in (expected or [])
            elif op is ConditionOperator.GREATER_THAN:
                ok = float(actual) > float(expected)
            elif op is ConditionOperator.LESS_THAN:
                ok = float(actual) < float(expected)
            elif op is ConditionOperator.MATCHES:
                ok = re.search(str(expected), str(actual)) is not None
            else:
                return False, f"unsupported operator {op}"
        except (TypeError, ValueError):
            return False, f"cannot compare {actual!r} {op.value} {expected!r}"
        return ok, f"{actual!r} {op.value} {expected!r}"

    def _resolve_field(self, field: str, request: GovernanceEvaluationRequest) -> Any:
        head, _, tail = field.partition(".")
        if head == "actor":
            value: Any = request.actor
        elif head == "context":
            value = request.context
        elif head == "subject":
            value = {"id": request.subject_id, "type": request.subject_type}
        else:
            return None
        if not tail:
            return value
        for part in tail.split("."):
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = getattr(value, part, None)
        return value

    def _resolve_value(self, value: Any, request: GovernanceEvaluationRequest) -> Any:
        if isinstance(value, str) and value.startswith(("actor.", "context.")):
            return self._resolve_field(value, request)
        return value
