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
from compiler.core.plan import CompilationPlan, SecurityPolicy, Service

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


def effect_owning_service(plan: CompilationPlan, effect_id: str) -> Service | None:
    """Return the single service that causes ``effect_id``, or ``None``.

    More than one owner (or an owner that is not a service) means the effect's
    authorization enforcement point is ambiguous; callers must fail closed.
    """
    services = {service.id: service for service in plan.services}
    owners = {
        binding.source_id
        for binding in plan.effect_bindings
        if binding.effect_id == effect_id
    }
    if len(owners) != 1:
        return None
    return services.get(next(iter(owners)))


def _route_actions(service: Service) -> dict[str, str]:
    """Map every canonical route action to the resource it governs."""
    return {
        canonical_action(model.entity_name, verb): model.entity_name
        for model in service.data_models
        for verb in ROUTE_VERBS
    }


def assert_effect_contracts_enforceable(plan: CompilationPlan) -> None:
    """An executable effect must bind to an enforcement point this plan emits.

    ``authorized_operation`` uses the same canonical ``<entity>.<verb>``
    vocabulary as the emitted routes, and ``permitted_side_effect`` must name
    the resource that action governs. An operation the owning service does not
    emit, a side effect it does not own, or a contract no typed allow rule can
    ever grant has no enforcement point: the effect would be refused for every
    principal or checked against an empty policy set. Such plans fail closed
    instead of emitting a runtime that merely looks enforced.
    """
    for effect in plan.effects:
        behavior = effect.behavior
        if behavior is None or not behavior.is_executable():
            continue
        service = effect_owning_service(plan, effect.id)
        if service is None:
            raise UnsupportedSemanticsError(
                "effect_execution: effect "
                f"'{effect.id}' declares an executable contract but is not "
                "caused by exactly one service, so it has no authorization "
                "enforcement point"
            )
        action = behavior.authorized_operation
        resource = behavior.permitted_side_effect
        governed = _route_actions(service).get(action or "")
        if governed is None:
            raise UnsupportedSemanticsError(
                "effect_execution: effect "
                f"'{effect.id}' declares authorized operation '{action}', "
                f"which service '{service.id}' does not emit"
            )
        if resource != governed:
            raise UnsupportedSemanticsError(
                "effect_execution: effect "
                f"'{effect.id}' permits a side effect on '{resource}', but "
                f"operation '{action}' governs '{governed}'"
            )
        granting = [
            rule
            for policy in service_policies(service)
            for rule in policy.behavior.rules
            if rule.effect == "allow"
            and ("*" in rule.actions or action in rule.actions)
            and rule.resource in (governed, "*")
        ]
        if not granting:
            raise UnsupportedSemanticsError(
                "effect_execution: effect "
                f"'{effect.id}' declares authorized operation '{action}' but "
                f"no typed allow rule of service '{service.id}' governs it, so "
                "no principal could ever execute the effect"
            )


def declaration_only_policies(plan: CompilationPlan) -> list[SecurityPolicy]:
    """Return policies that declare a boundary without stating an enforceable rule."""
    declared: list[SecurityPolicy] = []
    for policy in plan.security:
        if not _typed(policy):
            declared.append(policy)
    return declared


def assert_authorization_enforceable(plan: CompilationPlan) -> None:
    """Fail closed when a declared obligation cannot be enforced.

    The check is deliberately separate from the static capability gate: the
    capability says the backend implements authorization enforcement, this
    check says whether *this* plan's obligations are enforceable by it.
    """
    from compiler.core.declared_api import declared_routes

    # Declared operations are emittable only with an explicit service binding,
    # an unambiguous resource, and typed policies that actually govern the
    # operation. This also rejects an operation that names an unknown policy.
    declared_routes(plan)

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

    assert_effect_contracts_enforceable(plan)


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
