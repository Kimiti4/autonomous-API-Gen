"""Technology-independent persistence port for ISR revisions."""

from __future__ import annotations

from typing import Protocol

from isr.core.revision import ISRRevision


class ISRStore(Protocol):
    """Write + read port for ISR revisions.  The port is deliberately
    technology-independent; adapters implement this for Postgres, filesystem,
    in-memory, etc.  The store enforces immutability: a revision with an
    existing revision_id MUST NOT be silently overwritten."""

    async def load(self, system_id: str, revision_id: str) -> ISRRevision | None: ...

    async def persist(self, revision: ISRRevision) -> None: ...

    async def set_current(self, system_id: str, revision_id: str) -> None: ...
