"""Translate discovered architectural impact into executable co-evolution planning."""
from __future__ import annotations
from dataclasses import dataclass
from .impact_discovery import ImpactPlan


@dataclass(frozen=True)
class DomainPlan:
    domain: str
    reason: str
    required_properties: tuple[str, ...]


@dataclass(frozen=True)
class CoEvolutionPlan:
    source_domain: str
    domains: tuple[DomainPlan, ...]
    impact_evidence: tuple[str, ...]
    impact_complete: bool
    uncertainty_reasons: tuple[str, ...]


DOMAIN_PROPERTIES = {
    "frontend": ("accessibility", "interaction-consistency", "state-integrity"),
    "backend": ("api-contract", "effect-safety", "failure-recovery"),
    "data": ("data-integrity", "migration-safety", "traceability"),
    "security": ("authorization", "trust-boundary", "auditability"),
    "operations": ("observability", "recoverability", "failure-isolation"),
    "fullstack": ("cross-domain-contracts", "security", "operability", "end-to-end-flow"),
}


def build_coevolution_plan(
    impact: ImpactPlan,
    known_domains: tuple[str, ...],
    dependency_graph_complete: bool,
) -> CoEvolutionPlan:
    if not known_domains:
        raise ValueError("coevolution-plan-requires-known-domains")

    plans = []
    evidence = set()
    for finding in impact.findings:
        domain = finding.domain
        plans.append(
            DomainPlan(
                domain,
                finding.reason,
                DOMAIN_PROPERTIES.get(domain, ("domain-contract",)),
            )
        )
        for relation in finding.relations:
            evidence.update(relation.evidence)

    uncertainty = []
    if not dependency_graph_complete:
        uncertainty.append("dependency-graph-incomplete")

    unknown = {p.domain for p in plans} - set(known_domains)
    if unknown:
        uncertainty.append("unknown-domain:" + ",".join(sorted(unknown)))

    return CoEvolutionPlan(
        impact.source_domain,
        tuple(sorted(plans, key=lambda p: p.domain)),
        tuple(sorted(evidence)),
        dependency_graph_complete and not unknown,
        tuple(uncertainty),
    )


def require_complete_plan(plan: CoEvolutionPlan) -> None:
    if not plan.impact_complete:
        raise ValueError(
            "coevolution-impact-uncertain:" +
            ",".join(plan.uncertainty_reasons)
        )
