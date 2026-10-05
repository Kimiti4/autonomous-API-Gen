"""Concrete architecture mutation operators with domain and invariant gates."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
from .fullstack_genome import FullStackGenome
from .domain_mutation import MutationRequest, validate_mutation_request
from .invariant_contracts import InvariantContract, evaluate_contract, require_contract_pass


@dataclass(frozen=True)
class ArchitectureMutation:
    mutation_id: str
    request: MutationRequest
    apply: Callable[[FullStackGenome], FullStackGenome]

    @property
    def domain(self) -> str:
        return self.request.domain


@dataclass(frozen=True)
class MutationEvaluation:
    mutation_id: str
    domain: str
    genome: FullStackGenome
    invariant_results: tuple
    evidence: tuple[str, ...]


def execute_mutation(
    genome: FullStackGenome,
    mutation: ArchitectureMutation,
    contracts: tuple[InvariantContract, ...],
    observations: dict[str, object],
) -> MutationEvaluation:
    validate_mutation_request(mutation.request)
    candidate = mutation.apply(genome)
    all_results = []
    for contract in contracts:
        results = evaluate_contract(contract, observations)
        require_contract_pass(results)
        all_results.extend(results)
    if not mutation.request.evidence:
        raise ValueError("mutation-requires-evidence")
    return MutationEvaluation(
        mutation.mutation_id,
        mutation.request.domain,
        candidate,
        tuple(all_results),
        mutation.request.evidence,
    )


def domain_operator(
    mutation_id: str,
    domain: str,
    paths: tuple[str, ...],
    rationale: str,
    evidence: tuple[str, ...],
    operator: Callable[[FullStackGenome], FullStackGenome],
) -> ArchitectureMutation:
    request = MutationRequest(domain, paths, rationale, evidence)
    validate_mutation_request(request)
    return ArchitectureMutation(mutation_id, request, operator)
