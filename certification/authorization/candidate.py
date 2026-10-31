"""The candidate manifest for the authorization certification lane.

The manifest is the single record that binds a source-bound authorization
candidate to everything that must agree for it to be certified:

    source digest -> requirement graph hash -> ISR content hash -> plan hash
    -> generated bundle hash -> runtime test report hash

Nothing here decides whether the candidate is good. It records the bindings so
that the independent verifier can recompute them from the persisted artifacts.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

CANDIDATE_SCHEMA_ID = "tiannara.authorization.candidate"
CANDIDATE_SCHEMA_VERSION = "1.1.0"

#: The adversarial proof the generated application must execute for itself.
REQUIRED_ADVERSARIAL_TESTS: tuple[str, ...] = (
    "test_authorization_requires_a_signed_token",
    "test_authorization_rejects_a_tampered_token",
    "test_authorization_rejects_an_expired_token",
    "test_authorization_denies_a_principal_without_a_grant",
    "test_authorization_ignores_spoofed_role_and_tenant_headers",
    "test_denied_request_does_not_mutate_state",
    "test_authorization_runtime_denies_by_default",
    "test_authorization_runtime_explicit_deny_wins_over_allow",
    "test_authorization_runtime_missing_attribute_never_grants",
    "test_authorization_runtime_isolates_tenants",
)

#: The additional proof a candidate with declared API operations must execute.
DECLARED_OPERATION_TESTS: tuple[str, ...] = (
    "test_declared_operation_emits_the_exact_route",
    "test_declared_operation_requires_a_signed_token",
    "test_declared_operation_denies_a_principal_without_a_grant",
    "test_declared_operation_rejects_a_malformed_payload",
    "test_declared_operation_authorized_create_and_read",
    "test_declared_operation_denial_does_not_mutate_state",
    "test_declared_operation_explicit_deny_wins",
)


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(obj: Any) -> str:
    return sha256_text(canonical_json(obj))


@dataclass(frozen=True)
class AuthorizationCandidate:
    """The bound candidate record."""

    candidate_id: str
    corpus_id: str
    corpus_version: str
    corpus_hash: str
    workload_id: str
    source_name: str
    source_sha256: str
    requirement_graph_hash: str
    isr_revision_id: str
    isr_content_hash: str
    plan_id: str
    plan_hash: str
    backend_name: str
    backend_version: str
    artifact_bundle_hash: str
    policy_ids: tuple[str, ...]
    bound_operations: tuple[dict[str, Any], ...]
    runtime_report_hash: str
    required_adversarial_tests: tuple[str, ...] = REQUIRED_ADVERSARIAL_TESTS
    declared_routes: tuple[dict[str, Any], ...] = ()

    def manifest(self) -> dict[str, Any]:
        return {
            "schema_id": CANDIDATE_SCHEMA_ID,
            "schema_version": CANDIDATE_SCHEMA_VERSION,
            "candidate_id": self.candidate_id,
            "corpus_id": self.corpus_id,
            "corpus_version": self.corpus_version,
            "corpus_hash": self.corpus_hash,
            "workload_id": self.workload_id,
            "source_name": self.source_name,
            "source_sha256": self.source_sha256,
            "requirement_graph_hash": self.requirement_graph_hash,
            "isr_revision_id": self.isr_revision_id,
            "isr_content_hash": self.isr_content_hash,
            "plan_id": self.plan_id,
            "plan_hash": self.plan_hash,
            "backend_name": self.backend_name,
            "backend_version": self.backend_version,
            "artifact_bundle_hash": self.artifact_bundle_hash,
            "policy_ids": list(self.policy_ids),
            "bound_operations": [dict(binding) for binding in self.bound_operations],
            "declared_routes": [dict(route) for route in self.declared_routes],
            "runtime_report_hash": self.runtime_report_hash,
            "required_adversarial_tests": list(self.required_adversarial_tests),
        }

    @property
    def manifest_hash(self) -> str:
        return sha256_json(self.manifest())


def bound_operations_of(plan: Any) -> tuple[dict[str, Any], ...]:
    """Return the named operations the plan's policies govern."""
    from compiler.core.authorization import protected_services

    operations: list[dict[str, Any]] = []
    for service_id, policies in sorted(protected_services(plan).items()):
        for policy in policies:
            for rule in policy.behavior.rules:
                for action in rule.actions:
                    operations.append({
                        "policy_id": policy.policy_id,
                        "service_id": service_id,
                        "operation": action,
                        "resource": rule.resource,
                        "effect": rule.effect,
                        "roles": list(rule.roles),
                        "rule_id": rule.rule_id,
                    })
    operations.sort(key=lambda item: (item["policy_id"], item["operation"], item["effect"]))
    return tuple(operations)


def declared_routes_of(plan: Any) -> tuple[dict[str, Any], ...]:
    """Return the exact declared routes the plan requires, with every binding."""
    from compiler.core.declared_api import declared_routes

    return tuple(route.as_dict() for route in declared_routes(plan))


def build_candidate(
    *,
    candidate_id: str,
    corpus_id: str,
    corpus_version: str,
    corpus_hash: str,
    workload_id: str,
    projection: Any,
    plan: Any,
    repo: Any,
    runtime_report_hash: str,
    required_tests: Sequence[str] | None = None,
) -> AuthorizationCandidate:
    """Bind a source-bound candidate into its manifest."""
    from reqgraph.adapters.tor_isr import requirement_graph_hash

    return AuthorizationCandidate(
        candidate_id=candidate_id,
        corpus_id=corpus_id,
        corpus_version=corpus_version,
        corpus_hash=corpus_hash,
        workload_id=workload_id,
        source_name=projection.source_name,
        source_sha256=projection.source_sha256,
        requirement_graph_hash=requirement_graph_hash(projection.requirement_graph),
        isr_revision_id=projection.revision.revision_id,
        isr_content_hash=projection.revision.content_hash,
        plan_id=plan.plan_id,
        plan_hash=sha256_json(plan.model_dump(mode="json")),
        backend_name="python-fastapi",
        backend_version="1.4.0",
        artifact_bundle_hash=repo.content_hash,
        policy_ids=tuple(sorted(policy.policy_id for policy in plan.security)),
        bound_operations=bound_operations_of(plan),
        runtime_report_hash=runtime_report_hash,
        required_adversarial_tests=tuple(required_tests or REQUIRED_ADVERSARIAL_TESTS),
        declared_routes=declared_routes_of(plan),
    )


def candidate_from_manifest(manifest: Mapping[str, Any]) -> AuthorizationCandidate:
    """Rebuild a candidate from a persisted manifest."""
    return AuthorizationCandidate(
        candidate_id=manifest["candidate_id"],
        corpus_id=manifest["corpus_id"],
        corpus_version=manifest["corpus_version"],
        corpus_hash=manifest["corpus_hash"],
        workload_id=manifest["workload_id"],
        source_name=manifest["source_name"],
        source_sha256=manifest["source_sha256"],
        requirement_graph_hash=manifest["requirement_graph_hash"],
        isr_revision_id=manifest["isr_revision_id"],
        isr_content_hash=manifest["isr_content_hash"],
        plan_id=manifest["plan_id"],
        plan_hash=manifest["plan_hash"],
        backend_name=manifest["backend_name"],
        backend_version=manifest["backend_version"],
        artifact_bundle_hash=manifest["artifact_bundle_hash"],
        policy_ids=tuple(manifest["policy_ids"]),
        bound_operations=tuple(dict(binding) for binding in manifest["bound_operations"]),
        runtime_report_hash=manifest["runtime_report_hash"],
        required_adversarial_tests=tuple(manifest["required_adversarial_tests"]),
        declared_routes=tuple(
            dict(route) for route in manifest.get("declared_routes") or ()
        ),
    )


def stale_evidence_problems(
    candidate: AuthorizationCandidate,
    *,
    source_sha256: str,
    requirement_graph_hash: str,
    isr_content_hash: str,
    plan_hash: str,
    artifact_bundle_hash: str,
    runtime_report_hash: str,
) -> list[str]:
    """Return the mismatches that prove an evidence record is stale."""
    problems: list[str] = []
    for label, expected, actual in (
        ("source_sha256", candidate.source_sha256, source_sha256),
        ("requirement_graph_hash", candidate.requirement_graph_hash, requirement_graph_hash),
        ("isr_content_hash", candidate.isr_content_hash, isr_content_hash),
        ("plan_hash", candidate.plan_hash, plan_hash),
        ("artifact_bundle_hash", candidate.artifact_bundle_hash, artifact_bundle_hash),
        ("runtime_report_hash", candidate.runtime_report_hash, runtime_report_hash),
    ):
        if expected != actual:
            problems.append(f"{label} mismatch: evidence={expected} candidate={actual}")
    return problems


def required_tests_of(manifest: Mapping[str, Any]) -> Sequence[str]:
    return tuple(manifest.get("required_adversarial_tests") or REQUIRED_ADVERSARIAL_TESTS)
