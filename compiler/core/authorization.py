"""Authorization obligation analysis for compiled plans.

An *obligation* is a declared rule a generated runtime must enforce. The rules
here are deliberately narrow:

- A policy that carries typed rules (roles plus allow/deny rules) attached to a
  service is an obligation for the routes this compiler emits for that
  service. The action vocabulary is canonical and platform-defined
  (``<entity>.<verb>``), so a policy can only name actions that exist.
- A policy bound to a declared operation is an obligation for that operation.
  A backend that does not emit the declared operation cannot honour it, so the
  obligation fails closed instead of being dropped.
- A policy with no typed rules carries no enforceable rule. It is a
  declaration (an authentication scheme or a structural boundary) and never an
  obligation.

Nothing here decides whether a backend implements enforcement; it decides what
a plan demands and refuses obligations that cannot be honoured.
"""
from __future__ import annotations

from typing import Any, Iterable

from compiler.core.capabilities import SemanticFeature, UnsupportedSemanticsError
from compiler.core.plan import ApiOperation, CompilationPlan, SecurityPolicy, Service

ROUTE_VERBS: tuple[str, ...] = ("read", "create", "update", "delete")


def canonical_action(entity_name: str, verb: str) -> str:
    """Return the canonical action name for a route over ``entity_name``."""
    if verb not in ROUTE_VERBS:
        raise ValueError(f"unknown route verb: {verb}")
    normalized = "".join(
        char if char.isalnum() else "_" for char in entity_name.lower()
    ).strip("_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return f"{normalized}.{verb}"


def _snake(value: str) -> str:
    return canonical_action(value, "read").rsplit(".", 1)[0]


def policy_payload(policy: SecurityPolicy) -> dict[str, Any]:
    """Serialize a typed policy into the runtime payload the emitters use."""
    behavior = policy.behavior
    if behavior is None:
        raise ValueError(f"policy {policy.policy_id} carries no typed rules")
    return {
        "policy_id": policy.policy_id,
        "roles": list(behavior.roles),
        "rules": [
            {
                "rule_id": rule.rule_id,
                "effect": rule.effect,
                "roles": list(rule.roles),
                "actions": list(rule.actions),
                "resource": rule.resource,
                "conditions": dict(rule.conditions),
            }
            for rule in behavior.rules
        ],
    }


def _typed(policy: SecurityPolicy) -> bool:
    return policy.behavior is not None


def service_policies(service: Service) -> list[SecurityPolicy]:
    """Return the typed policies attached to a service, in declaration order."""
    return [policy for policy in service.security_policies if _typed(policy)]


def declaration_only_policies(plan: CompilationPlan) -> list[SecurityPolicy]:
    """Return policies that declare a boundary without stating an enforceable rule."""
    declared: list[SecurityPolicy] = []
    for policy in plan.security:
        if not _typed(policy):
            declared.append(policy)
    return declared


def _operation_obligations(plan: CompilationPlan) -> list[tuple[ApiOperation, SecurityPolicy]]:
    """Return (operation, policy) pairs that bind a policy to a declared route."""
    by_id = {policy.policy_id: policy for policy in plan.security}
    obligations: list[tuple[ApiOperation, SecurityPolicy]] = []
    for api in plan.apis:
        attached = list(api.security_policies)
        if api.behavior is not None:
            for policy_id in api.behavior.authorization_policy_ids:
                policy = by_id.get(policy_id)
                if policy is None:
                    raise UnsupportedSemanticsError(
                        "authorization_policies: operation "
                        f"'{api.id}' references unknown policy '{policy_id}'"
                    )
                attached.append(policy)
        for policy in attached:
            obligations.append((api, policy))
    return obligations


def assert_authorization_enforceable(plan: CompilationPlan) -> None:
    """Fail closed when a declared obligation cannot be enforced.

    The check is deliberately separate from the static capability gate: the
    capability says the backend implements authorization enforcement, this
    check says whether *this* plan's obligations are enforceable by it.
    """
    for api, policy in _operation_obligations(plan):
        if not _typed(policy):
            raise UnsupportedSemanticsError(
                "authorization_policies: policy "
                f"'{policy.policy_id}' is bound to operation '{api.id}' but "
                "carries no typed rules, so no enforcement can be proven"
            )
        raise UnsupportedSemanticsError(
            "authorization_policies: operation "
            f"'{api.id}' declares policy '{policy.policy_id}', but this "
            "backend does not emit declared operations, so the obligation "
            "cannot be enforced"
        )

    emitted_actions: dict[str, set[str]] = {}
    for service in plan.services:
        policies = service_policies(service)
        if not policies:
            continue
        owned = {model.entity_name for model in service.data_models}
        if not owned:
            raise UnsupportedSemanticsError(
                "authorization_policies: service "
                f"'{service.id}' declares policy "
                f"'{policies[0].policy_id}' but owns no route, so the "
                "obligation has no enforcement point"
            )
        actions = {
            canonical_action(entity, verb)
            for entity in owned
            for verb in ROUTE_VERBS
        }
        emitted_actions[service.id] = actions
        for policy in policies:
            for rule in policy.behavior.rules:
                unknown = [
                    action
                    for action in rule.actions
                    if action != "*" and action not in actions
                ]
                if unknown:
                    raise UnsupportedSemanticsError(
                        "authorization_policies: rule "
                        f"'{rule.rule_id}' of policy '{policy.policy_id}' names "
                        f"action(s) {sorted(unknown)} that are not routes of "
                        f"service '{service.id}'"
                    )
                if rule.resource != "*" and not any(
                    model.entity_name == rule.resource for model in service.data_models
                ):
                    raise UnsupportedSemanticsError(
                        "authorization_policies: rule "
                        f"'{rule.rule_id}' of policy '{policy.policy_id}' names "
                        f"resource '{rule.resource}', which service "
                        f"'{service.id}' does not own"
                    )


def protected_services(plan: CompilationPlan) -> dict[str, list[SecurityPolicy]]:
    """Return the services whose emitted routes carry authorization obligations."""
    return {
        service.id: service_policies(service)
        for service in plan.services
        if service_policies(service)
    }


def supported_feature() -> SemanticFeature:
    return SemanticFeature.AUTHORIZATION_POLICIES


def iter_policy_payloads(policies: Iterable[SecurityPolicy]) -> list[dict[str, Any]]:
    return [policy_payload(policy) for policy in policies]
