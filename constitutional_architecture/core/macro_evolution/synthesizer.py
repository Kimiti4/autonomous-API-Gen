"""
Phase 20 — Archetype Synthesizer.

Mints new CKB Archetypes and generates Platform-Level ADRs based on fleet
evidence. New archetypes are registered as EXPERIMENTAL and remain entirely
abstract and technology-agnostic.

Constitutional Alignment:
- "Continuous Evolution": the platform expands its own architectural
  vocabulary from fleet-wide production evidence.
- "Significant decisions should document Context, Problem, Alternatives,
  Trade-offs, Benefits, Risks": every minted archetype ships with a
  Platform ADR.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from constitutional_architecture.core.models.intent import QualityAttribute


class ArchetypeSynthesizer:
    """
    Evolves the Constitutional Knowledge Base by minting new architectural
    archetypes. `ckb` must expose
    `register_archetype(name, base_genes, empirical_weights)`.
    """

    def __init__(self, ckb: Any) -> None:
        self.ckb = ckb

    def synthesize_new_archetype(self, pattern_data: Dict[str, Any]) -> str:
        """
        Register the emergent pattern as a first-class Archetype in the CKB
        and generate the constitutional Platform ADR.
        """
        topology = pattern_data["topology_signature"]
        attr = pattern_data["attribute"]
        deviation = pattern_data["deviation"]
        sample_size = pattern_data["sample_size"]

        new_archetype_name = f"EMERGENT_{topology.upper()}_{attr.name}"
        self.ckb.register_archetype(
            name=new_archetype_name,
            base_genes={"architecture_style": topology},
            empirical_weights={attr: 0.95},
        )

        return self._generate_platform_adr(new_archetype_name, pattern_data)

    def _generate_platform_adr(self, archetype_name: str,
                               data: Dict[str, Any]) -> str:
        """Document the platform's own evolutionary shift (Constitution:
        Context, Problem, Alternatives, Trade-offs, Benefits, Risks)."""
        date_str = datetime.now(timezone.utc).isoformat()
        attr: QualityAttribute = data["attribute"]

        return f"""# Platform ADR: Minting New Archetype `{archetype_name}`

**Date:** {date_str}
**Status:** Accepted (Autonomous Macro-Evolution)
**Trigger:** Fleet Telemetry Anomaly Detection

## Context
The Runtime Learning Engine (Phase 18) has been monitoring the global fleet of deployed systems.
The Constitutional Knowledge Base (CKB) baseline predicted that the topology `{data['topology_signature']}`
would yield a `{attr.value}` score of `{data['baseline_score']:.2f}`.

## Observation (The Evidence)
Across `{data['sample_size']}` independent production deployments, this topology consistently
achieved an empirical `{attr.value}` score of `{data['empirical_score']:.2f}`.
This represents a positive deviation of `{data['deviation']:.2%}`.

## Decision
The platform has autonomously minted a new Architectural Archetype: `{archetype_name}`.
Future Intent Models matching this profile will be seeded with this archetype during Pass 3 (Topology Resolution),
bypassing the need for the Evolution Engine to rediscover this optimal topology from scratch.

## Trade-offs & Risks
- **Risk:** Fleet-wide correlation does not guarantee causation. The high performance may be driven by
  a hidden variable (e.g., specific workload types) rather than the topology itself.
- **Mitigation:** The new archetype is tagged as EXPERIMENTAL in the CKB. The Multi-Agent Coordinator
  (Phase 19) will inject a WARNING critique when this archetype is selected, forcing the Evolution
  Engine to heavily scrutinize it during Pareto optimization.
"""
