"""
Pass 3: Product Topology Resolver.

Consumes IntentModel (Pass 2 output) + RequirementsGraph.
Queries the Constitutional Knowledge Base (CKB) for architectural patterns.
Produces an Architecture Genome seed (Pass 4-5 input), NOT an ISR instance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from constitutional_architecture.ckb.knowledge_base import ConstitutionalKnowledgeBase
from constitutional_architecture.core.ckb.patterns import CKBPatterns
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.intent import (
    BusinessArchetype, Capability, IntentModel, QualityAttribute,
)
from constitutional_architecture.core.models.requirements_graph import (
    EdgeType, NodeType, RequirementEdge, RequirementNode, RequirementsGraph,
)
from constitutional_architecture.meta.genome import FrontendGenome
from constitutional_architecture.meta.genome.factory import GENOME_PRESETS
from constitutional_architecture.meta.genome.knowledge_graph.iknowledge_graph import (
    ChromosomeTarget, ModifierOperation,
)


ARCHETYPE_GENOME_MAP: Dict[BusinessArchetype, str] = {
    BusinessArchetype.B2B_SAAS: "default",
    BusinessArchetype.B2C_SAAS: "default",
    BusinessArchetype.MARKETPLACE: "consumer-app",
    BusinessArchetype.E_COMMERCE: "consumer-app",
    BusinessArchetype.INTERNAL_TOOL: "minimal",
    BusinessArchetype.DATA_PLATFORM: "enterprise-dashboard",
    BusinessArchetype.AI_APPLICATION: "enterprise-dashboard",
    BusinessArchetype.FINTECH: "enterprise-dashboard",
    BusinessArchetype.HEALTHCARE: "default",
    BusinessArchetype.ERP: "enterprise-dashboard",
    BusinessArchetype.CRM: "default",
}


@dataclass
class TopologyResult:
    genome: FrontendGenome
    architecture_genome: ArchitectureGenome = field(default_factory=ArchitectureGenome)
    archetype: BusinessArchetype = BusinessArchetype.B2B_SAAS
    requirements_graph: RequirementsGraph = field(default_factory=RequirementsGraph)
    pattern_modifiers_applied: int = 0
    ckb_patterns_used: List[str] = field(default_factory=list)
    quality_profile: Dict[str, float] = field(default_factory=dict)


class ProductTopologyResolver:
    """Pass 3: Maps IntentModel + RequirementsGraph → Genome seed via CKB."""

    def __init__(self, ckb: Optional[ConstitutionalKnowledgeBase] = None,
                 pattern_lib: Optional[CKBPatterns] = None) -> None:
        self._ckb = ckb or ConstitutionalKnowledgeBase()
        self._patterns = pattern_lib or CKBPatterns()

    def resolve(self, intent: IntentModel) -> TopologyResult:
        graph = self._build_requirements_graph(intent)

        # Resolve architecture genome via CKB patterns
        arch_genome = self._patterns.get_base_genome(intent.business_archetype)
        self._patterns.apply_quality_modifiers(arch_genome, intent.quality_priorities)

        preset_name = ARCHETYPE_GENOME_MAP.get(intent.business_archetype, "default")
        factory_fn = GENOME_PRESETS.get(preset_name, GENOME_PRESETS["default"])
        genome = factory_fn()

        context_tags = [intent.business_archetype.value]
        for cap in intent.core_capabilities:
            context_tags.append(cap.name.lower().replace(" ", "_"))
        patterns = self._ckb.resolve_archetype(context_tags)
        ckb_patterns_used: List[str] = []
        for pattern in patterns:
            for modifier in pattern.genome_modifiers:
                self._apply_modifier(genome, modifier)
                ckb_patterns_used.append(pattern.id)

        quality_profile = dict(self._patterns.get_quality_profile(intent.business_archetype))
        for attr, weight in intent.quality_priorities.items():
            quality_profile[attr.value] = weight

        return TopologyResult(
            genome=genome,
            architecture_genome=arch_genome,
            archetype=intent.business_archetype,
            requirements_graph=graph,
            pattern_modifiers_applied=len(ckb_patterns_used),
            ckb_patterns_used=ckb_patterns_used,
            quality_profile=quality_profile,
        )

    def _build_requirements_graph(self, intent: IntentModel) -> RequirementsGraph:
        graph = RequirementsGraph()

        for cap in intent.core_capabilities:
            graph.add_node(RequirementNode(
                id=f"cap:{cap.name.lower().replace(' ', '_')}",
                type=NodeType.CAPABILITY,
                label=cap.name,
                properties={"priority": cap.priority, "security": cap.security_classification},
            ))

        for persona in intent.personas:
            pid = f"persona:{persona.name.lower().replace(' ', '_')}"
            graph.add_node(RequirementNode(
                id=pid,
                type=NodeType.PERSONA,
                label=persona.name,
                properties={"role": persona.role, "proficiency": persona.technical_proficiency},
            ))

        for dd in intent.data_domains:
            graph.add_node(RequirementNode(
                id=f"data:{dd.name.lower().replace(' ', '_')}",
                type=NodeType.DATA_DOMAIN,
                label=dd.name,
                properties={"entities": dd.entities, "consistency": dd.consistency_requirement},
            ))

        for qa, weight in intent.quality_priorities.items():
            graph.add_node(RequirementNode(
                id=f"quality:{qa.value}",
                type=NodeType.QUALITY_ATTRIBUTE,
                label=qa.value,
                properties={"weight": weight},
            ))

        for cs in intent.compliance_standards:
            graph.add_node(RequirementNode(
                id=f"compliance:{cs.value}",
                type=NodeType.COMPLIANCE_STANDARD,
                label=cs.value,
                properties={},
            ))

        # Edge: capabilities → capabilities (dependencies)
        for cap in intent.core_capabilities:
            cap_id = f"cap:{cap.name.lower().replace(' ', '_')}"
            for dep in cap.dependencies:
                dep_id = f"cap:{dep.lower().replace(' ', '_')}"
                graph.add_edge(RequirementEdge(
                    source=cap_id, target=dep_id,
                    type=EdgeType.DEPENDS_ON,
                ))

        return graph

    def _apply_modifier(self, genome: FrontendGenome, modifier: Any) -> None:
        chromosome_map = {
            ChromosomeTarget.PRESENTATION: genome.presentation,
            ChromosomeTarget.STRUCTURE: genome.structure,
            ChromosomeTarget.BEHAVIOR: genome.behavior,
            ChromosomeTarget.COMPOSITION: genome.composition,
        }
        chromosome = chromosome_map.get(modifier.target_chromosome)
        if chromosome is None:
            return

        for gene in chromosome.genes:
            if gene.id == modifier.target_gene:
                if modifier.operation == ModifierOperation.SET:
                    gene._allele = modifier.value
                elif modifier.operation == ModifierOperation.MULTIPLY:
                    if isinstance(gene.allele, (int, float)):
                        gene._allele = gene.allele * modifier.value
                elif modifier.operation == ModifierOperation.ADD:
                    if isinstance(gene.allele, (int, float)):
                        gene._allele = gene.allele + modifier.value
                break
