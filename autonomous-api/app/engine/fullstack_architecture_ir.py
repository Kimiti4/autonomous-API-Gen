"""Technology-neutral full-stack architecture projection boundary.

The architecture model is shared; frontend and backend projections are
independent implementation plans and cannot mutate the source architecture.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureComponent:
    component_id: str
    role: str
    responsibilities: tuple[str, ...] = ()


@dataclass(frozen=True)
class FullStackArchitectureIR:
    architecture_id: str
    components: tuple[ArchitectureComponent, ...]
    contracts: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()


@dataclass(frozen=True)
class FrontendArchitectureIR:
    architecture_id: str
    components: tuple[ArchitectureComponent, ...]
    contracts_consumed: tuple[str, ...]
    invariants_preserved: tuple[str, ...]


@dataclass(frozen=True)
class BackendArchitectureIR:
    architecture_id: str
    components: tuple[ArchitectureComponent, ...]
    contracts_exposed: tuple[str, ...]
    invariants_preserved: tuple[str, ...]


def project_frontend(source: FullStackArchitectureIR) -> FrontendArchitectureIR:
    components = tuple(c for c in source.components if c.role in {
        "frontend", "presentation", "client"
    })
    return FrontendArchitectureIR(
        source.architecture_id, components, source.contracts, source.invariants
    )


def project_backend(source: FullStackArchitectureIR) -> BackendArchitectureIR:
    components = tuple(c for c in source.components if c.role in {
        "backend", "service", "persistence", "integration"
    })
    return BackendArchitectureIR(
        source.architecture_id, components, source.contracts, source.invariants
    )


def assert_projection_consistency(
    source: FullStackArchitectureIR,
    frontend: FrontendArchitectureIR,
    backend: BackendArchitectureIR,
) -> bool:
    if frontend.architecture_id != source.architecture_id:
        return False
    if backend.architecture_id != source.architecture_id:
        return False
    return (
        set(frontend.contracts_consumed).issubset(set(source.contracts))
        and set(backend.contracts_exposed).issubset(set(source.contracts))
        and set(frontend.invariants_preserved).issubset(set(source.invariants))
        and set(backend.invariants_preserved).issubset(set(source.invariants))
    )
