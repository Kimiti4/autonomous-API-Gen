"""Coordinate evidence-backed cross-domain co-evolution."""
from __future__ import annotations
from dataclasses import dataclass
from .evolution_population import EvolutionMember
from .specialized_mutations import EngineeringMutationSpec
from .verification_plans import VerificationReport


@dataclass(frozen=True)
class DomainChange:
    domain: str
    mutation_id: str
    verification_properties: tuple[str, ...]


@dataclass(frozen=True)
class CoEvolutionEvent:
    event_id: str
    source_architecture_id: str
    changes: tuple[DomainChange, ...]
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class CoEvolutionResult:
    event: CoEvolutionEvent
    architecture_id: str
    reports: tuple[VerificationReport, ...]
    passed: bool


def create_coevolution_event(
    event_id: str,
    source: EvolutionMember,
    specs: tuple[EngineeringMutationSpec, ...],
    evidence: tuple[str, ...],
) -> CoEvolutionEvent:
    if not specs:
        raise ValueError("coevolution-requires-domain-changes")
    if not evidence:
        raise ValueError("coevolution-requires-evidence")
    changes = tuple(
        DomainChange(
            s.mutation.request.domain,
            s.mutation.mutation_id,
            s.verification_properties,
        )
        for s in specs
    )
    domains = [c.domain for c in changes]
    if len(domains) != len(set(domains)):
        raise ValueError("coevolution-duplicate-domain")
    return CoEvolutionEvent(
        event_id,
        source.lineage.architecture_id,
        changes,
        tuple(sorted(set(evidence))),
    )


def complete_coevolution(
    event: CoEvolutionEvent,
    architecture_id: str,
    reports: tuple[VerificationReport, ...],
) -> CoEvolutionResult:
    expected = {c.mutation_id for c in event.changes}
    actual = {r.mutation_id for r in reports}
    missing = expected - actual
    if missing:
        raise ValueError("missing-domain-verification:" + ",".join(sorted(missing)))
    passed = all(r.passed for r in reports)
    return CoEvolutionResult(event, architecture_id, reports, passed)
