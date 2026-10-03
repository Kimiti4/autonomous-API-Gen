"""Evidence-backed architectural memory and lineage."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ArchitectureMemory:
    memory_id: str
    problem_signature: str
    hypothesis: str
    domains: tuple[str, ...]
    changes: tuple[str, ...]
    outcome: str
    properties: tuple[str, ...]
    evidence: tuple[str, ...]
    parent_memory_ids: tuple[str, ...] = ()
    confidence: str = "bounded"


@dataclass(frozen=True)
class MemoryQuery:
    problem_signature: str
    domains: tuple[str, ...] = ()


@dataclass(frozen=True)
class MemoryIndex:
    memories: tuple[ArchitectureMemory, ...] = ()


def record_memory(
    memory_id: str,
    problem_signature: str,
    hypothesis: str,
    domains: tuple[str, ...],
    changes: tuple[str, ...],
    outcome: str,
    properties: tuple[str, ...],
    evidence: tuple[str, ...],
    parent_memory_ids: tuple[str, ...] = (),
    confidence: str = "bounded",
) -> ArchitectureMemory:
    if not evidence:
        raise ValueError("architectural-memory-requires-evidence")
    if outcome not in {"success", "failure", "bounded", "regression"}:
        raise ValueError("invalid-memory-outcome")
    return ArchitectureMemory(
        memory_id, problem_signature, hypothesis, domains, changes,
        outcome, properties, evidence, parent_memory_ids, confidence
    )


def index_memory(index: MemoryIndex, memory: ArchitectureMemory) -> MemoryIndex:
    if any(m.memory_id == memory.memory_id for m in index.memories):
        raise ValueError("duplicate-memory-id")
    return MemoryIndex(index.memories + (memory,))


def retrieve_memory(
    index: MemoryIndex,
    query: MemoryQuery,
) -> tuple[ArchitectureMemory, ...]:
    matches = []
    for memory in index.memories:
        if memory.problem_signature != query.problem_signature:
            continue
        if query.domains and not set(query.domains).intersection(memory.domains):
            continue
        matches.append(memory)
    return tuple(matches)


def promote_confidence(
    memory: ArchitectureMemory,
    additional_evidence: tuple[str, ...],
    new_confidence: str,
) -> ArchitectureMemory:
    if not additional_evidence:
        raise ValueError("promotion-requires-new-evidence")
    return ArchitectureMemory(
        **{
            **memory.__dict__,
            "evidence": tuple(sorted(set(memory.evidence) | set(additional_evidence))),
            "confidence": new_confidence,
        }
    )
