"""
Tests for FEE Phases 4-12: Knowledge Graph, Evaluators, Evolution Coordinator,
Compilers, Component Runtime, Visual Intelligence, and Memory.
"""

from constitutional_architecture.meta.genome.knowledge_graph.iknowledge_graph import (
    IKnowledgeGraph, DesignPattern, GenomeModifier, ChromosomeTarget,
    ModifierOperation, PatternCategory, ContextTag,
)
from constitutional_architecture.meta.genome.knowledge_graph.in_memory_graph import InMemoryKnowledgeGraph
from constitutional_architecture.meta.genome.seeder.heuristic_injector import HeuristicInjector
from constitutional_architecture.meta.genome.evaluators.concrete_evaluators import (
    TokenConsistencyEvaluator, AccessibilityEvaluator,
    VisualHierarchyEvaluator, CompositeFitness, FitnessDimension,
)
from constitutional_architecture.meta.genome.evolution.pareto_coordinator import (
    ParetoEvolutionCoordinator, Candidate,
)
from constitutional_architecture.meta.genome.compilers.i_frontend_compiler import (
    TailwindCompiler, CompiledArtifact,
)
from constitutional_architecture.meta.genome.components.component_api_mutator import (
    ComponentAPIMutator, ComponentAPIMutation,
)
from constitutional_architecture.meta.genome.visual_intel.headless_analyzer import (
    VisualIntelligenceEvaluator,
)
from constitutional_architecture.meta.genome.memory.constitutional_memory import (
    InMemoryConstitutionalMemory, EvolutionarySnapshot, TasteModelUpdater,
)
from constitutional_architecture.meta.genome.factory import (
    create_default_genome, create_enterprise_dashboard_genome,
    create_consumer_app_genome,
)
from constitutional_architecture.meta.genome.transcriber import FrontendGenomeTranscriber
from constitutional_architecture.isr.profiles.frontend_model import (
    FrontendISRProfile, DesignSystem, Component, ComponentNode,
    TokenDefinition, Layout, Page, GenomeMapping, ChromosomeFamily,
    AccessibilityContract, PropertyDefinition, EventDefinition,
)


# ==============================================================================
# Phase 4: Knowledge Graph Tests
# ==============================================================================

class TestKnowledgeGraphInterface:
    def test_resolve_patterns_by_context(self):
        kg = InMemoryKnowledgeGraph()
        patterns = kg.resolve_patterns(["dashboard", "analytics"])
        assert len(patterns) > 0
        names = [p.name for p in patterns]
        assert "Enterprise Data Dashboard" in names

    def test_resolve_empty_tags_returns_all(self):
        kg = InMemoryKnowledgeGraph()
        patterns = kg.resolve_patterns([])
        assert len(patterns) == kg.pattern_count

    def test_get_pattern_by_id(self):
        kg = InMemoryKnowledgeGraph()
        pat = kg.get_pattern("pat-001")
        assert pat is not None
        assert pat.name == "Enterprise Data Dashboard"

    def test_get_pattern_missing(self):
        kg = InMemoryKnowledgeGraph()
        assert kg.get_pattern("pat-999") is None

    def test_conflicting_patterns(self):
        kg = InMemoryKnowledgeGraph()
        conflicts = kg.get_conflicting("pat-001")
        assert len(conflicts) == 1
        assert conflicts[0].name == "Consumer Marketing Landing"

    def test_register_pattern(self):
        kg = InMemoryKnowledgeGraph()
        new_pat = DesignPattern(
            id="pat-999", name="Custom Pattern", category=PatternCategory.COLOR,
            description="Test",
            genome_modifiers=(
                GenomeModifier(ChromosomeTarget.PRESENTATION, "typography-modular-scale", ModifierOperation.SET, 1.25),
            ),
        )
        kg.register_pattern(new_pat)
        assert kg.get_pattern("pat-999") is not None
        assert kg.pattern_count > 1

    def test_pattern_genome_modifiers(self):
        kg = InMemoryKnowledgeGraph()
        pat = kg.get_pattern("pat-001")
        assert pat is not None
        assert len(pat.genome_modifiers) > 0
        mod = pat.genome_modifiers[0]
        assert mod.target_chromosome == ChromosomeTarget.PRESENTATION
        assert mod.target_gene == "typography-modular-scale"
        assert mod.operation == ModifierOperation.SET
        assert mod.value == 1.125


class TestHeuristicInjector:
    def test_inject_patterns_into_genome(self):
        kg = InMemoryKnowledgeGraph()
        genome = create_default_genome()
        patterns = kg.resolve_patterns(["dashboard", "enterprise"])
        injector = HeuristicInjector()
        injector.inject(patterns, genome)

        assert genome.presentation.typography_scale.allele == 1.125
        assert genome.structure.spacing_scale.allele == 4
        assert genome.structure.density_profile.allele == 0.8

    def test_inject_multiplicative(self):
        genome = create_default_genome()
        patterns = [
            DesignPattern(
                id="test-pat", name="Test", category=PatternCategory.LAYOUT,
                description="",
                genome_modifiers=(
                    GenomeModifier(ChromosomeTarget.STRUCTURE, "density-profile", ModifierOperation.MULTIPLY, 2.0),
                ),
            )
        ]
        HeuristicInjector().inject(patterns, genome)
        assert genome.structure.density_profile.allele == 1.0  # clamped by bounds

    def test_inject_only_matching_patterns(self):
        kg = InMemoryKnowledgeGraph()
        genome = create_consumer_app_genome()
        patterns = kg.resolve_patterns(["table", "data-grid"])
        injector = HeuristicInjector()
        injector.inject(patterns, genome)

        assert genome.structure.spacing_scale.allele == 2
        assert genome.structure.density_profile.allele == 0.9

    def test_inject_into_complex_genome(self):
        kg = InMemoryKnowledgeGraph()
        genome = create_enterprise_dashboard_genome()
        patterns = kg.resolve_patterns(["dark-mode"])
        injector = HeuristicInjector()
        injector.inject(patterns, genome)

        assert genome.presentation.elevation.allele == 0.2
        assert genome.presentation.color_system.allele.base_hue == 220
        assert genome.presentation.color_system.allele.saturation == 0.4


# ==============================================================================
# Phase 5: Evaluator Tests
# ==============================================================================

class TestTokenConsistencyEvaluator:
    def test_all_components_use_tokens(self):
        ds = DesignSystem(id="ds", name="DS",
            tokens={"color": {"p": TokenDefinition("p", "P", "color", "#000")}},
        )
        comp = Component(id="btn", name="Button", purpose="Action",
                         token_dependencies=("color-p",))
        profile = FrontendISRProfile(ds, components=(comp,))
        result = TokenConsistencyEvaluator().evaluate(profile)
        assert result.score >= 0.9

    def test_component_missing_tokens_penalized(self):
        ds = DesignSystem(id="ds", name="DS",
            tokens={"color": {"p": TokenDefinition("p", "P", "color", "#000")}},
        )
        comp = Component(id="btn", name="Button", purpose="Action",
                         token_dependencies=())
        profile = FrontendISRProfile(ds, components=(comp,))
        result = TokenConsistencyEvaluator().evaluate(profile)
        assert result.score < 0.9

    def test_no_profile_returns_zero(self):
        result = TokenConsistencyEvaluator().evaluate(None)
        assert result.score == 0.0


class TestAccessibilityEvaluator:
    def test_components_with_accessibility(self):
        comp = Component(id="btn", name="Button", purpose="Action",
                         accessibility_contract=AccessibilityContract(
                             aria_role="button", focus_management="sequential",
                         ),
                         states=("default", "hover", "focus"))
        ds = DesignSystem(id="ds", name="DS",
            tokens={"color": {"p": TokenDefinition("p", "P", "color", "#000")}},
        )
        profile = FrontendISRProfile(ds, components=(comp,))
        result = AccessibilityEvaluator().evaluate(profile)
        assert result.score >= 0.8

    def test_missing_aria_role_warns(self):
        comp = Component(id="btn", name="Button", purpose="Action",
                         accessibility_contract=AccessibilityContract(),
                         states=("default",))
        ds = DesignSystem(id="ds", name="DS",
            tokens={"color": {"p": TokenDefinition("p", "P", "color", "#000")}},
        )
        profile = FrontendISRProfile(ds, components=(comp,))
        result = AccessibilityEvaluator().evaluate(profile)
        assert len(result.violations) > 0


class TestCompositeFitness:
    def test_composite_score(self):
        dims = [
            FitnessDimension("A", 1.0, weight=0.5),
            FitnessDimension("B", 0.5, weight=0.5),
        ]
        cf = CompositeFitness(dims)
        assert cf.composite_score == 0.75

    def test_composite_zero_weight(self):
        cf = CompositeFitness([])
        assert cf.composite_score == 0.0

    def test_all_violations_aggregated(self):
        dims = [
            FitnessDimension("A", 0.5, weight=1.0, violations=("v1", "v2")),
            FitnessDimension("B", 0.5, weight=1.0, violations=("v3",)),
        ]
        cf = CompositeFitness(dims)
        assert len(cf.all_violations) == 3


# ==============================================================================
# Phase 6: Evolution Coordinator Tests
# ==============================================================================

class TestParetoEvolutionCoordinator:
    def test_run_generation(self):
        genome = create_default_genome()
        coordinator = ParetoEvolutionCoordinator()
        evaluators = [TokenConsistencyEvaluator(), AccessibilityEvaluator()]
        result = coordinator.run_generation([genome, genome.clone()], evaluators)
        assert result.survivors is not None
        assert len(result.next_generation) == 2

    def test_multiple_generations(self):
        genome = create_default_genome()
        coordinator = ParetoEvolutionCoordinator()
        evaluators = [TokenConsistencyEvaluator()]
        pop = [genome, genome.clone(), create_enterprise_dashboard_genome(), create_consumer_app_genome()]
        for _ in range(3):
            result = coordinator.run_generation(pop, evaluators)
            pop = result.next_generation
        assert coordinator.generation == 3

    def test_genome_with_lethality_removed(self):
        genome = create_default_genome()
        genome.compliance.cognitive_load._allele = 12
        coordinator = ParetoEvolutionCoordinator()
        result = coordinator.run_generation([genome], [TokenConsistencyEvaluator()])
        assert len(result.survivors) == 0


# ==============================================================================
# Phase 7/12: Compiler Tests
# ==============================================================================

class TestTailwindCompiler:
    def test_compile_tokens_generates_config(self):
        ds = DesignSystem(id="ds", name="DS",
            tokens={
                "color": {"primary": TokenDefinition("primary", "Primary", "color", "#2563EB")},
                "spacing": {"md": TokenDefinition("md", "Medium", "spacing", "16px")},
                "typography": {"base": TokenDefinition("base", "Base", "typography", 16)},
            },
        )
        profile = FrontendISRProfile(ds)
        compiler = TailwindCompiler()
        artifact = compiler.compile_tokens(profile)
        assert artifact.format == "tailwind-config"
        assert "tailwindcss" in artifact.dependencies
        assert "colors" in artifact.content
        assert "spacing" in artifact.content

    def test_compile_missing_component_returns_error(self):
        ds = DesignSystem(id="ds", name="DS")
        profile = FrontendISRProfile(ds)
        artifact = TailwindCompiler().compile_component(profile, "nonexistent")
        assert artifact.format == "error"

    def test_compile_component_generates_skeleton(self):
        comp = Component(id="card", name="ProductCard", purpose="Displays product",
                         states=("default", "hover"), allowed_children=("Badge",))
        ds = DesignSystem(id="ds", name="DS")
        profile = FrontendISRProfile(ds, components=(comp,))
        artifact = TailwindCompiler().compile_component(profile, "card")
        assert "ProductCard" in artifact.content
        assert "hover" in artifact.content


# ==============================================================================
# Phase 8: Component API Mutator Tests
# ==============================================================================

class TestComponentAPIMutator:
    def test_refactor_few_props_no_op(self):
        comp = Component(id="btn", name="Button", purpose="Action",
                         inputs=(PropertyDefinition("label", "string", True),))
        ds = DesignSystem(id="ds", name="DS")
        profile = FrontendISRProfile(ds, components=(comp,))
        mutator = ComponentAPIMutator()
        mutations = mutator.refactor_props_to_objects(profile, "btn")
        assert len(mutations) == 0

    def test_refactor_many_props_groups_them(self):
        inputs = tuple(
            PropertyDefinition(f"prop_{i}", "string")
            for i in range(6)
        )
        comp = Component(id="card", name="Card", purpose="Display", inputs=inputs)
        ds = DesignSystem(id="ds", name="DS")
        profile = FrontendISRProfile(ds, components=(comp,))
        mutator = ComponentAPIMutator()
        mutations = mutator.refactor_props_to_objects(profile, "card")
        assert len(mutations) > 0
        assert mutations[0].component_id == "card"

    def test_inject_state(self):
        comp = Component(id="btn", name="Button", purpose="Action",
                         states=("default",))
        ds = DesignSystem(id="ds", name="DS")
        profile = FrontendISRProfile(ds, components=(comp,))
        mutator = ComponentAPIMutator()
        mutation = mutator.inject_state(profile, "btn", "loading")
        assert mutation is not None
        assert mutation.mutation_type == "inject_state"

    def test_inject_duplicate_state_returns_none(self):
        comp = Component(id="btn", name="Button", purpose="Action",
                         states=("default",))
        ds = DesignSystem(id="ds", name="DS")
        profile = FrontendISRProfile(ds, components=(comp,))
        mutator = ComponentAPIMutator()
        mutation = mutator.inject_state(profile, "btn", "default")
        assert mutation is None


# ==============================================================================
# Phase 9: Visual Intelligence Tests
# ==============================================================================

class TestVisualIntelligenceEvaluator:
    def test_empty_profile_penalized(self):
        ds = DesignSystem(id="ds", name="DS",
            tokens={"color": {"p": TokenDefinition("p", "P", "color", "#000")}},
        )
        profile = FrontendISRProfile(ds)
        result = VisualIntelligenceEvaluator().evaluate(profile)
        assert result.score < 0.9

    def test_rich_profile_scores_well(self):
        ds = DesignSystem(id="ds", name="DS",
            tokens={
                "color": {"p": TokenDefinition("p", "P", "color", "#000")},
                "spacing": {"m": TokenDefinition("m", "M", "spacing", "16px")},
                "typography": {"b": TokenDefinition("b", "B", "typography", 16)},
            },
        )
        comp = Component(id="btn", name="Button", purpose="Action",
                         states=("default", "hover", "focus"))
        layout = Layout(id="main", name="Main Layout")
        page = Page(id="home", name="Home", route_pattern="/", layout_ref="main",
                    component_tree=ComponentNode("Home"))
        profile = FrontendISRProfile(ds, components=(comp,), layouts=(layout,), pages=(page,))
        result = VisualIntelligenceEvaluator().evaluate(profile)
        assert result.score > 0.5

    def test_no_profile_returns_zero(self):
        result = VisualIntelligenceEvaluator().evaluate(None)
        assert result.score == 0.0


# ==============================================================================
# Phase 10/11: Memory & Taste Model Tests
# ==============================================================================

class TestInMemoryConstitutionalMemory:
    def test_save_and_retrieve(self):
        mem = InMemoryConstitutionalMemory()
        snapshot = EvolutionarySnapshot(pareto_rank=1)
        mem.save_snapshot(snapshot)
        assert mem.snapshot_count == 1

    def test_get_high_performers(self):
        mem = InMemoryConstitutionalMemory()
        dim = FitnessDimension("Test", 0.95, 1.0)
        mem.save_snapshot(EvolutionarySnapshot(fitness_scores=(dim,), pareto_rank=0))
        mem.save_snapshot(EvolutionarySnapshot(pareto_rank=1))
        winners = mem.get_high_performers("Test", limit=5)
        assert len(winners) == 1

    def test_no_high_performers(self):
        mem = InMemoryConstitutionalMemory()
        winners = mem.get_high_performers("Nonexistent")
        assert len(winners) == 0

    def test_get_all_snapshots(self):
        mem = InMemoryConstitutionalMemory()
        mem.save_snapshot(EvolutionarySnapshot())
        mem.save_snapshot(EvolutionarySnapshot())
        assert len(mem.get_all_snapshots()) == 2


class TestTasteModelUpdater:
    def test_update_no_data_returns_empty(self):
        mem = InMemoryConstitutionalMemory()
        updater = TasteModelUpdater()
        result = updater.update_taste_weights(mem, None)
        assert result["updated"] == 0

    def test_update_with_genome_data(self):
        mem = InMemoryConstitutionalMemory()
        genome = create_default_genome()
        dim = FitnessDimension("Design System Consistency", 0.95, 1.0)
        mem.save_snapshot(EvolutionarySnapshot(
            genome=genome, fitness_scores=(dim,), pareto_rank=0,
        ))
        updater = TasteModelUpdater()
        result = updater.update_taste_weights(mem, None)
        assert result["updated"] > 0


# ==============================================================================
# Integrated E2E: Phase 4-6 Pipeline
# ==============================================================================

class TestPhases4to6Integration:
    def test_knowledge_graph_to_evolution(self):
        kg = InMemoryKnowledgeGraph()
        genome = create_default_genome()
        patterns = kg.resolve_patterns(["dashboard"])
        HeuristicInjector().inject(patterns, genome)
        assert genome.presentation.typography_scale.allele == 1.125

        coordinator = ParetoEvolutionCoordinator()
        evaluators = [TokenConsistencyEvaluator(), AccessibilityEvaluator()]
        result = coordinator.run_generation(
            [genome, genome.clone(), create_enterprise_dashboard_genome()],
            evaluators,
        )
        assert len(result.survivors) > 0

    def test_all_evaluators_run_without_error(self):
        ds = DesignSystem(id="ds", name="DS",
            tokens={
                "color": {"p": TokenDefinition("p", "P", "color", "#000")},
                "spacing": {"m": TokenDefinition("m", "M", "spacing", "16px")},
            },
        )
        comp = Component(id="btn", name="Button", purpose="Action",
                         token_dependencies=("color-p",),
                         accessibility_contract=AccessibilityContract(
                             aria_role="button", focus_management="sequential",
                         ),
                         states=("default", "hover"))
        profile = FrontendISRProfile(ds, components=(comp,))

        results = [
            TokenConsistencyEvaluator().evaluate(profile),
            AccessibilityEvaluator().evaluate(profile),
            VisualHierarchyEvaluator().evaluate(profile),
            VisualIntelligenceEvaluator().evaluate(profile),
        ]
        for r in results:
            assert 0.0 <= r.score <= 1.0

    def test_full_pipeline_generates_compile_artifact(self):
        kg = InMemoryKnowledgeGraph()
        genome = create_default_genome()
        patterns = kg.resolve_patterns(["ecommerce", "checkout"])
        HeuristicInjector().inject(patterns, genome)

        transcriber = FrontendGenomeTranscriber()
        profile = transcriber.transcribe(genome, "E-Commerce Checkout")

        compiler = TailwindCompiler()
        artifact = compiler.compile_tokens(profile)
        assert "module.exports" in artifact.content
        assert "spacing" in artifact.content
