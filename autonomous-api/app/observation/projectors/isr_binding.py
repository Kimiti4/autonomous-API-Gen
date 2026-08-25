"""CanonicalIsrAccessor binding contract (RR-01).

The single integration point between the ISR subsystem (owner of canonical
truth) and the Observation Layer (owner of projections). The binding
ADAPTS the ISR; it never modifies it.

Constitutional invariants enforced by this contract:
1. Read-only. Implementations must never mutate the ISR.
2. No graph leakage. Projections are flattened ISRObservation only.
3. Single-revision consistency. read() returns a snapshot of ONE revision.
4. No invention. Missing required fields fail closed (PLATFORM_UNAVAILABLE).
5. Provenance always. Every projection carries isrRevision + provenance.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CanonicalIsr(Protocol):
    """The minimal read-only surface the binding requires from the ISR.

    The real ISR object must satisfy this structurally. The ISR subsystem
    owns the full schema; this contract only names what the projection needs.
    """

    @property
    def revision(self) -> str: ...

    @property
    def domains(self) -> list:
        """Each element structurally satisfies IsrDomain."""
        ...

    @property
    def services(self) -> list:
        """Each element structurally satisfies IsrService."""
        ...

    @property
    def deployments(self) -> list:
        """Each element structurally satisfies IsrDeployment."""
        ...


@runtime_checkable
class IsrDomain(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def capabilities(self) -> list: ...


@runtime_checkable
class IsrService(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def name(self) -> str: ...

    @property
    def domain(self) -> str: ...


@runtime_checkable
class IsrDeployment(Protocol):
    @property
    def target(self) -> str: ...

    @property
    def service_ids(self) -> list: ...


@runtime_checkable
class CanonicalIsrAccessor(Protocol):
    """The port the ISR subsystem must implement.

    Contract:
      - read() returns a consistent snapshot of a SINGLE revision.
      - current_revision() is cheap and used for cache keys.
      - Implementations MUST NOT block the event loop on heavy I/O without
        yielding; prefer returning a cached, immutable snapshot.
    """

    async def current_revision(self) -> str: ...

    async def read(self) -> CanonicalIsr: ...