"""Resolve required mutation domains for governed Bucket 2 work modes."""

from __future__ import annotations

from .work_mode import WorkMode
from .work_capability import WorkCapabilityContract

_MODE_DOMAIN = {
    WorkMode.DOCUMENT: "documentation",
    WorkMode.TEST: "testing",
    WorkMode.ARCHITECTURE: "architecture",
    WorkMode.MIGRATE: "migration",
    WorkMode.REFACTOR: "refactor",
}


def required_mutation_domain(contract: WorkCapabilityContract) -> str | None:
    return _MODE_DOMAIN.get(contract.mode.mode)


def validate_mutation_domains(contract: WorkCapabilityContract, domains: tuple[str, ...]) -> None:
    required = required_mutation_domain(contract)
    if required is not None and required not in domains:
        raise ValueError(f"missing-required-mutation-domain:{required}")
