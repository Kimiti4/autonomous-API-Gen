"""Turn failed co-evolution verification into bounded repair candidates."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any

from .architecture_mutation import execute_mutation
from .cross_domain_evolution import CoEvolutionResult
from .evolution_population import EvolutionMember
from .fullstack_genome import FullStackGenome
from .specialized_mutations import EngineeringMutationSpec
from .verification_plans import VerificationReport, build_verification_plan, execute_verification


@dataclass(frozen=True)
class Counterexample:
    mutation_id: str
    domain: str
    failed_properties: tuple[str, ...]
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class RepairCandidate:
    source_mutation_id: str
    repair_mutation_id: str
    domain: str
    rationale: str
    counterexample_properties: tuple[str, ...]


@dataclass(frozen=True)
class RepairExecution:
    candidate: RepairCandidate
    architecture: FullStackGenome
    verification: VerificationReport


@dataclass(frozen=True)
class RepairResult:
    source_event_id: str
    source_architecture_id: str
    counterexamples: tuple[Counterexample, ...]
    repairs: tuple[RepairExecution, ...]
    passed: bool


def extract_counterexamples(result: CoEvolutionResult) -> tuple[Counterexample, ...]:
    """Extract only failed required gates; passing work produces no repair demand."""
    by_id = {c.mutation_id: c for c in result.event.changes}
    out = []
    for report in result.reports:
        failed = tuple(r.property_name for r in report.results if not r.passed)
        if not failed:
            continue
        change = by_id.get(report.mutation_id)
        if change is None:
            raise ValueError("verification-report-not-in-event:" + report.mutation_id)
        evidence = tuple(
            e for r in report.results if not r.passed for e in r.evidence
        )
        out.append(
            Counterexample(
                report.mutation_id,
                next(
                    c.domain for c in result.event.changes
                    if c.mutation_id == report.mutation_id
                ),
                failed,
                tuple(sorted(set(evidence))),
            )
        )
    return tuple(out)


def build_repair_candidates(
    result: CoEvolutionResult,
    repair_specs: tuple[EngineeringMutationSpec, ...],
) -> tuple[RepairCandidate, ...]:
    counterexamples = extract_counterexamples(result)
    specs_by_id = {s.mutation.mutation_id: s for s in repair_specs}
    candidates = []
    for counterexample in counterexamples:
        spec = specs_by_id.get(counterexample.mutation_id)
        if spec is None:
            # A repair is intentionally not guessed: missing repair operators are
            # surfaced as an explicit bounded residual.
            continue
        candidates.append(
            RepairCandidate(
                counterexample.mutation_id,
                spec.mutation.mutation_id,
                spec.mutation.request.domain,
                spec.mutation.request.rationale,
                counterexample.failed_properties,
            )
        )
    return tuple(candidates)


def execute_repairs(
    result: CoEvolutionResult,
    source: EvolutionMember,
    genome: FullStackGenome,
    repair_specs: tuple[EngineeringMutationSpec, ...],
    verifiers: Mapping[str, Any],
    observations: Mapping[str, Any],
    evidence_by_property: Mapping[str, tuple[str, ...]],
    *,
    contracts_by_domain: Mapping[str, tuple[Any, ...]] | None = None,
) -> RepairResult:
    del source
    counterexamples = extract_counterexamples(result)
    candidates = build_repair_candidates(result, repair_specs)
    candidate_by_source = {c.source_mutation_id: c for c in candidates}
    current = genome
    executions = []

    for cx in counterexamples:
        candidate = candidate_by_source.get(cx.mutation_id)
        if candidate is None:
            raise ValueError("missing-repair-mutation:" + cx.domain + ":" + ",".join(cx.failed_properties))
        spec = next(
            s for s in repair_specs
            if s.mutation.mutation_id == candidate.repair_mutation_id
        )
        contracts = () if contracts_by_domain is None else contracts_by_domain.get(candidate.domain, ())
        evaluation = execute_mutation(current, spec.mutation, tuple(contracts), dict(observations))
        current = evaluation.genome
        plan = build_verification_plan(spec, verifiers)
        evidence_by_gate = {
            f"{candidate.domain}:{p}": tuple(evidence_by_property.get(p, ()))
            for p in spec.verification_properties
        }
        report = execute_verification(plan, observations, evidence_by_gate)
        executions.append(RepairExecution(candidate, current, report))

    return RepairResult(
        result.event.event_id,
        result.event.source_architecture_id,
        counterexamples,
        tuple(executions),
        bool(executions) and all(r.verification.passed for r in executions),
    )
