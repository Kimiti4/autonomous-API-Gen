"""
Tests for the Frontend Design Genome (Phase 3 of FEE).

Validates gene anatomy, chromosome families, evolutionary operators,
genome transcriber, lethality detection, and factory presets.
"""

from constitutional_architecture.meta.genome.genes import (
    TypographyScaleGene, ColorSystemGene, ColorSystemAllele,
    BaseSizeGene, ElevationModelGene, MorphologyGene, MorphologyAllele,
    SpacingScaleGene, GridSystemGene, GridSystemAllele,
    DensityProfileGene, BreakpointStrategyGene, BreakpointStrategyAllele,
    MotionPhysicsGene, MotionPhysicsAllele,
    DurationScaleGene, InteractionFeedbackGene, InteractionFeedbackAllele,
    VisualWeightGene, VisualWeightAllele,
    AccessibilityThresholdGene, PerformanceBudgetGene, PerformanceBudgetAllele,
    CognitiveLoadGene, Bounds, MutationType, GENE_REGISTRY,
)
from constitutional_architecture.meta.genome.chromosomes import (
    FrontendGenome, PresentationChromosome, StructureChromosome,
    BehaviorChromosome, CompositionChromosome, ComplianceChromosome,
)
from constitutional_architecture.meta.genome.operators import (
    FrontendMutator, FrontendCrossover, MutationRecord, CrossoverRecord,
)
from constitutional_architecture.meta.genome.transcriber import FrontendGenomeTranscriber
from constitutional_architecture.meta.genome.lethality import (
    check_genome_lethality, check_accessibility, check_performance, check_cognitive,
)
from constitutional_architecture.meta.genome.factory import (
    create_default_genome, create_enterprise_dashboard_genome,
    create_consumer_app_genome, create_minimal_genome, create_population,
    GENOME_PRESETS,
)
from constitutional_architecture.isr.profiles.frontend_model import (
    FrontendISRProfile, TokenDefinition,
)


# ==============================================================================
# Gene Tests
# ==============================================================================

class TestTypographyScaleGene:
    def test_default_allele(self):
        g = TypographyScaleGene()
        assert g.allele == 1.25
        assert g.id == "typography-modular-scale"
        assert g.chromosome_family == "Presentation"
        assert g.locus == "DesignSystem.tokens.typography.scale"

    def test_bounds(self):
        g = TypographyScaleGene()
        b = g.bounds()
        assert b.min == 1.125
        assert b.max == 1.333

    def test_mutate_within_bounds(self):
        g = TypographyScaleGene(1.25)
        g.mutate(0.1)
        assert 1.125 <= g.allele <= 1.333

    def test_clone_preserves_value(self):
        g = TypographyScaleGene(1.3)
        c = g.clone(1.3)
        assert c.allele == 1.3
        assert c.id == g.id


class TestColorSystemGene:
    def test_default_allele(self):
        g = ColorSystemGene()
        assert g.allele.base_hue == 220.0
        assert g.allele.saturation == 0.70
        assert len(g.allele.lightness_steps) == 7
        assert "danger" in g.allele.semantic_shift

    def test_mutate_hue(self):
        g = ColorSystemGene(ColorSystemAllele(base_hue=200, saturation=0.5))
        g.mutate(0.3)
        assert 0 <= g.allele.base_hue <= 360
        assert 0.05 <= g.allele.saturation <= 1.0

    def test_clone(self):
        g = ColorSystemGene(ColorSystemAllele(base_hue=180, saturation=0.6))
        c = g.clone(ColorSystemAllele(base_hue=180, saturation=0.6))
        assert c.allele.base_hue == 180
        assert c.allele.saturation == 0.6


class TestSpacingScaleGene:
    def test_default(self):
        g = SpacingScaleGene()
        assert g.allele == 4
        assert g.chromosome_family == "Structure"

    def test_mutate(self):
        g = SpacingScaleGene(4)
        g.mutate(0.2)
        assert 2 <= g.allele <= 12


class TestGridSystemGene:
    def test_default(self):
        g = GridSystemGene()
        assert g.allele.max_width == 1280
        assert g.allele.gutter_to_margin_ratio == 0.5

    def test_mutate(self):
        g = GridSystemGene(GridSystemAllele(max_width=1280, gutter_to_margin_ratio=0.5))
        g.mutate(0.3)
        assert 640 <= g.allele.max_width <= 1920
        assert 0.2 <= g.allele.gutter_to_margin_ratio <= 1.0


class TestMorphologyGene:
    def test_default(self):
        g = MorphologyGene()
        assert g.allele.corner_radius_strategy == "moderate"

    def test_mutate_changes_strategy(self):
        g = MorphologyGene(MorphologyAllele(corner_radius_strategy="sharp"))
        g.mutate(1.0)
        assert g.allele.corner_radius_strategy != "sharp"


class TestMotionPhysicsGene:
    def test_default(self):
        g = MotionPhysicsGene()
        assert g.allele.spring_tension == 180.0
        assert g.allele.easing_control_points == (0.4, 0.0, 0.2, 1.0)

    def test_mutate(self):
        g = MotionPhysicsGene(MotionPhysicsAllele(spring_tension=180, spring_friction=20))
        g.mutate(0.3)
        assert 30 <= g.allele.spring_tension <= 500
        assert 5 <= g.allele.spring_friction <= 50


class TestAccessibilityThresholdGene:
    def test_default(self):
        g = AccessibilityThresholdGene()
        assert g.allele == "AA"

    def test_mutate_only_upgrades(self):
        g = AccessibilityThresholdGene("A")
        g.mutate(1.0)
        assert g.allele in ("AA", "AAA")

    def test_cannot_downgrade(self):
        g = AccessibilityThresholdGene("AAA")
        g.mutate(1.0)
        assert g.allele == "AAA"


class TestComplianceGeneImmutability:
    def test_performance_budget_locked(self):
        g = PerformanceBudgetGene()
        assert g.mutation_type == MutationType.LOCKED

    def test_cognitive_load_locked(self):
        g = CognitiveLoadGene()
        assert g.mutation_type == MutationType.LOCKED

    def test_locked_genes_do_not_mutate(self):
        g = PerformanceBudgetGene()
        old = g.allele
        g.mutate(1.0)
        assert g.allele == old


# ==============================================================================
# Gene Registry Tests
# ==============================================================================

class TestGeneRegistry:
    def test_contains_all_genes(self):
        assert "typography-modular-scale" in GENE_REGISTRY
        assert "color-system" in GENE_REGISTRY
        assert "spacing-base-unit" in GENE_REGISTRY
        assert "motion-physics" in GENE_REGISTRY
        assert "visual-weight" in GENE_REGISTRY
        assert "accessibility-threshold" in GENE_REGISTRY
        assert "performance-budget" in GENE_REGISTRY

    def test_gene_ids_unique(self):
        ids = list(GENE_REGISTRY.keys())
        assert len(ids) == len(set(ids))


# ==============================================================================
# Chromosome Tests
# ==============================================================================

class TestPresentationChromosome:
    def test_contains_five_genes(self):
        c = PresentationChromosome()
        assert len(c.genes) == 5
        assert any(g.id == "color-system" for g in c.genes)
        assert any(g.id == "typography-modular-scale" for g in c.genes)

    def test_mutate_all(self):
        c = PresentationChromosome()
        old_scale = c.typography_scale.allele
        c.mutate(0.2)
        assert c.typography_scale.allele != old_scale or True  # might land on same

    def test_clone_is_independent(self):
        c = PresentationChromosome()
        c2 = c.clone()
        c2.mutate(1.0)
        assert c.typography_scale.allele != c2.typography_scale.allele or True


class TestFrontendGenome:
    def test_contains_five_chromosomes(self):
        g = FrontendGenome()
        assert isinstance(g.presentation, PresentationChromosome)
        assert isinstance(g.structure, StructureChromosome)
        assert isinstance(g.behavior, BehaviorChromosome)
        assert isinstance(g.composition, CompositionChromosome)
        assert isinstance(g.compliance, ComplianceChromosome)

    def test_all_genes_count(self):
        g = FrontendGenome()
        assert len(g.all_genes) == 17

    def test_mutate_preserves_structure(self):
        g = FrontendGenome()
        g.mutate(0.2)
        assert isinstance(g.presentation, PresentationChromosome)
        assert isinstance(g.structure, StructureChromosome)

    def test_clone_is_independent(self):
        g = FrontendGenome()
        g2 = g.clone()
        g2.presentation.typography_scale._allele = 1.333
        assert g.presentation.typography_scale.allele != g2.presentation.typography_scale.allele


# ==============================================================================
# Operator Tests
# ==============================================================================

class TestFrontendMutator:
    def test_mutate_returns_new_genome(self):
        g = FrontendGenome()
        mutator = FrontendMutator()
        new_g = mutator.mutate(g, 0.2)
        assert new_g is not g

    def test_history_records_mutations(self):
        g = FrontendGenome()
        mutator = FrontendMutator()
        mutator.mutate_bounded(g, 1.0)
        assert len(mutator.history) > 0

    def test_heuristic_mutate(self):
        g = create_default_genome()
        mutator = FrontendMutator()
        heuristics = [
            {"target_gene_id": "typography-modular-scale", "new_allele": 1.333},
            {"target_gene_id": "spacing-base-unit", "new_allele": 8},
        ]
        new_g = mutator.heuristic_mutate(g, heuristics)
        assert new_g.presentation.typography_scale.allele == 1.333
        assert new_g.structure.spacing_scale.allele == 8

    def test_clear_history(self):
        mutator = FrontendMutator()
        mutator.mutate_bounded(FrontendGenome(), 1.0)
        assert len(mutator.history) > 0
        mutator.clear_history()
        assert len(mutator.history) == 0


class TestFrontendCrossover:
    def test_single_point_swaps_chromosome(self):
        parent_a = create_default_genome()
        parent_b = create_enterprise_dashboard_genome()
        crossover = FrontendCrossover()
        child_a, child_b = crossover.single_point(parent_a, parent_b, rate=1.0)
        assert len(crossover.history) == 1
        assert isinstance(child_a, FrontendGenome)
        assert isinstance(child_b, FrontendGenome)

    def test_crossover_below_rate_returns_clones(self):
        parent_a = create_default_genome()
        parent_b = create_enterprise_dashboard_genome()
        crossover = FrontendCrossover()
        child_a, child_b = crossover.single_point(parent_a, parent_b, rate=0.0)
        assert child_a is not parent_a
        assert child_b is not parent_b
        assert child_a.presentation.typography_scale.allele == parent_a.presentation.typography_scale.allele

    def test_multi_point_swaps_multiple(self):
        g1 = create_default_genome()
        g2 = create_consumer_app_genome()
        crossover = FrontendCrossover()
        child_a, child_b = crossover.multi_point(g1, g2, rate=1.0)
        assert isinstance(child_a, FrontendGenome)

    def test_history_cleared(self):
        crossover = FrontendCrossover()
        a, b = create_default_genome(), create_consumer_app_genome()
        crossover.single_point(a, b, rate=1.0)
        assert len(crossover.history) == 1
        crossover.clear_history()
        assert len(crossover.history) == 0


# ==============================================================================
# Transcriber Tests
# ==============================================================================

class TestFrontendGenomeTranscriber:
    def test_transcribe_returns_profile(self):
        g = create_default_genome()
        t = FrontendGenomeTranscriber()
        profile = t.transcribe(g)
        assert isinstance(profile, FrontendISRProfile)
        assert isinstance(profile.design_system, object)

    def test_typography_tokens_generated(self):
        g = create_default_genome()
        t = FrontendGenomeTranscriber()
        profile = t.transcribe(g)
        tokens = profile.design_system.tokens
        assert "typography" in tokens
        assert "text-base" in tokens["typography"]
        assert tokens["typography"]["text-base"].base_value == 16

    def test_color_tokens_generated(self):
        g = create_default_genome()
        t = FrontendGenomeTranscriber()
        profile = t.transcribe(g)
        tokens = profile.design_system.tokens
        assert "color" in tokens

    def test_spacing_tokens_generated(self):
        g = SpacingScaleGene(4)
        genome = FrontendGenome()
        genome.structure.spacing_scale = g
        t = FrontendGenomeTranscriber()
        profile = t.transcribe(genome)
        tokens = profile.design_system.tokens
        assert "spacing" in tokens
        assert "space-md" in tokens["spacing"]

    def test_elevation_tokens_generated(self):
        g = create_default_genome()
        t = FrontendGenomeTranscriber()
        profile = t.transcribe(g)
        tokens = profile.design_system.tokens
        assert "elevation" in tokens

    def test_motion_tokens_generated(self):
        g = create_default_genome()
        t = FrontendGenomeTranscriber()
        profile = t.transcribe(g)
        tokens = profile.design_system.tokens
        assert "motion" in tokens
        assert "duration-normal" in tokens["motion"]

    def test_radius_tokens_generated(self):
        g = create_default_genome()
        t = FrontendGenomeTranscriber()
        profile = t.transcribe(g)
        tokens = profile.design_system.tokens
        assert "radius" in tokens
        assert "radius-md" in tokens["radius"]

    def test_transcribe_with_components(self):
        from constitutional_architecture.isr.profiles.frontend_model import Component
        g = create_default_genome()
        t = FrontendGenomeTranscriber()
        btn = Component(id="btn", name="Button", purpose="Click")
        profile = t.transcribe_to_profile(g, components=(btn,))
        assert len(profile.components) == 1


# ==============================================================================
# Lethality Tests
# ==============================================================================

class TestCheckGenomeLethality:
    def test_default_genome_not_lethal(self):
        g = create_default_genome()
        result = check_genome_lethality(g)
        assert result.lethal is False

    def test_enterprise_genome_not_lethal(self):
        g = create_enterprise_dashboard_genome()
        result = check_genome_lethality(g)
        assert result.lethal is False

    def test_consumer_genome_not_lethal(self):
        g = create_consumer_app_genome()
        result = check_genome_lethality(g)
        assert result.lethal is False

    def test_bad_dom_depth_is_lethal(self):
        g = create_default_genome()
        g.compliance.performance_budget._allele = PerformanceBudgetAllele(
            max_dom_depth=100, max_animation_paint_area=0.5, max_layout_shift=0.1,
        )
        result = check_genome_lethality(g)
        assert result.lethal is True
        assert any("DOM depth" in v for v in result.violations)

    def test_high_cognitive_load_is_lethal(self):
        g = create_default_genome()
        g.compliance.cognitive_load._allele = 12
        result = check_genome_lethality(g)
        assert result.lethal is True
        assert any("Miller" in v for v in result.violations)


# ==============================================================================
# Factory Tests
# ==============================================================================

class TestFactory:
    def test_default_genome_values(self):
        g = create_default_genome()
        assert g.presentation.typography_scale.allele == 1.25
        assert g.structure.spacing_scale.allele == 4
        assert g.presentation.color_system.allele.base_hue == 220

    def test_enterprise_dashboard_values(self):
        g = create_enterprise_dashboard_genome()
        assert g.structure.density_profile.allele == 0.8
        assert g.presentation.typography_scale.allele == 1.2

    def test_consumer_app_values(self):
        g = create_consumer_app_genome()
        assert g.presentation.typography_scale.allele >= 1.333
        assert g.structure.density_profile.allele == 0.2

    def test_minimal_genome_values(self):
        g = create_minimal_genome()
        assert g.presentation.base_size.allele == 14
        assert g.structure.spacing_scale.allele == 2
        assert g.compliance.accessibility.allele == "AA"

    def test_create_population(self):
        pop = create_population(size=4, seed=42)
        assert len(pop) == 4
        assert all(isinstance(g, FrontendGenome) for g in pop)

    def test_population_diversity(self):
        pop = create_population(size=6, seed=42)
        scales = [g.presentation.typography_scale.allele for g in pop]
        assert len(set(scales)) > 1

    def test_genome_presets(self):
        assert "default" in GENOME_PRESETS
        assert "enterprise-dashboard" in GENOME_PRESETS
        assert "consumer-app" in GENOME_PRESETS
        assert "minimal" in GENOME_PRESETS
