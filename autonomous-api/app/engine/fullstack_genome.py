from .pareto_architecture import Objective
"""Technology-neutral full-stack genome for evolutionary software architecture."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class FrontendGenome:
    rendering_model: str
    state_model: str
    interaction_model: str
    accessibility_strategy: str
    resilience_strategy: str

    @property
    def framework(self) -> str:
        return self.rendering_model


@dataclass(frozen=True)
class BackendGenome:
    service_model: str
    consistency_model: str
    concurrency_model: str
    resilience_strategy: str
    contract_strategy: str

    @property
    def framework(self) -> str:
        return self.service_model


@dataclass(frozen=True)
class DataGenome:
    persistence_model: str
    integrity_strategy: str
    migration_strategy: str
    consistency_model: str


@dataclass(frozen=True)
class SecurityGenome:
    authentication_model: str
    authorization_model: str
    trust_boundaries: tuple[str, ...]
    threat_controls: tuple[str, ...]
    secret_handling: str

    @property
    def threat_model(self) -> str:
        return self.threat_controls[0] if self.threat_controls else ""


@dataclass(frozen=True)
class OperationalGenome:
    deployment_model: str
    observability_model: str
    rollback_strategy: str
    resource_strategy: str


@dataclass(frozen=True)
class FullStackGenome:
    frontend: FrontendGenome
    backend: BackendGenome
    data: DataGenome
    security: SecurityGenome
    operations: OperationalGenome
    api_contract: str
    state_flow: str
    constraints: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, str] = field(default_factory=dict)


def genome_domains(genome: FullStackGenome) -> tuple[str, ...]:
    return ("frontend", "backend", "data", "security", "operations")


def validate_genome(genome: FullStackGenome) -> tuple[str, ...]:
    errors: list[str] = []
    required = {
        "frontend.rendering_model": genome.frontend.rendering_model,
        "frontend.state_model": genome.frontend.state_model,
        "backend.service_model": genome.backend.service_model,
        "backend.contract_strategy": genome.backend.contract_strategy,
        "data.persistence_model": genome.data.persistence_model,
        "security.authentication_model": genome.security.authentication_model,
        "security.authorization_model": genome.security.authorization_model,
        "operations.deployment_model": genome.operations.deployment_model,
        "api_contract": genome.api_contract,
        "state_flow": genome.state_flow,
    }
    errors.extend(f"missing:{key}" for key, value in required.items() if not value)
    if not genome.security.trust_boundaries:
        errors.append("missing:security.trust_boundaries")
    return tuple(errors)
