"""Technology-independent read port for the ISR."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from isr.core.graph import Edge, EdgeType, NodeType
from isr.core.revision import ISRRevision


class ISRQuery:
    """Abstract query object.  Concrete query semantics are defined by the
    adapter that evaluates the query, not by the core ISR types."""

    def __init__(
        self,
        *,
        system_id: str | None = None,
        node_types: Sequence[NodeType] = (),
        edge_types: Sequence[EdgeType] = (),
        filters: Mapping[str, Any] | None = None,
    ) -> None:
        self.system_id = system_id
        self.node_types = node_types
        self.edge_types = edge_types
        self.filters = dict(filters) if filters else {}


class ISRQueryResult:
    """Holds the result of an ISR query.  The result is expressed in terms of
    core graph entities so adapters return domain-level views."""

    def __init__(
        self,
        *,
        revisions: Sequence[ISRRevision] = (),
        nodes: Mapping[str, Any] | None = None,
        edges: Mapping[str, Any] | None = None,
    ) -> None:
        self.revisions = revisions
        self.nodes = dict(nodes) if nodes else {}
        self.edges = dict(edges) if edges else {}


class ISRReader(Protocol):
    """Read-only access to ISR revisions.  Adapters implement this against
    whatever backing store is appropriate (Postgres, filesystem, …)."""

    async def get_revision(self, system_id: str, revision_id: str) -> ISRRevision: ...

    async def get_current(self, system_id: str) -> ISRRevision: ...

    async def query(self, query: ISRQuery) -> ISRQueryResult: ...
