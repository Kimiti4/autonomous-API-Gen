"""Domain-aware mutation guards for full-stack evolution."""
from __future__ import annotations
from dataclasses import dataclass
from .fullstack_genome import FullStackGenome
from .fullstack_mutation import compatibility_errors


@dataclass(frozen=True)
class MutationRequest:
    domain: str
    paths: tuple[str, ...]
    rationale: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class MutationResult:
    parent_id: str
    domain: str
    changed_paths: tuple[str, ...]
    genome: FullStackGenome


_ALLOWED = {
    "frontend": ("frontend.",),
    "backend": ("backend.",),
    "data": ("data.",),
    "security": ("security.",),
    "operations": ("operations.",),
    "fullstack": ("frontend.", "backend.", "data.", "security.", "operations."),
    "documentation": ("documentation.", "docs.", "x"),
    "testing": ("testing.", "tests.", "x"),
    "architecture": ("architecture.", "x"),
    "migration": ("migration.", "data.", "x"),
    "refactor": ("refactor.", "x"),
    "generate": ("generate.", "x"),
    "maintain": ("maintain.", "x"),
    "improve": ("improve.", "x"),
    "seo": ("seo.", "x"),
    "crossstack": ("crossstack.", "x"),
}


def validate_mutation_request(request: MutationRequest) -> None:
    if request.domain not in _ALLOWED:
        raise ValueError("unknown-mutation-domain")
    if not request.paths:
        raise ValueError("mutation-requires-target-paths")
    if not request.evidence:
        raise ValueError("mutation-requires-evidence")
    prefixes = _ALLOWED[request.domain]
    if not all(any(path.startswith(prefix) for prefix in prefixes)
               for path in request.paths):
        raise ValueError("mutation-crosses-domain-boundary")


def apply_domain_mutation(
    parent_id: str,
    genome: FullStackGenome,
    request: MutationRequest,
    mutate,
) -> MutationResult:
    validate_mutation_request(request)
    candidate = mutate(genome, request)
    errors = compatibility_errors(candidate)
    if errors:
        raise ValueError("invalid-domain-mutation:" + ";".join(errors))
    return MutationResult(parent_id, request.domain, request.paths, candidate)
