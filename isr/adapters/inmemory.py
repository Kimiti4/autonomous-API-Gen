"""In-memory reference adapter for the ISR store port.

Provides a deterministic, technology-independent implementation for tests,
gate verification, and G6 (exact reconstruction) validation.  Enforces the
constitutional immutability rule: a revision with an existing revision_id
cannot be overwritten silently.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Mapping, MutableMapping

from isr.core.revision import ISRRevision


class ISRImmutableViolation(Exception):
    """Raised when an adapter operation violates ISR immutability."""

    def __init__(self, revision_id: str) -> None:
        self.revision_id = revision_id
        super().__init__(
            f"Revision '{revision_id}' already exists; ISR revisions are immutable "
            f"and cannot be overwritten"
        )


class ISRRevisionNotFound(Exception):
    """Raised when a requested revision does not exist in the store."""

    def __init__(self, system_id: str, revision_id: str) -> None:
        self.system_id = system_id
        self.revision_id = revision_id
        super().__init__(
            f"Revision '{revision_id}' not found for system '{system_id}'"
        )


class MemoryISRStore:
    """Deterministic in-memory ISR store (G6 reference adapter).

    Storage is organised as:
        _store[system_id][revision_id] = ISRRevision
        _current[system_id] = revision_id | None

    All operations are synchronous despite the async protocol so tests remain
    simple; the caller may wrap in ``asyncio.get_event_loop().run_in_executor``
    if a true async boundary is required.
    """

    def __init__(self) -> None:
        self._store: MutableMapping[str, MutableMapping[str, ISRRevision]] = defaultdict(dict)
        self._current: MutableMapping[str, str | None] = {}

    async def load(self, system_id: str, revision_id: str) -> ISRRevision | None:
        return self._store.get(system_id, {}).get(revision_id)

    async def persist(self, revision: ISRRevision) -> None:
        revisions = self._store[revision.system_id]
        if revision.revision_id in revisions:
            raise ISRImmutableViolation(revision.revision_id)
        revisions[revision.revision_id] = revision

    async def set_current(self, system_id: str, revision_id: str) -> None:
        if system_id not in self._store or revision_id not in self._store[system_id]:
            raise ISRRevisionNotFound(system_id, revision_id)
        self._current[system_id] = revision_id

    async def get_current_revision(self, system_id: str) -> ISRRevision | None:
        rev_id = self._current.get(system_id)
        if rev_id is None:
            return None
        return await self.load(system_id, rev_id)
