"""Discover cross-domain impact from declared dependency/effect relationships."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ImpactRelation:
    source_domain: str
    target_domain: str
    relation: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ImpactRequest:
    domain: str
    changed_paths: tuple[str, ...]
    declared_effects: tuple[str, ...]


@dataclass(frozen=True)
class ImpactFinding:
    domain: str
    reason: str
    relations: tuple[ImpactRelation, ...]


@dataclass(frozen=True)
class ImpactPlan:
    source_domain: str
    affected_domains: tuple[str, ...]
    findings: tuple[ImpactFinding, ...]


def discover_impact(
    request: ImpactRequest,
    relations: tuple[ImpactRelation, ...],
) -> ImpactPlan:
    if not request.domain or not request.changed_paths:
        raise ValueError("impact-request-requires-domain-and-paths")
    findings = []
    affected = set()
    for relation in relations:
        if not relation.evidence:
            continue
        if relation.source_domain != request.domain:
            continue
        if relation.relation not in request.declared_effects:
            continue
        affected.add(relation.target_domain)
        findings.append(
            ImpactFinding(
                relation.target_domain,
                f"{relation.relation}-dependency",
                (relation,),
            )
        )
    return ImpactPlan(
        request.domain,
        tuple(sorted(affected)),
        tuple(findings),
    )


def require_declared_impact_evidence(plan: ImpactPlan) -> None:
    for finding in plan.findings:
        for relation in finding.relations:
            if not relation.evidence:
                raise ValueError("impact-relation-requires-evidence")
