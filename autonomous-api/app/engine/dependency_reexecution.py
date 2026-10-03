"""Execute dependency-aware downstream re-verification after repair."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any, Sequence

from .architecture_mutation import execute_mutation
from .cross_domain_evolution import CoEvolutionResult
from .fullstack_genome import FullStackGenome
from .repair_coevolution import RepairExecution, extract_counterexamples
from .repair_closure import SuccessorDomainVerification, close_repair_and_dependencies
from .specialized_mutations import EngineeringMutationSpec
from .verification_plans import VerificationReport, build_verification_plan, execute_verification


@dataclass(frozen=True)
class DependentDomainExecution:
    domain: str
    mutation_id: str
    architecture: FullStackGenome
    verification: VerificationReport


@dataclass(frozen=True)
class DependencyExecutionResult:
    executions: tuple[DependentDomainExecution, ...]
    final_architecture: FullStackGenome
    closure: object


def _downstream(
    failed_domains: set[str],
    graph: Mapping[str, Sequence[str]],
) -> tuple[str, ...]:
    seen = set(failed_domains)
    queue = list(sorted(failed_domains))
    while queue:
        source = queue.pop(0)
        for target in graph.get(source, ()):
            if target not in seen:
                seen.add(target)
                queue.append(target)
    # Failed domains are repaired separately; only their downstream dependants
    # are re-executed here.
    return tuple(sorted(seen - failed_domains))


def execute_dependent_reverification(
    result: CoEvolutionResult,
    repairs: tuple[RepairExecution, ...],
    dependency_graph: Mapping[str, Sequence[str]],
    mutation_specs: tuple[EngineeringMutationSpec, ...],
    verifiers: Mapping[str, Any],
    observations: Mapping[str, Any],
    evidence_by_property: Mapping[str, tuple[str, ...]],
    *,
    successor_architecture_id: str,
) -> DependencyExecutionResult:
    """Re-execute every downstream domain invalidated by a failed repair.

    The repaired architecture is the input to downstream work. No previously
    recorded verification report is accepted as a substitute for execution.
    """
    counterexamples = extract_counterexamples(result)
    failed_domains = {cx.domain for cx in counterexamples}
    domains = _downstream(failed_domains, dependency_graph)

    if not failed_domains:
        raise ValueError("dependency-reverification-requires-counterexample")

    if not repairs:
        raise ValueError("dependency-reverification-requires-repair")

    repair_domains = {r.candidate.domain for r in repairs}
    missing = failed_domains - repair_domains
    if missing:
        raise ValueError("unrepaired-domain:" + ",".join(sorted(missing)))

    current = repairs[-1].architecture
    specs_by_domain = {s.mutation.request.domain: s for s in mutation_specs}
    executions = []

    for domain in domains:
        spec = specs_by_domain.get(domain)
        if spec is None:
            raise ValueError("missing-dependent-mutation:" + domain)

        mutation_evaluation = execute_mutation(
            current,
            spec.mutation,
            tuple(),
            dict(observations),
        )
        current = mutation_evaluation.genome

        plan = build_verification_plan(spec, verifiers)
        evidence_by_gate = {}
        for property_name in spec.verification_properties:
            evidence = tuple(evidence_by_property.get(property_name, ()))
            if not evidence:
                raise ValueError(
                    "missing-verification-evidence:" + domain + ":" + property_name
                )
            evidence_by_gate[f"{domain}:{property_name}"] = evidence

        report = execute_verification(plan, observations, evidence_by_gate)
        executions.append(
            DependentDomainExecution(
                domain,
                spec.mutation.mutation_id,
                current,
                report,
            )
        )

    reports = tuple(
        SuccessorDomainVerification(x.domain, x.mutation_id, x.verification)
        for x in executions
    )
    closure = close_repair_and_dependencies(
        result,
        repairs,
        dependency_graph,
        reports,
        successor_architecture_id=successor_architecture_id,
    )

    return DependencyExecutionResult(tuple(executions), current, closure)
