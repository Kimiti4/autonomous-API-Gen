"""Adversarial engineering challenge model for architecture alternatives."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Challenge:
    challenge_id: str
    challenger: str
    target: str
    claim: str
    counterexample: str
    stress_scenario: str
    expected_property: str


@dataclass(frozen=True)
class ChallengeResult:
    challenge_id: str
    status: str
    evidence_id: str
    observation: str


@dataclass(frozen=True)
class Deliberation:
    deliberation_id: str
    alternatives: tuple[str, ...]
    challenges: tuple[Challenge, ...]
    results: tuple[ChallengeResult, ...]
    unresolved: tuple[str, ...]


def generate_challenges(
    alternatives: tuple[str, ...],
    claims: dict[str, tuple[str, ...]],
) -> tuple[Challenge, ...]:
    out: list[Challenge] = []
    for challenger in alternatives:
        for target in alternatives:
            if challenger == target:
                continue
            for i, claim in enumerate(claims.get(target, ())):
                out.append(Challenge(
                    challenge_id=f"CH-{challenger}-{target}-{i}",
                    challenger=challenger,
                    target=target,
                    claim=claim,
                    counterexample=f"find a case where {claim} does not hold",
                    stress_scenario=f"stress {claim} under failure, concurrency, scale, and adversarial input",
                    expected_property=f"provide evidence that {claim} remains valid",
                ))
    return tuple(out)


def record_challenge(
    challenge: Challenge,
    status: str,
    evidence_id: str,
    observation: str,
) -> ChallengeResult:
    if status not in {"supported", "refuted", "inconclusive"}:
        raise ValueError("invalid challenge status")
    if not evidence_id:
        raise ValueError("challenge result requires evidence")
    return ChallengeResult(challenge.challenge_id, status, evidence_id, observation)


def build_deliberation(
    deliberation_id: str,
    alternatives: tuple[str, ...],
    challenges: tuple[Challenge, ...],
    results: tuple[ChallengeResult, ...],
) -> Deliberation:
    result_ids = {r.challenge_id for r in results}
    unresolved = tuple(
        c.challenge_id for c in challenges
        if c.challenge_id not in result_ids
        or next(r for r in results if r.challenge_id == c.challenge_id).status == "inconclusive"
    )
    return Deliberation(deliberation_id, alternatives, challenges, results, unresolved)
