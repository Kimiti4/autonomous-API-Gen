"""
Frontend Transformer — bidirectional mapping between platform ISR and Frontend ISR Profile.

The ISR is the sole source of truth. The FrontendISRProfile is an extension
that references backend entities by ID. This transformer ensures consistency.
"""

from __future__ import annotations

from typing import Any, Optional

from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.system import System
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.service import Service
from constitutional_architecture.isr.model.entity import Entity
from constitutional_architecture.isr.model.nodes import NodeType
from constitutional_architecture.isr.model.edges import EdgeType
from constitutional_architecture.isr.isr_graph import ISRGraph

from constitutional_architecture.isr.profiles.frontend_model import (
    FrontendISRProfile, DesignSystem, Component, ComponentNode,
    Layout, Page, Interaction, TokenDefinition,
    GenomeMapping, ChromosomeFamily, AccessibilityContract,
    PropertyDefinition, EventDefinition,
)


class FrontendTransformer:
    """Bidirectional mapping between platform ISR and FrontendISRProfile."""

    @staticmethod
    def embed_profile(isr: ISR, profile: FrontendISRProfile) -> ISR:
        """Embed a FrontendISRProfile into a platform ISR as metadata.

        Returns a new ISR instance (immutable pattern).
        """
        system = isr.system
        new_metadata = dict(system.metadata.__dict__) if hasattr(system.metadata, "__dict__") else {}
        new_metadata["frontend_profile"] = profile

        from constitutional_architecture.isr.model.system import SystemMetadata
        new_sys_meta = SystemMetadata(
            version=system.metadata.version,
            authors=system.metadata.authors,
            license=system.metadata.license,
            description=system.metadata.description,
            tags=system.metadata.tags,
        )

        new_system = System(
            id=system.id,
            name=system.name,
            description=system.description,
            modules=system.modules,
            deployment=system.deployment,
            metadata=new_sys_meta,
            global_policies=system.global_policies,
        )

        return ISR(
            system=new_system,
            version=isr.version + 1,
        )

    @staticmethod
    def extract_profile(isr: ISR) -> Optional[FrontendISRProfile]:
        """Extract a previously embedded FrontendISRProfile from an ISR."""
        metadata = isr.system.metadata
        if hasattr(metadata, "__dict__"):
            profile = metadata.__dict__.get("frontend_profile")
        else:
            profile = getattr(metadata, "frontend_profile", None)
        if isinstance(profile, FrontendISRProfile):
            return profile
        return None

    @staticmethod
    def build_data_requirement_refs(graph: ISRGraph) -> dict[str, list[str]]:
        """From the platform ISR graph, build a map of available API/service refs per module.

        Returns {module_name: [entity_id, service_id, ...]} that pages can reference.
        """
        refs: dict[str, list[str]] = {}
        for node in graph.nodes.values():
            module = node.module_name or "global"
            if module not in refs:
                refs[module] = []
            refs[module].append(node.node_id)
        return refs

    @staticmethod
    def check_page_data_integrity(
        profile: FrontendISRProfile,
        graph: ISRGraph,
    ) -> list[str]:
        """Verify that every Page.data_requirements reference exists in the ISR graph.

        Returns a list of broken references.
        """
        broken: list[str] = []
        all_node_ids = set(graph.nodes.keys())
        for page in profile.pages:
            for ref in page.data_requirements:
                if ref not in all_node_ids:
                    broken.append(f"Page '{page.id}' references '{ref}' — not found in ISR graph")
        return broken
