"""
Phase 16.1 — Policy Engine: deny-by-default UI projection.

Every surface is a projection of the capability ledger (D-1). The engine is
deny-by-default: a principal is granted nothing unless a registered
capability says otherwise, and every denial carries an explainable reason
(`requires <cap>`). Projections are deterministic — input order never
affects the emitted navigation tree.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from constitutional_architecture.core.hil.capabilities import (
    CapabilityRegistry,
    CapabilityStatus,
)


class Denial(BaseModel):
    capability: str
    principal: str
    reason: str
    source: str = "policy_engine"


class AuthorizationDecision(BaseModel):
    allowed: bool
    capability: str
    principal: str
    denial: Optional[Denial] = None


class NavigationEntry(BaseModel):
    id: str
    label: str
    capability: str
    children: List["NavigationEntry"] = Field(default_factory=list)


class NavigationProjection(BaseModel):
    principal: str
    entries: List[NavigationEntry] = Field(default_factory=list)
    denials: List[Denial] = Field(default_factory=list)

    def visible_ids(self) -> List[str]:
        def walk(nodes: List[NavigationEntry]) -> List[str]:
            out: List[str] = []
            for n in nodes:
                out.append(n.id)
                out.extend(walk(n.children))
            return out

        return walk(self.entries)


class PolicyEngine:
    """Projects capability-gated surfaces. Never mutates the ledger."""

    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry

    def authorize(self, principal: str, required_cap: str) -> AuthorizationDecision:
        """Deny-by-default check with an explainable denial."""
        cap = self.registry.get(required_cap)
        if cap is None:
            return AuthorizationDecision(
                allowed=False,
                capability=required_cap,
                principal=principal,
                denial=Denial(
                    capability=required_cap,
                    principal=principal,
                    reason=f"requires {required_cap} (unknown capability)",
                ),
            )
        allowed = cap.status in (CapabilityStatus.ACTIVE, CapabilityStatus.INTRODUCED)
        return AuthorizationDecision(
            allowed=allowed,
            capability=required_cap,
            principal=principal,
            denial=(
                None
                if allowed
                else Denial(
                    capability=required_cap,
                    principal=principal,
                    reason=f"requires {required_cap}",
                )
            ),
        )

    def project_navigation(
        self,
        principal: str,
        granted: List[str],
        nav_tree: List[NavigationEntry],
    ) -> NavigationProjection:
        """
        Filter a navigation tree to the principal's effective claims.
        Deny-by-default: an entry whose capability is not held is dropped
        and reported as a denial with reason `requires <cap>`.
        Deterministic: entries keep tree order; denials are sorted.
        """
        claims = self.registry.claims_for(set(granted))

        def walk(nodes: List[NavigationEntry], denials: List[Denial]) -> List[NavigationEntry]:
            kept: List[NavigationEntry] = []
            for entry in sorted(nodes, key=lambda n: n.id):
                if entry.capability in claims:
                    children = walk(entry.children, denials)
                    kept.append(entry.model_copy(update={"children": children}))
                else:
                    denials.append(
                        Denial(
                            capability=entry.capability,
                            principal=principal,
                            reason=f"requires {entry.capability}",
                        )
                    )
            return kept

        denials: List[Denial] = []
        entries = walk(nav_tree, denials)
        denials.sort(key=lambda d: d.capability)
        return NavigationProjection(
            principal=principal, entries=entries, denials=denials
        )
