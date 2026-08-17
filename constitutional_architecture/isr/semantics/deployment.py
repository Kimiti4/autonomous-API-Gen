"""R2.10.3-G — deployment rollout/rollback primitive (intent and lifecycle guarantees).

Deployment is where the gravity toward infrastructure specification is
strongest: the entire culture expresses deployment as Kubernetes manifests,
replica counts, and CI/CD pipelines. G holds TWO distinct boundaries, because
they fail differently:

1. NO realization technology in the gene — the strictest mechanism guard yet.
   The lint rejects orchestration platforms (kubernetes, k8s, docker, ecs,
   nomad, mesos), IaC tooling (terraform, pulumi, cloudformation, ansible,
   helm, kubectl), cloud providers (aws, gcp, azure), realization mechanics
   (replica_count, pod_spec, container_image, deployment_manifest, ingress,
   load_balancer_config, service_mesh), and CI/CD tooling (jenkins,
   github_actions, gitlab_ci, circleci, argo). RolloutStrategy values CANARY
   and BLUE_GREEN are SEMANTIC strategies and must pass — they describe
   desired behavior, not implementation.

2. NO backward leak into architecture. Deployment references architecture
   (targets = capabilities/modules) by identity; a deployment mutation must
   never propagate into the boundary genes it references. Deployment is a
   lifecycle gene OVER the architecture, never a trojan horse for
   re-encoding it.

CARRIER DECISION (documented, not ambiguous): ``System.deployment_intents``
is a NEW carrier alongside the pre-existing ``System.deployment``
environment placeholder. The two are different semantic layers:
``System.deployment`` describes the ENVIRONMENT (tier, scaling bounds,
networking, monitoring paths, storage, secrets — static attributes of where
the system runs); ``System.deployment_intents`` declares the LIFECYCLE
contract (WHAT a change must accomplish, under what conditions, WHAT must
remain preserved, WHEN rollback is required). Folding intent into the
environment placeholder would mix "what the environment is" with "how a
change must proceed". Intent references targets by identity and composes
with the environment only through the target's architecture.

Rollback reuses C's rollback-as-invariant pattern: rollback is a contract
about what must be restored, never a command. ``rollback_target_ref`` must
name one of the intent's own targets (the C rule: rollback restores a member
of the operation's own refs).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from typing import TYPE_CHECKING, Any, Optional

from constitutional_architecture.isr.semantics.projection import canonical_form, canonicalize

if TYPE_CHECKING:
    from constitutional_architecture.isr.model.isr import ISR


class DeploymentValidationError(ValueError):
    """A deployment intent violates its construction or structural contract."""


@unique
class RolloutStrategy(str, Enum):
    """Semantic rollout behaviors — WHAT the rollout accomplishes, never HOW.

    A backend may realize CANARY via K8s, ECS, or manual traffic shifting,
    provided the declared semantic holds.
    """

    IMMEDIATE = "IMMEDIATE"
    CANARY = "CANARY"
    BLUE_GREEN = "BLUE_GREEN"
    PROGRESSIVE = "PROGRESSIVE"


@dataclass(frozen=True)
class DeploymentIntent:
    """Deployment intent and lifecycle guarantees. Semantic only.

    Declares WHAT deployment must accomplish, under what conditions, WHAT
    must remain preserved, and WHEN rollback is required. NEVER the
    realization — no Kubernetes, Docker, Terraform, replica counts, pods,
    containers, or orchestration mechanics. Reuse of C's
    rollback-as-invariant pattern: rollback is a contract about what must
    be restored, never a command.

    Deployment is a lifecycle gene over existing genes, not an architecture
    carrier: it references targets by identity and must not encode structure.
    """

    deployment_id: str
    target_refs: tuple[str, ...]  # capabilities/modules deployed (by id)
    rollout_strategy: RolloutStrategy
    rollout_constraints: tuple[str, ...] = ()  # semantic rollout constraints
    health_requirements: tuple[str, ...] = ()  # semantic health requirements
    rollback_required: bool = False
    rollback_target_ref: Optional[str] = None  # semantic target to restore
    rollback_invariants: tuple[str, ...] = ()  # what rollback must preserve
    preservation_requirements: tuple[str, ...] = ()  # what must survive deployment

    def __post_init__(self) -> None:
        if not self.deployment_id:
            raise DeploymentValidationError("deployment_id is required")
        if not self.target_refs:
            raise DeploymentValidationError(
                "target_refs required: deployment must target something explicit"
            )
        if self.rollback_required and not self.rollback_target_ref:
            raise DeploymentValidationError(
                "rollback_required demands a rollback_target_ref"
            )


# -- mechanism lint (the dangerous boundary — strictest yet) -----------------

DEPLOYMENT_MECHANISM_TERMS: frozenset[str] = frozenset({
    # orchestration / container platforms
    "kubernetes", "k8s", "docker", "ecs", "ec2", "lambda", "nomad", "mesos",
    # IaC / tooling
    "terraform", "pulumi", "cloudformation", "ansible", "helm", "kubectl",
    # cloud providers
    "aws", "gcp", "azure",
    # realization mechanics
    "replica_count", "pod_spec", "container_image", "deployment_manifest",
    "ingress", "load_balancer_config", "service_mesh",
    # CI/CD tooling
    "jenkins", "github_actions", "gitlab_ci", "circleci", "argo",
})


def deployment_mechanism_hits(intent: DeploymentIntent) -> tuple[str, ...]:
    """Which realization terms (if any) leaked into a deployment's semantic form."""
    lowered = canonicalize(intent).lower()
    return tuple(term for term in DEPLOYMENT_MECHANISM_TERMS if term in lowered)


def assert_deployment_technology_agnostic(intent: DeploymentIntent) -> None:
    """Gate: no realization technology may leak into the semantic representation.

    The asymmetry the lint must preserve: CANARY and BLUE_GREEN are semantic
    strategies and PASS; kubernetes and replica_count FAIL.
    """
    hits = deployment_mechanism_hits(intent)
    if hits:
        raise DeploymentValidationError(
            f"deployment '{intent.deployment_id}' couples to realization(s): {hits}"
        )


# -- structural validation (pre-execution) -----------------------------------

def _deployment_target_ids(system: Any) -> set[str]:
    """The deployment-target identity space: capabilities and modules.

    Consistent with E's member-ref identity space — deployment targets the
    architecture it composes with.
    """
    ids: set[str] = set()
    ids.update(c.capability_id for c in system.business_capabilities)
    ids.update(m.id for m in system.modules)
    return ids


def validate_system_deployment_constraints(system: Any) -> tuple[str, ...]:
    """Structural validation for one system's deployment intents.

    Rejects, pre-execution: duplicate deployment ids, dangling target refs
    (must name capabilities or modules), and rollback targets that are not
    members of the intent's own targets (the C rule). Empty tuple means valid.
    """
    errors: list[str] = []
    target_ids = _deployment_target_ids(system)
    seen: set[str] = set()
    for intent in system.deployment_intents:
        if intent.deployment_id in seen:
            errors.append(
                f"duplicate deployment id '{intent.deployment_id}'"
            )
        seen.add(intent.deployment_id)
        for target_ref in intent.target_refs:
            if target_ref not in target_ids:
                errors.append(
                    f"deployment '{intent.deployment_id}' targets unknown "
                    f"gene '{target_ref}'"
                )
        if intent.rollback_target_ref not in (None, *intent.target_refs):
            errors.append(
                f"deployment '{intent.deployment_id}' rollback target "
                f"'{intent.rollback_target_ref}' is not one of its targets "
                f"{tuple(intent.target_refs)}"
            )
    return tuple(errors)


# -- projection (semantics only) ---------------------------------------------

def project_deployment_intents(isr: Any) -> tuple[dict[str, Any], ...]:
    """Backend-independent semantic projection of deployment lifecycle intents.

    Returns deployment semantics (targets, rollout strategy, health
    requirements, rollback contract, preservation). Never Kubernetes
    manifests, replica counts, CI/CD pipelines, or runnable scripts — those
    are backend realizations, not the intent.
    """
    return tuple(
        canonical_form(intent)
        for intent in getattr(isr.system, "deployment_intents", ())
    )
