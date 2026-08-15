"""
Phase 16.1 — UIPM v1 Serializer: renderer-agnostic UI Projection Model.

The UI is a compiled view — a projection of (isr_snapshot, principal,
capability_schema_ver, uipm_ver) — and is NEVER stored. Replay re-derives.

UIPM surfaces (D-4): navigation, layout, components, commands, events.
The capability surface and the command surface are renderer-independent
test properties; renderers (react P0, terminal P1, desktop/mobile P2,
AR/VR P3) differ only in the layout compiler backend.

Latency budgets: navigation <= 16ms, layout <= 100ms.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from constitutional_architecture.core.hil.capabilities import CapabilityRegistry
from constitutional_architecture.core.hil.policy_engine import (
    NavigationEntry,
    NavigationProjection,
    PolicyEngine,
)

UIPM_VERSION = "1.0"
NAV_LATENCY_BUDGET_MS = 16.0
LAYOUT_LATENCY_BUDGET_MS = 100.0


class ProjectionRequest(BaseModel):
    """Everything the projection is a pure function of."""

    isr_snapshot_id: str
    principal: str
    capability_schema_ver: str
    uipm_ver: str = UIPM_VERSION


def projection_ref(request: ProjectionRequest) -> str:
    """
    Content-address of the derived projection, per ratified doctrine:
        projection_ref = hash(isr_snapshot, principal, capability_schema_ver,
                              uipm_ver)
    Deterministic and re-derivable: replaying the request yields the same ref.
    """
    return hashlib.sha256(
        json.dumps(request.model_dump(), sort_keys=True).encode()
    ).hexdigest()


class Command(BaseModel):
    id: str
    label: str
    capability: str


class EventSurface(BaseModel):
    id: str
    kind: str
    capability: str


class UIPMDocument(BaseModel):
    uipm_ver: str
    projection_ref: str
    renderer: str
    navigation: List[NavigationEntry] = Field(default_factory=list)
    layout: Dict[str, Any] = Field(default_factory=dict)
    components: List[Dict[str, str]] = Field(default_factory=list)
    commands: List[Command] = Field(default_factory=list)
    events: List[EventSurface] = Field(default_factory=list)
    nav_latency_ms: float = 0.0
    layout_latency_ms: float = 0.0

    def capability_surface(self) -> List[str]:
        """Renderer-independent capability surface (D-4 test property)."""
        caps: List[str] = []
        for entry in self.navigation:
            caps.append(entry.capability)
            caps.extend(c.capability for c in entry.children)
        caps.extend(cmd.capability for cmd in self.commands)
        return sorted(set(caps))

    def command_surface(self) -> List[str]:
        return sorted(cmd.id for cmd in self.commands)


class UIPMSerializer:
    """
    Compiles a ProjectionRequest into a UIPMDocument for a renderer backend.
    Pure with respect to its inputs: identical inputs yield identical output
    (modulo measured latency), which is what makes re-derivation safe.
    """

    def __init__(self, engine: PolicyEngine, registry: CapabilityRegistry) -> None:
        self.engine = engine
        self.registry = registry

    def serialize(
        self,
        request: ProjectionRequest,
        granted: List[str],
        nav_tree: List[NavigationEntry],
        renderer: str = "react",
    ) -> UIPMDocument:
        t0 = time.perf_counter()
        projection: NavigationProjection = self.engine.project_navigation(
            request.principal, granted, nav_tree
        )
        t1 = time.perf_counter()
        nav_latency_ms = (t1 - t0) * 1000.0

        commands = [
            Command(id="promote", label="Promote candidate", capability="ops.promote"),
            Command(id="mutate", label="Queue mutation", capability="ops.mutate"),
            Command(id="run", label="Run generation", capability="ops.run"),
            Command(id="dismiss", label="Dismiss", capability="ops.dismiss"),
        ]
        claims = set(self.registry.claims_for(set(granted)))
        commands = [
            cmd for cmd in commands
            if cmd.capability in claims or cmd.capability == "ops.dismiss"
        ]
        components = [
            {"kind": "card", "capability": cap}
            for cap in self.registry.valid_ids()
            if cap in claims
        ]
        events = [
            EventSurface(id="telemetry", kind="stream", capability="obs.telemetry"),
            EventSurface(id="log", kind="stream", capability="obs.log"),
            EventSurface(id="arbitration", kind="notice", capability="ops.arbitration"),
        ]
        t2 = time.perf_counter()
        layout_latency_ms = (t2 - t1) * 1000.0

        return UIPMDocument(
            uipm_ver=request.uipm_ver,
            projection_ref=projection_ref(request),
            renderer=renderer,
            navigation=projection.entries,
            layout={
                "panels": self._layout_panels(renderer, projection),
                "latency_budget_ms": LAYOUT_LATENCY_BUDGET_MS,
            },
            components=components,
            commands=commands,
            events=events,
            nav_latency_ms=nav_latency_ms,
            layout_latency_ms=layout_latency_ms,
        )

    def _layout_panels(
        self, renderer: str, projection: NavigationProjection
    ) -> List[str]:
        """Renderer-specific layout backends (D-4). Surface, not truth."""
        base = ["command_bar", "content"]
        if renderer == "react":
            return base + ["dock", "palette", "isr_map"]
        if renderer == "terminal":
            return base + ["status_line"]
        if renderer == "desktop":
            return base + ["dock", "status_bar"]
        return base  # ar/vr: minimal projection

    def within_budgets(self, doc: UIPMDocument) -> bool:
        return (
            doc.nav_latency_ms <= NAV_LATENCY_BUDGET_MS
            and doc.layout_latency_ms <= LAYOUT_LATENCY_BUDGET_MS
        )
