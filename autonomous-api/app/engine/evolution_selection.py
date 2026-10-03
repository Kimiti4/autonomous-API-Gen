"""Evidence-driven composition and comparison of engineering candidates."""
from __future__ import annotations
from dataclasses import dataclass
from .evolution_domains import EngineeringCandidate


@dataclass(frozen=True)
class CandidateAssessment:
    candidate_id: str
    verified_properties: tuple[str, ...]
    failed_properties: tuple[str, ...]
    evidence: tuple[str, ...]
    risk_flags: tuple[str, ...] = ()

    @property
    def viable(self) -> bool:
        return bool(self.evidence) and not self.failed_properties


@dataclass(frozen=True)
class CandidateComposition:
    composition_id: str
    candidate_ids: tuple[str, ...]
    domains: tuple[str, ...]
    conflicts: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class EvolutionOption:
    option_id: str
    candidate_ids: tuple[str, ...]
    domains: tuple[str, ...]
    covered_properties: tuple[str, ...]
    evidence: tuple[str, ...]
    risks: tuple[str, ...]

    @property
    def eligible_for_governance(self) -> bool:
        return bool(self.evidence) and not self.risks


def assess_candidate(
    candidate: EngineeringCandidate,
    verified_properties: tuple[str, ...],
    failed_properties: tuple[str, ...],
    evidence: tuple[str, ...],
) -> CandidateAssessment:
    return CandidateAssessment(
        candidate.candidate_id,
        verified_properties,
        failed_properties,
        evidence,
        candidate.risks,
    )


def compose_candidates(
    candidates: tuple[EngineeringCandidate, ...],
) -> CandidateComposition:
    ids = tuple(c.candidate_id for c in candidates)
    domains = tuple(sorted({c.domain for c in candidates}))
    risks = []
    for i, left in enumerate(candidates):
        for right in candidates[i + 1:]:
            overlap = set(left.changes) & set(right.changes)
            if overlap:
                risks.append(
                    f"overlapping-change:{left.candidate_id}:{right.candidate_id}"
                )
    return CandidateComposition(
        ":".join(ids),
        ids,
        domains,
        tuple(risks),
        "coordinated candidate set requires joint verification",
    )


def build_options(
    candidates: tuple[EngineeringCandidate, ...],
    assessments: tuple[CandidateAssessment, ...],
) -> tuple[EvolutionOption, ...]:
    by_id = {a.candidate_id: a for a in assessments}
    options = []
    for c in candidates:
        a = by_id.get(c.candidate_id)
        if a is None:
            continue
        options.append(EvolutionOption(
            c.candidate_id,
            (c.candidate_id,),
            (c.domain,),
            a.verified_properties,
            a.evidence,
            tuple(c.risks) + a.risk_flags,
        ))

    # Coordinated option: only construct it from independently assessed candidates.
    if len(candidates) > 1 and all(
        by_id.get(c.candidate_id) and by_id[c.candidate_id].viable
        for c in candidates
    ):
        composed = compose_candidates(candidates)
        covered = tuple(sorted({
            p for c in candidates
            for p in by_id[c.candidate_id].verified_properties
        }))
        evidence = tuple(sorted({
            e for c in candidates
            for e in by_id[c.candidate_id].evidence
        }))
        options.append(EvolutionOption(
            composed.composition_id,
            composed.candidate_ids,
            composed.domains,
            covered,
            evidence,
            composed.conflicts,
        ))
    return tuple(options)
