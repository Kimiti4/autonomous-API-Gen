"""Resolve concrete Bucket 2 capability mutation factories."""

from __future__ import annotations

from collections.abc import Callable

from .mode_capability_mutations import cross_stack_mutation, generate_mutation, improve_mutation, maintain_mutation, seo_mutation
from .specialized_capability_mutations import architecture_mutation, documentation_mutation, migration_mutation, refactor_mutation, test_mutation
from .work_mode import WorkMode
from .work_capability import WorkCapabilityContract

_MODE_FACTORY = {
    WorkMode.GENERATE: generate_mutation, WorkMode.MAINTAIN: maintain_mutation,
    WorkMode.IMPROVE: improve_mutation, WorkMode.DOCUMENT: documentation_mutation,
    WorkMode.SEO: seo_mutation, WorkMode.TEST: test_mutation,
    WorkMode.ARCHITECTURE: architecture_mutation, WorkMode.MIGRATE: migration_mutation,
    WorkMode.REFACTOR: refactor_mutation, WorkMode.CROSS_STACK: cross_stack_mutation,
}
_MODE_DOMAIN = {
    WorkMode.GENERATE: "generate", WorkMode.MAINTAIN: "maintain", WorkMode.IMPROVE: "improve",
    WorkMode.DOCUMENT: "documentation", WorkMode.SEO: "seo", WorkMode.TEST: "testing",
    WorkMode.ARCHITECTURE: "architecture", WorkMode.MIGRATE: "migration",
    WorkMode.REFACTOR: "refactor", WorkMode.CROSS_STACK: "crossstack",
}


def required_mutation_domain(contract: WorkCapabilityContract) -> str | None:
    return _MODE_DOMAIN.get(contract.mode.mode)


def resolve_mutation_factory(contract: WorkCapabilityContract) -> Callable:
    try:
        return _MODE_FACTORY[contract.mode.mode]
    except KeyError as exc:
        raise ValueError(f"missing-capability-mutation-factory:{contract.mode.mode.value}") from exc


def validate_mutation_domains(contract: WorkCapabilityContract, domains: tuple[str, ...]) -> None:
    required = required_mutation_domain(contract)
    if required is not None and required not in domains:
        raise ValueError(f"missing-required-mutation-domain:{required}")
