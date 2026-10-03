"""Generate concrete domain mutation and verification work from an impact plan."""
from __future__ import annotations
from dataclasses import dataclass
from .impact_to_coevolution import CoEvolutionPlan
from .specialized_mutations import EngineeringMutationSpec


@dataclass(frozen=True)
class PlannedDomainWork:
    domain: str
    mutation_id: str
    required_properties: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class ExecutableCoEvolutionWork:
    source_domain: str
    work: tuple[PlannedDomainWork, ...]
    evidence: tuple[str, ...]
    uncertain: bool


def materialize_coevolution_work(
    plan: CoEvolutionPlan,
    mutation_specs: tuple[EngineeringMutationSpec, ...],
) -> ExecutableCoEvolutionWork:
    by_domain = {s.mutation.request.domain: s for s in mutation_specs}
    work = []
    for domain_plan in plan.domains:
        spec = by_domain.get(domain_plan.domain)
        if spec is None:
            raise ValueError("missing-domain-mutation:" + domain_plan.domain)
        actual = set(spec.verification_properties)
        required = set(domain_plan.required_properties)
        missing = required - actual
        if missing:
            raise ValueError(
                "mutation-missing-verification-properties:" +
                domain_plan.domain + ":" + ",".join(sorted(missing))
            )
        work.append(
            PlannedDomainWork(
                domain_plan.domain,
                spec.mutation.mutation_id,
                domain_plan.required_properties,
                domain_plan.reason,
            )
        )
    return ExecutableCoEvolutionWork(
        plan.source_domain,
        tuple(work),
        plan.impact_evidence,
        not plan.impact_complete,
    )
