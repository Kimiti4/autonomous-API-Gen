"""
Frontend Design Genome — Phases 3 of the FEE Runtime.

Encodes the "taste," "systems thinking," and "accumulated heuristics"
of a senior frontend engineer into a structured, evolvable parameter space.

The genome stores abstract design parameters (genotype). The Frontend ISR
Profile (Phase 2) acts as the intermediate expression. The Transcriber
bridges genotype → ISR. Compiler Backends produce the final rendered UI
(phenotype).
"""

from constitutional_architecture.meta.genome.genes import (
    Gene, ColorSystemGene, ColorSystemAllele,
    TypographyScaleGene, BaseSizeGene,
    ElevationModelGene, MorphologyGene, MorphologyAllele,
    SpacingScaleGene, GridSystemGene, GridSystemAllele,
    DensityProfileGene, BreakpointStrategyGene, BreakpointStrategyAllele,
    MotionPhysicsGene, MotionPhysicsAllele,
    DurationScaleGene, InteractionFeedbackGene, InteractionFeedbackAllele,
    VisualWeightGene, VisualWeightAllele, ComponentVariantAllele,
    ComponentVariantGene,
    AccessibilityThresholdGene,
    PerformanceBudgetGene, PerformanceBudgetAllele,
    CognitiveLoadGene,
    Bounds, MutationType, GENE_REGISTRY,
)
from constitutional_architecture.meta.genome.chromosomes import (
    FrontendGenome,
    PresentationChromosome, StructureChromosome,
    BehaviorChromosome, CompositionChromosome, ComplianceChromosome,
)
from constitutional_architecture.meta.genome.operators import (
    FrontendMutator, FrontendCrossover,
    MutationRecord, CrossoverRecord,
)
from constitutional_architecture.meta.genome.transcriber import FrontendGenomeTranscriber
from constitutional_architecture.meta.genome.lethality import (
    check_genome_lethality, LethalityResult,
)
from constitutional_architecture.meta.genome.factory import (
    create_default_genome, create_enterprise_dashboard_genome,
    create_consumer_app_genome, create_minimal_genome,
    create_population, GENOME_PRESETS,
)
from constitutional_architecture.meta.genome.knowledge_graph import (
    IKnowledgeGraph, DesignPattern, GenomeModifier, ContextTag,
    ChromosomeTarget, ModifierOperation, PatternCategory,
    InMemoryKnowledgeGraph,
)
from constitutional_architecture.meta.genome.seeder import HeuristicInjector
from constitutional_architecture.meta.genome.evaluators import (
    IFitnessEvaluator, FitnessDimension,
    TokenConsistencyEvaluator, AccessibilityEvaluator,
    VisualHierarchyEvaluator, CompositeFitness,
)
from constitutional_architecture.meta.genome.evolution import (
    ParetoEvolutionCoordinator, Candidate, EvolutionResult,
)
from constitutional_architecture.meta.genome.compilers import (
    IFrontendCompiler, CompiledArtifact, TailwindCompiler,
)
from constitutional_architecture.meta.genome.components import ComponentAPIMutator, ComponentAPIMutation
from constitutional_architecture.meta.genome.visual_intel import VisualIntelligenceEvaluator
from constitutional_architecture.meta.genome.memory import (
    IConstitutionalMemory, EvolutionarySnapshot,
    InMemoryConstitutionalMemory, TasteModelUpdater,
)

__all__ = [
    # Genes
    "Gene", "Bounds", "MutationType", "GENE_REGISTRY",
    "ColorSystemGene", "ColorSystemAllele",
    "TypographyScaleGene", "BaseSizeGene",
    "ElevationModelGene", "MorphologyGene", "MorphologyAllele",
    "SpacingScaleGene", "GridSystemGene", "GridSystemAllele",
    "DensityProfileGene", "BreakpointStrategyGene", "BreakpointStrategyAllele",
    "MotionPhysicsGene", "MotionPhysicsAllele",
    "DurationScaleGene", "InteractionFeedbackGene", "InteractionFeedbackAllele",
    "VisualWeightGene", "VisualWeightAllele", "ComponentVariantGene", "ComponentVariantAllele",
    "AccessibilityThresholdGene",
    "PerformanceBudgetGene", "PerformanceBudgetAllele",
    "CognitiveLoadGene",
    # Chromosomes
    "FrontendGenome",
    "PresentationChromosome", "StructureChromosome",
    "BehaviorChromosome", "CompositionChromosome", "ComplianceChromosome",
    # Operators
    "FrontendMutator", "FrontendCrossover",
    "MutationRecord", "CrossoverRecord",
    # Transcriber
    "FrontendGenomeTranscriber",
    # Lethality
    "check_genome_lethality", "LethalityResult",
    # Factory
    "create_default_genome", "create_enterprise_dashboard_genome",
    "create_consumer_app_genome", "create_minimal_genome",
    "create_population", "GENOME_PRESETS",
    # Phase 4: Knowledge Graph
    "IKnowledgeGraph", "DesignPattern", "GenomeModifier", "ContextTag",
    "ChromosomeTarget", "ModifierOperation", "PatternCategory",
    "InMemoryKnowledgeGraph",
    # Phase 4: Seeder
    "HeuristicInjector",
    # Phase 5: Evaluators
    "IFitnessEvaluator", "FitnessDimension",
    "TokenConsistencyEvaluator", "AccessibilityEvaluator",
    "VisualHierarchyEvaluator", "CompositeFitness",
    # Phase 6: Evolution
    "ParetoEvolutionCoordinator", "Candidate", "EvolutionResult",
    # Phase 7/12: Compilers
    "IFrontendCompiler", "CompiledArtifact", "TailwindCompiler",
    # Phase 8: Component Runtime
    "ComponentAPIMutator", "ComponentAPIMutation",
    # Phase 9: Visual Intelligence
    "VisualIntelligenceEvaluator",
    # Phase 10/11: Memory & Taste
    "IConstitutionalMemory", "EvolutionarySnapshot",
    "InMemoryConstitutionalMemory", "TasteModelUpdater",
]
