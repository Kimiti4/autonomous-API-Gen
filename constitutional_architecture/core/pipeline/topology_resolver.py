from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from constitutional_architecture.ckb.knowledge_base import ConstitutionalKnowledgeBase
from constitutional_architecture.core.ckb.patterns import CKBPatterns
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.intent import (
    BusinessArchetype, IntentModel, QualityAttribute,
)
from constitutional_architecture.core.models.requirements_graph import (
    EdgeType, NodeType, RequirementEdge, RequirementNode, RequirementsGraph,
)
from constitutional_architecture.meta.genome import FrontendGenome
from constitutional_architecture.meta.genome.factory import GENOME_PRESETS
from constitutional_architecture.meta.genome.knowledge_graph.iknowledge_graph import (
    ChromosomeTarget, ModifierOperation,
)


class ProductTopologyResolver:
    """Pass 3: Maps IntentModel + RequirementsGraph → ArchitectureGenome + FrontendGenome via CKB."""

    def __init__(self, ckb: Optional[ConstitutionalKnowledgeBase] = None,
                 pattern_lib: Optional[CKBPatterns] = None) -> None:
        self._ckb = ckb or ConstitutionalKnowledgeBase()
        self._patterns = pattern_lib or CKBPatterns()

    def resolve_architectural_profile(self, intent: IntentModel) -> Tuple[ArchitectureGenome, Dict[str, float]]:
        base = self._patterns.get_base_genome(intent.business_archetype)
        mods = self._patterns.apply_quality_modifiers(base, intent.quality_priorities)
        quality_scores = self._patterns.get_quality_profile(intent.business_archetype)
        return base, quality_scores

    def resolve(self, intent: IntentModel) -> 'TopologyResult':
        arch_genome, quality_scores = self.resolve_architectural_profile(intent)
        graph = self._build_requirements_graph(intent)

        preset_name = ARCHETYPE_GENOME_MAP.get(intent.business_archetype, "default")
        factory_fn = GENOME_PRESETS.get(preset_name, GENOME_PRESETS["default"])
        frontend_genome = factory_fn()

        context_tags = [intent.business_archetype.value]
        for cap in intent.core_capabilities:
            context_tags.append(cap.name.lower().replace(" ", "_"))
        patterns = self._ckb.resolve_archetype(context_tags)
        ckb_patterns_used: List[str] = []
        for pattern in patterns:
            for modifier in pattern.genome_modifiers:
                _apply_frontend_modifier(frontend_genome, modifier)
                ckb_patterns_used.append(pattern.id)

        merged_profile = dict(quality_scores)
        for attr, weight in intent.quality_priorities.items():
            merged_profile[attr.value] = weight

        return TopologyResult(
            architecture_genome=arch_genome,
            frontend_genome=frontend_genome,
            archetype=intent.business_archetype,
            requirements_graph=graph,
            pattern_modifiers_applied=len(ckb_patterns_used),
            ckb_patterns_used=ckb_patterns_used,
            quality_profile=merged_profile,
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

        for cap in intent.core_capabilities:
            cap_id = f"cap:{cap.name.lower().replace(' ', '_')}"
            for dep in cap.dependencies:
                dep_id = f"cap:{dep.lower().replace(' ', '_')}"
                graph.add_edge(RequirementEdge(
                    source=cap_id, target=dep_id,
                    type=EdgeType.DEPENDS_ON,
                ))

        return graph


from dataclasses import dataclass, field


@dataclass
class TopologyResult:
    architecture_genome: ArchitectureGenome
    frontend_genome: FrontendGenome
    archetype: BusinessArchetype
    requirements_graph: RequirementsGraph
    pattern_modifiers_applied: int = 0
    ckb_patterns_used: List[str] = field(default_factory=list)
    quality_profile: Dict[str, float] = field(default_factory=dict)


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


def _apply_frontend_modifier(genome: FrontendGenome, modifier: 'GenomeModifier') -> None:
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
