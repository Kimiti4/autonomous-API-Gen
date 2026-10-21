"""Versioned authorization corpus — source-bound, typed, operation-bound policies.

The corpus is certification-owned and separate from the general Campaign A
substrate matrix. Campaign A covers 39 workloads across two backends; adding
mandatory typed authorization there would make the Rust matrix fail for a
known unsupported feature and obscure the result. This corpus instead carries
explicit, reviewable authorization workloads for the Python backend, with the
Rust backend kept as a negative control.

Every workload in this corpus declares, in its own source text:

* the role that governs the operation,
* the operations that role may perform, and
* the operation that role may not perform.

The reviewer-authored approval then binds that source requirement to a typed
ISR policy. No policy is inferred from prose, and the declared behaviour must
be traceable back to the statement that authorised it.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from compiler.core.authorization import ROUTE_VERBS, canonical_action
from reqgraph.ingestion.tor_extractor import HumanApproval

CORPUS_SCHEMA_ID = "tiannara.authorization.corpus"
CORPUS_VERSION = "1.0.0"

#: The operation/resource vocabulary is platform-defined, not invented per app.
_ALLOWED_EFFECTS = ("allow", "deny")


class CorpusError(ValueError):
    """Raised when a corpus entry violates the authorization corpus contract."""


@dataclass(frozen=True)
class OperationBinding:
    """A named operation a policy governs."""

    operation: str
    resource: str
    effect: str
    roles: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "resource": self.resource,
            "effect": self.effect,
            "roles": list(self.roles),
        }

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.operation, self.resource, self.effect)


@dataclass(frozen=True)
class AuthorizationWorkload:
    """One source-bound authorization workload.

    Requirements are addressed by a stable needle inside the source statement,
    because the extractor's requirement identifiers are derived from the
    source digest and the line number.
    """

    workload_id: str
    source_name: str
    source_text: str
    approval_needles: tuple[tuple[str, dict[str, Any]], ...]
    policy_requirement_needle: str
    policy_node_id: str
    policy_node: dict[str, Any]
    policy_edge: dict[str, Any]
    bound_operations: tuple[OperationBinding, ...]
    system_id: str
    revision_id: str
    created_at: str

    def resolve_requirements(self, draft: Any) -> tuple[dict[str, HumanApproval], str]:
        """Bind the corpus needles to the draft's requirement identifiers."""
        approvals: dict[str, HumanApproval] = {}
        policy_requirement_id = ""
        for needle, payload in self.approval_needles:
            matches = [c for c in draft.candidates if needle in c.statement]
            if len(matches) != 1:
                raise CorpusError(
                    f"expected exactly one requirement matching {needle!r}, got {len(matches)}"
                )
            requirement_id = matches[0].requirement_id
            if needle == self.policy_requirement_needle:
                policy_requirement_id = requirement_id
            approvals[requirement_id] = HumanApproval.model_validate(
                _bind_requirement_id(payload, requirement_id)
            )
        if not policy_requirement_id:
            raise CorpusError("the policy requirement needle matched no requirement")
        return approvals, policy_requirement_id

    def as_dict(self) -> dict[str, Any]:
        return {
            "workload_id": self.workload_id,
            "source_name": self.source_name,
            "source_text": self.source_text,
            "approval_needles": [
                {"needle": needle, "payload": payload}
                for needle, payload in self.approval_needles
            ],
            "policy_requirement_needle": self.policy_requirement_needle,
            "policy_node_id": self.policy_node_id,
            "policy_node": self.policy_node,
            "policy_edge": self.policy_edge,
            "bound_operations": [binding.as_dict() for binding in self.bound_operations],
            "system_id": self.system_id,
            "revision_id": self.revision_id,
            "created_at": self.created_at,
        }


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


#: Placeholder replaced with the approving requirement identifier at bind time.
REQUIREMENT_ID_TOKEN = "$requirement_id"


def _bind_requirement_id(payload: Any, requirement_id: str) -> Any:
    """Replace the requirement-id placeholder inside a declaration payload."""
    if isinstance(payload, str):
        return requirement_id if payload == REQUIREMENT_ID_TOKEN else payload
    if isinstance(payload, Mapping):
        return {
            key: _bind_requirement_id(value, requirement_id)
            for key, value in payload.items()
        }
    if isinstance(payload, (list, tuple)):
        return [_bind_requirement_id(value, requirement_id) for value in payload]
    return payload


def corpus_hash(workloads: Sequence[AuthorizationWorkload]) -> str:
    """Deterministic digest of the whole corpus, including source text."""
    payload = [workload.as_dict() for workload in workloads]
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _statement_for(source_text: str, requirement_id: str) -> str:
    from reqgraph.ingestion.tor_extractor import extract_tor_text

    draft = extract_tor_text(source_text, "authorization-corpus.md")
    for candidate in draft.candidates:
        if candidate.requirement_id == requirement_id:
            return candidate.statement
    raise CorpusError(f"requirement {requirement_id!r} is not present in the source text")


def _route_vocabulary(resource: str) -> set[str]:
    return {canonical_action(resource, verb) for verb in ROUTE_VERBS}


def validate_policy_declaration(
    workload: AuthorizationWorkload,
    *,
    statement: str,
) -> None:
    """Validate the typed policy declaration against the authorization contract.

    The declaration must be a typed security policy, bound to the service that
    owns the named resource, and every role, verb, and resource it names must
    be traceable to the statement that authorised it.
    """
    node = workload.policy_node
    node_id = node.get("id")
    if node_id != workload.policy_node_id:
        raise CorpusError("policy node id does not match the corpus entry")
    if node.get("type") != "security_policy":
        raise CorpusError(f"policy node {node_id!r} must be a security_policy node")

    properties = node.get("properties")
    if not isinstance(properties, Mapping):
        raise CorpusError(f"policy node {node_id!r} needs a properties mapping")
    behavior = properties.get("behavior")
    if not isinstance(behavior, Mapping):
        raise CorpusError(f"policy node {node_id!r} must carry typed behavior")
    roles = behavior.get("roles")
    if not isinstance(roles, (list, tuple)) or not roles:
        raise CorpusError(f"policy node {node_id!r} must declare at least one role")
    rules = behavior.get("rules")
    if not isinstance(rules, (list, tuple)) or not rules:
        raise CorpusError(f"policy node {node_id!r} must declare at least one rule")

    edge = workload.policy_edge
    if edge.get("type") != "secured_by":
        raise CorpusError("the policy must be bound with a secured_by edge")
    if edge.get("target_id") != workload.policy_node_id:
        raise CorpusError("the secured_by edge must target the declared policy")

    statement_lower = statement.lower()
    declared: dict[tuple[str, str, str], OperationBinding] = {}
    for rule in rules:
        if not isinstance(rule, Mapping):
            raise CorpusError("each policy rule must be a mapping")
        rule_id = rule.get("rule_id")
        effect = rule.get("effect")
        rule_roles = rule.get("roles")
        actions = rule.get("actions")
        resource = rule.get("resource")
        if not isinstance(rule_id, str) or not rule_id:
            raise CorpusError("each policy rule needs a rule_id")
        if effect not in _ALLOWED_EFFECTS:
            raise CorpusError(f"rule {rule_id!r} must have effect allow or deny")
        if not isinstance(rule_roles, (list, tuple)) or not rule_roles:
            raise CorpusError(f"rule {rule_id!r} must name the roles it governs")
        if not isinstance(actions, (list, tuple)) or not actions:
            raise CorpusError(f"rule {rule_id!r} must name the operations it governs")
        if not isinstance(resource, str) or not resource:
            raise CorpusError(f"rule {rule_id!r} must name the resource it governs")

        vocabulary = _route_vocabulary(resource)
        for action in actions:
            if action not in vocabulary:
                raise CorpusError(
                    f"rule {rule_id!r} names action {action!r}, which is not a route "
                    f"operation of resource {resource!r}"
                )
            verb = action.rsplit(".", 1)[1]
            if verb not in statement_lower:
                raise CorpusError(
                    f"rule {rule_id!r} names operation {action!r}, but the source "
                    "statement does not authorise it"
                )
        if resource.lower() not in statement_lower:
            raise CorpusError(
                f"rule {rule_id!r} names resource {resource!r}, which the source "
                "statement does not authorise"
            )
        for role in (*roles, *rule_roles):
            if str(role).lower() not in statement_lower:
                raise CorpusError(
                    f"rule {rule_id!r} names role {role!r}, which the source "
                    "statement does not authorise"
                )
        binding = OperationBinding(
            operation=actions[0] if len(actions) == 1 else "*, ".join(actions),
            resource=resource,
            effect=effect,
            roles=tuple(str(role) for role in rule_roles),
        )
        for action in actions:
            key = (action, resource, effect)
            declared[key] = OperationBinding(
                operation=action,
                resource=resource,
                effect=effect,
                roles=tuple(str(role) for role in rule_roles),
            )

    expected = {binding.key for binding in workload.bound_operations}
    if expected != set(declared):
        raise CorpusError(
            "the declared bound operations do not match the typed policy rules: "
            f"declared={sorted(declared)} expected={sorted(expected)}"
        )


def validate_workload(workload: AuthorizationWorkload) -> None:
    """Validate a corpus entry end to end."""
    if not workload.source_text.strip():
        raise CorpusError("workload source text must not be empty")
    from reqgraph.ingestion.tor_extractor import extract_tor_text

    draft = extract_tor_text(workload.source_text, workload.source_name)
    approvals, policy_requirement_id = workload.resolve_requirements(draft)
    for requirement_id, approval in approvals.items():
        if not approval.reviewer_id or not approval.approval_ref:
            raise CorpusError(f"approval for {requirement_id!r} must name a reviewer and a reference")
        if not approval.acceptance_criteria:
            raise CorpusError(f"approval for {requirement_id!r} must state acceptance criteria")
    statement = _statement_for(workload.source_text, policy_requirement_id)
    validate_policy_declaration(workload, statement=statement)


def build_workload(
    *,
    workload_id: str,
    source_name: str,
    source_text: str,
    approval_needles: Sequence[tuple[str, dict[str, Any]]],
    policy_requirement_needle: str,
    policy_node_id: str,
    policy_node: dict[str, Any],
    policy_edge: dict[str, Any],
    bound_operations: Sequence[OperationBinding],
    system_id: str,
    revision_id: str,
    created_at: str,
) -> AuthorizationWorkload:
    """Build and validate one corpus entry."""
    workload = AuthorizationWorkload(
        workload_id=workload_id,
        source_name=source_name,
        source_text=source_text,
        approval_needles=tuple(approval_needles),
        policy_requirement_needle=policy_requirement_needle,
        policy_node_id=policy_node_id,
        policy_node=policy_node,
        policy_edge=policy_edge,
        bound_operations=tuple(bound_operations),
        system_id=system_id,
        revision_id=revision_id,
        created_at=created_at,
    )
    validate_workload(workload)
    return workload
