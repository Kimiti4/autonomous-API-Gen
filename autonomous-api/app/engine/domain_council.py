"""Domain engineering councils over shared architectural memory."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping
from .architectural_memory import ArchitectureMemory, MemoryIndex, MemoryQuery, retrieve_memory


@dataclass(frozen=True)
class DomainReview:
    domain: str
    memory_ids: tuple[str, ...]
    concerns: tuple[str, ...]
    corrections: tuple[str, ...]
    supporting_evidence: tuple[str, ...]


@dataclass(frozen=True)
class EngineeringCouncilReview:
    reviews: tuple[DomainReview, ...]
    shared_memory_ids: tuple[str, ...]


def review_domain(
    domain: str,
    problem_signature: str,
    index: MemoryIndex,
) -> DomainReview:
    memories = retrieve_memory(index, MemoryQuery(problem_signature, (domain,)))
    concerns: list[str] = []
    corrections: list[str] = []
    evidence: set[str] = set()

    for memory in memories:
        evidence.update(memory.evidence)
        if memory.outcome in {"failure", "regression"}:
            concerns.append(
                f"{memory.memory_id}:previous-{memory.outcome}"
            )
            corrections.append(
                f"reconsider:{memory.hypothesis}"
            )

    return DomainReview(
        domain=domain,
        memory_ids=tuple(m.memory_id for m in memories),
        concerns=tuple(sorted(concerns)),
        corrections=tuple(sorted(corrections)),
        supporting_evidence=tuple(sorted(evidence)),
    )


def review_across_domains(
    problem_signature: str,
    domains: tuple[str, ...],
    index: MemoryIndex,
) -> EngineeringCouncilReview:
    reviews = tuple(
        review_domain(domain, problem_signature, index)
        for domain in domains
    )
    shared = tuple(sorted({
        memory_id
        for review in reviews
        for memory_id in review.memory_ids
    }))
    return EngineeringCouncilReview(reviews, shared)
