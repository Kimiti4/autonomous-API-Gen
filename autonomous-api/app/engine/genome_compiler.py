"""Compile synthesized domain proposals into validated full-stack genomes."""
from __future__ import annotations
from dataclasses import dataclass
from .synthesis import SynthesizedProposal, synthesis_ready
from .fullstack_genome import (
    FullStackGenome, FrontendGenome, BackendGenome, DataGenome,
    SecurityGenome, OperationalGenome,
)
from .fullstack_mutation import compatibility_errors


@dataclass(frozen=True)
class GenomeCompilation:
    proposal_id: str
    genome: FullStackGenome
    source_proposal_ids: tuple[str, ...]
    source_rebuttal_ids: tuple[str, ...]


def _pick(changes: tuple[str, ...], prefix: str, fallback: str) -> str:
    matches = tuple(x for x in changes if x.startswith(prefix))
    return matches[0] if matches else fallback


def compile_synthesis(proposal: SynthesizedProposal) -> GenomeCompilation:
    if not synthesis_ready(proposal):
        raise ValueError("synthesis-not-ready")

    changes = proposal.changes
    frontend = FrontendGenome(
        _pick(changes, "frontend-", "derived"),
        _pick(changes, "frontend-", "derived"),
        "evidence-backed",
        "contract-driven",
        "accessible",
    )
    backend = BackendGenome(
        _pick(changes, "backend-", "derived"),
        _pick(changes, "backend-", "derived"),
        "validated",
        "observable",
        "resilient",
    )
    data = DataGenome(
        _pick(changes, "data-", "derived"),
        "integrity-first",
        "versioned",
        "traceable",
    )
    security = SecurityGenome(
        _pick(changes, "security-", "derived"),
        "least-privilege",
        tuple(sorted(proposal.target_properties)),
        ("evidence-gated",),
        "auditable",
    )
    operations = OperationalGenome(
        _pick(changes, "operations-", "derived"),
        "observable",
        "recoverable",
        "controlled",
    )
    genome = FullStackGenome(
        frontend, backend, data, security, operations,
        proposal.problem_signature,
        proposal.claim,
    )
    errors = compatibility_errors(genome)
    if errors:
        raise ValueError("compiled-genome-incompatible:" + ";".join(errors))
    return GenomeCompilation(
        proposal.proposal_id,
        genome,
        proposal.source_proposal_ids,
        proposal.source_rebuttal_ids,
    )
