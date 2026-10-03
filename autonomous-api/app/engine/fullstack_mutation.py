"""Constrained mutation and recombination for full-stack genomes."""
from __future__ import annotations
from dataclasses import replace
from .fullstack_genome import (
    FullStackGenome, FrontendGenome, BackendGenome, DataGenome,
    SecurityGenome, OperationalGenome, validate_genome,
)


def mutate_frontend(genome: FullStackGenome, **changes: str) -> FullStackGenome:
    return replace(genome, frontend=replace(genome.frontend, **changes))


def mutate_backend(genome: FullStackGenome, **changes: str) -> FullStackGenome:
    return replace(genome, backend=replace(genome.backend, **changes))


def mutate_data(genome: FullStackGenome, **changes: str) -> FullStackGenome:
    return replace(genome, data=replace(genome.data, **changes))


def mutate_security(genome: FullStackGenome, **changes: object) -> FullStackGenome:
    return replace(genome, security=replace(genome.security, **changes))


def mutate_operations(genome: FullStackGenome, **changes: str) -> FullStackGenome:
    return replace(genome, operations=replace(genome.operations, **changes))


def recombine(a: FullStackGenome, b: FullStackGenome) -> FullStackGenome:
    """Domain-wise crossover; shared contracts/flows are retained from parent a."""
    return FullStackGenome(
        frontend=a.frontend,
        backend=b.backend,
        data=a.data,
        security=b.security,
        operations=a.operations,
        api_contract=a.api_contract,
        state_flow=a.state_flow,
        constraints=tuple(sorted(set(a.constraints) | set(b.constraints))),
        metadata={**b.metadata, **a.metadata},
    )


def compatibility_errors(genome: FullStackGenome) -> tuple[str, ...]:
    errors = list(validate_genome(genome))
    if genome.backend.contract_strategy == "versioned" and not genome.api_contract:
        errors.append("contract-strategy-requires-api-contract")
    if genome.security.authorization_model and not genome.security.trust_boundaries:
        errors.append("authorization-requires-trust-boundaries")
    if genome.frontend.state_model and not genome.state_flow:
        errors.append("frontend-state-model-requires-state-flow")
    return tuple(dict.fromkeys(errors))


def safe_mutation(genome: FullStackGenome, domain: str, changes: dict[str, object]) -> FullStackGenome:
    if domain == "frontend":
        candidate = mutate_frontend(genome, **changes)
    elif domain == "backend":
        candidate = mutate_backend(genome, **changes)
    elif domain == "data":
        candidate = mutate_data(genome, **changes)
    elif domain == "security":
        candidate = mutate_security(genome, **changes)
    elif domain == "operations":
        candidate = mutate_operations(genome, **changes)
    else:
        raise ValueError(f"unknown-domain:{domain}")
    errors = compatibility_errors(candidate)
    if errors:
        raise ValueError("incompatible-genome:" + ";".join(errors))
    return candidate
