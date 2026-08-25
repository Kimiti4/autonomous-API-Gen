"""Capability negotiation contract (closes GAP-04).

The dashboard asks the platform what it supports instead of assuming.
"""
from __future__ import annotations

from app.core.contracts.events import EventType
from app.core.contracts.observations import (
    CapabilityContract,
    CapabilityFeature,
    CapabilitySchema,
)
from app.observation.projectors.base import ProjectionContract


async def build_capabilities(store, source_revision: str) -> CapabilityContract:
    """Build the capability contract from live platform state."""
    supported_streams = []
    # Enumerate known streams from the store where cheaply possible.
    if hasattr(store, "_counter"):
        supported_streams = sorted(
            s for s, v in store._counter.items() if v >= 0
        )

    return CapabilityContract(
        observationSchemas=[
            CapabilitySchema(
                contractId=cid,
                versions=[ver],
            )
            for cid, ver in (
                ProjectionContract.ISR,
                ProjectionContract.FITNESS,
                ProjectionContract.CANDIDATES,
                ProjectionContract.LINEAGE,
            )
        ],
        eventTypes=list(EventType.__args__),  # type: ignore[attr-defined]
        supportedStreamIds=supported_streams,
        features=[
            CapabilityFeature(id="error_envelope", version="1.0.0"),
            CapabilityFeature(id="event_envelope", version="1.0.0"),
            CapabilityFeature(id="stream_replay", version="1.0.0"),
            CapabilityFeature(id="authoritative_pareto", version="1.0.0"),
        ],
    )