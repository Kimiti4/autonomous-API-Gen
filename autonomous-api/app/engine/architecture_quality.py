"""Architecture candidate evaluation against engineering quality obligations."""
from __future__ import annotations
from dataclasses import dataclass
from .engineering_deliberation import ArchitectureAlternative
from .quality_profiles import EngineeringQualityProfile


@dataclass(frozen=True)
class CandidateQualityEvaluation:
    alternative_id: str
    satisfied: tuple[str, ...]
    missing: tuple[str, ...]
    risks: tuple[str, ...]


def evaluate_candidate(
    candidate: ArchitectureAlternative,
    profile: EngineeringQualityProfile,
) -> CandidateQualityEvaluation:
    corpus = " ".join((candidate.summary, *candidate.benefits, *candidate.costs, *candidate.risks, *candidate.assumptions)).lower()
    terms = {
        "correctness": ("correct", "invariant", "consistency"),
        "accessibility": ("accessib", "a11y"),
        "performance": ("performance", "latency", "throughput", "cache"),
        "security": ("security", "authorization", "authentication", "trust"),
        "resilience": ("resilien", "failure", "retry", "recovery"),
        "testability": ("test", "verification"),
        "maintainability": ("maintain", "modular", "evolve"),
        "usability": ("user", "ux", "interaction"),
        "domain": ("domain", "business", "invariant"),
        "data": ("data", "database", "transaction", "integrity"),
        "api": ("api", "contract"),
        "reliability": ("reliab", "failure", "recovery"),
        "observability": ("observ", "trace", "metric", "log"),
        "operability": ("operat", "health", "configuration"),
        "system flow": ("flow", "end-to-end", "e2e"),
        "contracts": ("contract", "api"),
        "data integrity": ("data", "integrity", "effect"),
        "delivery": ("deploy", "delivery", "build"),
        "evolution": ("evolut", "regression", "change"),
    }
    satisfied, missing = [], []
    for obligation in profile.obligations:
        tokens = terms.get(obligation.domain, (obligation.domain,))
        if any(token in corpus for token in tokens):
            satisfied.append(obligation.obligation_id)
        else:
            missing.append(obligation.obligation_id)
    return CandidateQualityEvaluation(
        candidate.alternative_id, tuple(satisfied), tuple(missing), candidate.risks
    )


def evaluate_candidates(
    candidates: tuple[ArchitectureAlternative, ...],
    profile: EngineeringQualityProfile,
) -> tuple[CandidateQualityEvaluation, ...]:
    return tuple(evaluate_candidate(c, profile) for c in candidates)
