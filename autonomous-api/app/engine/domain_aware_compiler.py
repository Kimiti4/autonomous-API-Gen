"""Domain-aware compilation with explicit capability contracts."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping
from .synthesis import SynthesizedProposal, synthesis_ready
from .fullstack_genome import (
    FullStackGenome, FrontendGenome, BackendGenome, DataGenome,
    SecurityGenome, OperationalGenome,
)
from .fullstack_mutation import compatibility_errors


@dataclass(frozen=True)
class DomainConstraint:
    domain: str
    required: bool
    properties: tuple[str, ...]
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class CompilationPlan:
    proposal_id: str
    constraints: tuple[DomainConstraint, ...]


def build_plan(proposal: SynthesizedProposal) -> CompilationPlan:
    if not synthesis_ready(proposal):
        raise ValueError("synthesis-not-ready")
    domains = set(proposal.domains)
    constraints = tuple(
        DomainConstraint(
            domain=d,
            required=True,
            properties=tuple(sorted(
                p for p in proposal.target_properties
                if p.lower().startswith(d)
                or d in p.lower()
            )),
            evidence=proposal.evidence,
        )
        for d in ("frontend", "backend", "data", "security", "operations")
        if d in domains
    )
    return CompilationPlan(proposal.proposal_id, constraints)


def _constraint(plan: CompilationPlan, domain: str) -> DomainConstraint:
    for c in plan.constraints:
        if c.domain == domain:
            return c
    raise ValueError(f"missing-domain-constraint:{domain}")


def _change_for(changes: tuple[str, ...], domain: str) -> str:
    matches = tuple(x for x in changes if x.lower().startswith(domain + "-"))
    if not matches:
        raise ValueError(f"missing-domain-change:{domain}")
    return matches[0]


def compile_domain_aware(proposal: SynthesizedProposal) -> FullStackGenome:
    plan = build_plan(proposal)
    changes = proposal.changes

    fe = _constraint(plan, "frontend")
    be = _constraint(plan, "backend")
    da = _constraint(plan, "data")
    se = _constraint(plan, "security")
    op = _constraint(plan, "operations")

    genome = FullStackGenome(
        FrontendGenome(_change_for(changes, "frontend"), "domain-derived",
                       "evidence-backed", "contract-driven", "accessible"),
        BackendGenome(_change_for(changes, "backend"), "domain-derived",
                      "validated", "observable", "resilient"),
        DataGenome(_change_for(changes, "data"), "integrity-first",
                   "versioned", "traceable"),
        SecurityGenome(_change_for(changes, "security"), "least-privilege",
                       se.properties, se.evidence, "auditable"),
        OperationalGenome(_change_for(changes, "operations"), "observable",
                          "recoverable", "controlled"),
        proposal.problem_signature,
        proposal.claim,
    )
    errors = compatibility_errors(genome)
    if errors:
        raise ValueError("compiled-genome-incompatible:" + ";".join(errors))
    return genome
