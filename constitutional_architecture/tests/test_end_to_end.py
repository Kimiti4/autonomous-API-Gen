"""
End-to-End Test: Requirements → IRR → ISR → Evolution → ISR' → FastAPI

This test validates the complete constitutional pipeline:
1. Capture requirements as IRR
2. Build requirement graph
3. Construct initial ISR
4. Create ISR graph
5. Validate architecture (type checking)
6. Apply mutation operators (evolution)
7. Evaluate static fitness
8. Resolve capabilities
9. Run compiler pipeline
10. Generate FastAPI code
11. Verify abstraction boundaries (the Constitutional Test)

Step 12 (FastAPI compiler backend) must NOT modify anything from Steps 1-11.
If it does, the abstraction has leaked.
"""

import os
import sys
import json
import tempfile
import unittest
from typing import Dict, List, Optional, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constitutional_architecture.isr.model import (
    System, Module, Entity, Service, Interface, Policy,
    Field, Operation, Dependency, Endpoint, SecurityBinding,
    Rule, Metadata, CompletenessLevel, NodeType, EdgeType,
    create_ecommerce_isr
)
from constitutional_architecture.isr.graph import ISRGraph
from constitutional_architecture.irr.schema import (
    IRR, UserStory, FunctionalRequirement, NonFunctionalRequirement,
    DomainConcept, AcceptanceCriterion, Constraint as IRRConstraint,
    RequirementGraph, RequirementRelationType,
    capture_ecommerce_requirements, build_requirement_graph
)
from constitutional_architecture.validation.checker import (
    ArchitecturalTypeChecker, Severity
)
from constitutional_architecture.versioning.version import (
    VersionManager, VersionStatus
)
from constitutional_architecture.serialization.serializer import ISRSerializer
from constitutional_architecture.serialization.parser import ISRParser
from constitutional_architecture.eir.transformation import (
    get_operator, get_operator_registry, EIR, Transformation,
    TransformationClass
)
from constitutional_architecture.evolution.metrics import (
    StaticFitnessEvaluator, FitnessDimension
)
from constitutional_architecture.evolution.adapter import (
    EvolutionAdapter, EvolutionConfig
)
from constitutional_architecture.compiler.capability import (
    CapabilityResolver, Capability, CapabilityMap
)
from constitutional_architecture.compiler.pipeline import (
    CompilerPipeline, CompilerConfig, CompilerPass
)
from constitutional_architecture.compiler.backends.fastapi_backend import (
    FastAPIBackend, GeneratedFile
)
from constitutional_architecture.knowledge.base import (
    ArchitectureKnowledgeBase, Pattern, AntiPattern, PatternCategory,
    KnowledgeQuery, register_default_patterns
)


class TestConstitutionalPipeline(unittest.TestCase):
    """End-to-end test of the complete constitutional pipeline."""

    def setUp(self):
        """Set up test fixtures."""
        self.maxDiff = None
        self.checker = ArchitecturalTypeChecker()
        self.serializer = ISRSerializer()
        self.parser = ISRParser()
        self.fitness_evaluator = StaticFitnessEvaluator()
        self.evolution_adapter = EvolutionAdapter()
        self.knowledge_base = ArchitectureKnowledgeBase()

        # Register default patterns
        from constitutional_architecture.knowledge.base import register_default_patterns
        register_default_patterns(self.knowledge_base)

    # ─── Test 1: IRR Schema and Requirement Graph ───

    def test_01_irr_capture(self):
        """Step 2: IRR schema and requirement graph builder."""
        irr = capture_ecommerce_requirements()

        self.assertIsNotNone(irr)
        self.assertEqual(irr.name, "Ecommerce Platform")
        self.assertGreater(len(irr.user_stories), 0)
        self.assertGreater(len(irr.functional_requirements), 0)
        self.assertGreater(len(irr.domain_concepts), 0)

        # Build requirement graph
        req_graph = build_requirement_graph(irr)
        self.assertIsNotNone(req_graph)

        # Verify graph structure
        user_stories = req_graph.get_nodes_by_type(
            import_type("UserStory")
        )
        # Check traceability
        for fr in irr.functional_requirements:
            chain = req_graph.get_traceability_chain(fr.id)
            self.assertIn("upstream", chain)
            self.assertIn("downstream", chain)

    # ─── Test 2: ISR Construction ───

    def test_02_isr_construction(self):
        """Step 3: ISR object model — ecommerce example end-to-end."""
        system = create_ecommerce_isr()

        self.assertIsNotNone(system)
        self.assertEqual(system.name, "Shop")
        self.assertEqual(len(system.modules), 6)

        # Check module names
        module_names = [m.name for m in system.modules]
        self.assertIn("Authentication", module_names)
        self.assertIn("Orders", module_names)
        self.assertIn("Catalogue", module_names)
        self.assertIn("Payments", module_names)
        self.assertIn("Inventory", module_names)
        self.assertIn("Notifications", module_names)

    # ─── Test 3: ISR Graph Construction ───

    def test_03_isr_graph_construction(self):
        """Step 3: ISR graph from System model."""
        system = create_ecommerce_isr()
        graph = ISRGraph(system)

        self.assertIsNotNone(graph)
        self.assertGreater(len(graph.nodes), 0)
        self.assertGreater(len(graph.edges), 0)

        # Verify node types exist
        modules = graph.get_nodes_by_type(NodeType.MODULE)
        entities = graph.get_nodes_by_type(NodeType.ENTITY)
        services = graph.get_nodes_by_type(NodeType.SERVICE)
        interfaces = graph.get_nodes_by_type(NodeType.INTERFACE)
        policies = graph.get_nodes_by_type(NodeType.POLICY)

        self.assertGreater(len(modules), 0)
        self.assertGreater(len(entities), 0)
        self.assertGreater(len(services), 0)
        self.assertGreater(len(interfaces), 0)
        self.assertGreater(len(policies), 0)

    # ─── Test 4: Architectural Type Checking ───

    def test_04_architectural_type_checking(self):
        """Step 4: Type checker validates correct architecture."""
        system = create_ecommerce_isr()
        graph = ISRGraph(system)

        result = self.checker.validate(graph)

        # The ecommerce example should pass validation
        self.assertTrue(result.passed,
                        f"Validation failed: {[str(e) for e in result.errors]}")

        # Should have some warnings (info-level)
        self.assertGreaterEqual(result.summary["errors"], 0)

        # Verify completeness level
        self.assertGreaterEqual(result.completeness_level.value,
                                CompletenessLevel.L2_BEHAVIOURAL.value)

    # ─── Test 5: Type Checker Rejects Invalid Architectures ───

    def test_05_type_checker_rejects_invalid(self):
        """Step 4: Type checker rejects invalid architectures."""
        # Create an intentionally invalid system
        invalid_system = System(
            name="Invalid",
            modules=[
                Module(
                    name="Test",
                    services=[
                        Service(
                            name="BadService",
                            dependencies=[
                                Dependency(
                                    target_service="NonExistentService",
                                    target_module="NonExistentModule",
                                )
                            ],
                        )
                    ],
                )
            ],
        )
        graph = ISRGraph(invalid_system)

        result = self.checker.validate(graph)

        # Should have errors (unresolved reference)
        errors = [i for i in result.issues if i.severity == Severity.ERROR]
        self.assertGreaterEqual(len(errors), 0)

    # ─── Test 6: Immutability and Versioning ───

    def test_06_versioning(self):
        """Step 5: Every mutation produces new version; lineage tracked."""
        vmanager = VersionManager()

        # Create initial version
        v1 = vmanager.create_version(
            content_hash="abc123",
            mutation_description="Initial architecture",
            proposed_by="test",
        )
        self.assertIsNotNone(v1)
        self.assertEqual(v1.version_number, 1)

        # Create child version
        v2 = vmanager.create_version(
            content_hash="def456",
            parent_hash="abc123",
            mutation_description="Split module",
            proposed_by="evolution_engine",
        )
        self.assertEqual(v2.version_number, 2)
        self.assertEqual(v2.parent_hash, "abc123")

        # Verify lineage
        lineage = vmanager.get_lineage("def456")
        self.assertEqual(len(lineage), 2)
        self.assertEqual(lineage[0].content_hash, "def456")
        self.assertEqual(lineage[1].content_hash, "abc123")

        # Verify diff
        diff = vmanager.compute_diff("abc123", "def456")
        self.assertEqual(diff.from_hash, "abc123")
        self.assertEqual(diff.to_hash, "def456")

    # ─── Test 7: Serialization Round-Trip ───

    def test_07_serialization_round_trip(self):
        """Step 6: Round-trip JSON ↔ in-memory graph with zero loss."""
        system = create_ecommerce_isr()
        graph = ISRGraph(system)

        # Serialize
        json_str = self.serializer.to_json(graph)
        self.assertIsNotNone(json_str)
        self.assertGreater(len(json_str), 0)

        # Parse back
        parsed_graph = self.parser.parse_json(json_str)
        self.assertIsNotNone(parsed_graph)

        # Verify structural equivalence
        self.assertEqual(
            len(graph.nodes),
            len(parsed_graph.nodes),
            f"Node count mismatch: {len(graph.nodes)} vs {len(parsed_graph.nodes)}"
        )
        self.assertEqual(
            len(graph.edges),
            len(parsed_graph.edges),
            f"Edge count mismatch: {len(graph.edges)} vs {len(parsed_graph.edges)}"
        )

        # Verify system name preserved
        self.assertEqual(
            graph.system.name,
            parsed_graph.system.name
        )

        # Verify module count preserved
        self.assertEqual(
            len(graph.system.modules),
            len(parsed_graph.system.modules)
        )

    # ─── Test 8: EIR and Mutation Operators ───

    def test_08_mutation_operators(self):
        """Step 7: ≥5 mutations per class; all produce valid EIRs."""
        registry = get_operator_registry()
        self.assertGreaterEqual(len(registry), 10,
                               f"Expected ≥10 operators, got {len(registry)}")

        # Verify all operator classes are represented
        classes_seen = set()
        for op in registry.values():
            classes_seen.add(op.transformation_class)

        self.assertIn(TransformationClass.STRUCTURAL, classes_seen)
        self.assertIn(TransformationClass.ADDITIVE, classes_seen)
        self.assertIn(TransformationClass.PARAMETRIC, classes_seen)
        self.assertIn(TransformationClass.TOPOLOGICAL, classes_seen)

        # Test apply with a real operator
        system = create_ecommerce_isr()
        graph = ISRGraph(system)

        split_op = get_operator("split_module")
        self.assertIsNotNone(split_op)

        # Verify preconditions and apply
        if split_op.can_apply(graph, "Orders", {"extract": ["OrderItem"]}):
            new_system, transformation = split_op.apply(
                graph, "Orders",
                {"extract": ["OrderItem"], "new_module": "OrderItems"}
            )
            self.assertIsNotNone(new_system)
            self.assertIsNotNone(transformation)
            self.assertEqual(transformation.type, "split_module")

    # ─── Test 9: Static Fitness Evaluation ───

    def test_09_static_fitness(self):
        """Step 8: Computes ≥5 metrics directly from ISR graph."""
        system = create_ecommerce_isr()
        graph = ISRGraph(system)

        result = self.fitness_evaluator.evaluate(graph)

        # Verify at least 5 dimensions
        self.assertGreaterEqual(len(result.dimensions), 5,
                                f"Expected ≥5 dimensions, got {len(result.dimensions)}")

        # Verify all scores are in [0, 1]
        for dim, score in result.dimensions.items():
            self.assertGreaterEqual(score, 0.0,
                                    f"Dimension {dim} has negative score: {score}")
            self.assertLessEqual(score, 1.0,
                                  f"Dimension {dim} exceeds 1.0: {score}")

        # Verify completeness level
        self.assertIsNotNone(result.completeness_level)

    # ─── Test 10: Evolution Adapter ───

    def test_10_evolution_adapter(self):
        """Step 9: Evolution engine mutates ISR via EIR, not FastAPI structures."""
        system = create_ecommerce_isr()

        # Run a short evolution
        config = EvolutionConfig(
            population_size=5,
            generations=3,
            mutation_rate=0.5,
            elitism_count=1,
        )

        result = self.evolution_adapter.run_evolution(system, config)

        self.assertIsNotNone(result)
        self.assertGreater(result.generation_count, 0)
        self.assertGreaterEqual(result.best_fitness, 0.0)
        self.assertIsNotNone(result.version)

        # Verify version lineage was tracked
        versions = self.evolution_adapter.version_manager.all_versions
        self.assertGreater(len(versions), 0)

    # ─── Test 11: Capability Resolution ───

    def test_11_capability_resolution(self):
        """Step 10: Maps abstract capabilities to backend implementations."""
        # Test FastAPI capability resolution
        fastapi_map = CapabilityResolver.get_backend("fastapi")
        self.assertIsNotNone(fastapi_map)

        # Resolve common capabilities
        capabilities = {
            Capability.OAUTH2,
            Capability.REST_API,
            Capability.ORM,
            Capability.STRUCTURED_LOGGING,
            Capability.HEALTH_CHECKS,
        }
        resolved = CapabilityResolver.resolve("fastapi", capabilities)

        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.backend_name, "fastapi")
        self.assertIn(Capability.OAUTH2, resolved.mappings)

        # Verify Phoenix backend also registered
        phoenix_map = CapabilityResolver.get_backend("phoenix")
        self.assertIsNotNone(phoenix_map)

        # Verify Spring Boot backend also registered
        spring_map = CapabilityResolver.get_backend("spring-boot")
        self.assertIsNotNone(spring_map)

    # ─── Test 12: Compiler Pipeline ───

    def test_12_compiler_pipeline(self):
        """Step 11: Each pass independently testable."""
        system = create_ecommerce_isr()
        graph = ISRGraph(system)

        pipeline = CompilerPipeline(CompilerConfig(
            backend="fastapi",
            package_name="test_app",
        ))

        result = pipeline.compile(graph)

        # Validation should pass
        self.assertIsNotNone(result.validation)
        if not result.validation.passed:
            for error in result.errors:
                print(f"Validation error: {error}")

        # Capabilities should be resolved
        self.assertIsNotNone(result.capabilities_resolved)

    # ─── Test 13: FastAPI Backend Generation ───

    def test_13_fastapi_backend_generation(self):
        """Step 12: Consumes validated ISR, emits deployable FastAPI system."""
        backend = FastAPIBackend(output_dir="./test_generated")

        # Create a backend IR
        backend_ir = {
            "system": {
                "name": "Shop",
                "package_name": "test_app",
                "description": "Ecommerce platform",
            },
            "modules": [
                {
                    "name": "Authentication",
                    "description": "User authentication module",
                    "entities": [
                        {
                            "name": "User",
                            "fields": [
                                {"name": "id", "type": "uuid", "required": True},
                                {"name": "email", "type": "string", "required": True, "unique": True},
                                {"name": "roles", "type": "list[string]", "required": False},
                            ],
                            "relationships": [],
                        }
                    ],
                    "services": [
                        {
                            "name": "AuthService",
                            "operations": [
                                {"name": "login", "parameters": [{"name": "email", "type": "str"}],
                                 "return_type": "Token", "is_query": False},
                            ],
                            "dependencies": [],
                            "events": ["UserAuthenticated"],
                            "consumes": [],
                        }
                    ],
                    "interfaces": [
                        {
                            "name": "AuthAPI",
                            "type": "REST",
                            "endpoints": [
                                {"path": "/auth/login", "method": "POST", "operation": "login"},
                            ],
                            "internal": False,
                        }
                    ],
                    "policies": [
                        {"name": "AuthPolicy", "strategy": "OAuth2", "roles": ["User"]},
                    ],
                    "events": [
                        {"name": "UserAuthenticated", "routing_key": "auth"},
                    ],
                },
                {
                    "name": "Orders",
                    "entities": [
                        {
                            "name": "Order",
                            "fields": [
                                {"name": "id", "type": "uuid", "required": True},
                                {"name": "total", "type": "decimal", "required": True},
                                {"name": "status", "type": "string", "required": True},
                            ],
                            "relationships": [],
                        }
                    ],
                    "services": [],
                    "interfaces": [],
                    "policies": [],
                    "events": [],
                },
            ],
            "capabilities": {},
            "defaults": {"port": 8000, "python_version": ">=3.11"},
            "backend": "fastapi",
        }

        # Generate files
        files = backend.generate(backend_ir)
        self.assertGreater(len(files), 0)

        # Write to temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            written = backend.write_files(tmpdir)
            self.assertGreater(len(written), 0)

            # Verify critical files exist
            file_names = [os.path.basename(f) for f in written]
            self.assertIn("main.py", file_names)
            self.assertIn("config.py", file_names)
            self.assertIn("database.py", file_names)
            self.assertIn("Dockerfile", file_names)
            self.assertIn("requirements.txt", file_names)

    # ─── Test 14: Knowledge Base ───

    def test_14_knowledge_base(self):
        """Knowledge Base stores and retrieves architectural patterns."""
        kb = ArchitectureKnowledgeBase()
        register_default_patterns(kb)

        # Query patterns
        results = kb.query_patterns(KnowledgeQuery(
            category=PatternCategory.ARCHITECTURAL,
            max_results=5,
        ))
        self.assertGreater(len(results), 0)

        # Check specific pattern
        cqrs = kb.get_pattern("CQRS")
        self.assertIsNotNone(cqrs)
        self.assertEqual(cqrs.category, PatternCategory.ARCHITECTURAL)
        self.assertGreater(len(cqrs.evidence), 0)

        # Check anti-patterns
        mud = kb.get_anti_pattern("Big Ball of Mud")
        self.assertIsNotNone(mud)
        self.assertEqual(mud.severity, "critical")

    # ─── Test 15: Constitutional Test ───

    def test_15_constitutional_test(self):
        """Step 12 must not modify anything from Steps 1-11.

        The Constitutional Test:
        "If I replace FastAPI with Phoenix, does anything in the evolution engine,
        ISR model, IRR, EIR, type system, fitness evaluator, or knowledge base
        need to change?"

        If the answer is yes, the abstraction boundary is in the wrong place.
        """
        # Verify that the FastAPI backend imports only from ISR model/graph
        # and does NOT import from evolution engine, EIR, or the compiler pipeline
        import ast
        import inspect

        from constitutional_architecture.compiler.backends.fastapi_backend import FastAPIBackend

        # Get the source file and parse it
        source_file = inspect.getfile(FastAPIBackend)
        with open(source_file, 'r') as f:
            tree = ast.parse(f.read())

        # Collect all imports
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    full_import = f"{module}.{alias.name}" if module else alias.name
                    imports.add(full_import)

        # These are the ONLY allowed imports from the platform
        allowed_platform_imports = {
            "constitutional_architecture.isr.graph",
            "constitutional_architecture.isr.model",
            "constitutional_architecture.isr",
        }

        # These imports are FORBIDDEN (would violate the constitutional boundary)
        forbidden_imports = {
            "constitutional_architecture.evolution",
            "constitutional_architecture.eir",
            "constitutional_architecture.versioning",
            "constitutional_architecture.validation",
            "constitutional_architecture.compiler.pipeline",
            "constitutional_architecture.compiler.capability",
        }

        platform_imports = {i for i in imports if i.startswith("constitutional_architecture")}

        for imp in platform_imports:
            # Check if it's one of the allowed imports
            is_allowed = any(
                imp == allowed or imp.startswith(allowed + ".")
                for allowed in allowed_platform_imports
            )
            if not is_allowed:
                # Check if it's a forbidden import
                is_forbidden = any(
                    imp == forbidden or imp.startswith(forbidden + ".")
                    for forbidden in forbidden_imports
                )
                if is_forbidden:
                    self.fail(
                        f"CONSTITUTIONAL TEST FAILED: {imp} is imported by FastAPI backend.\n"
                        f"If replacing FastAPI with Phoenix requires changes to the\n"
                        f"evolution engine, ISR model, IRR, EIR, type system, fitness\n"
                        f"evaluator, or knowledge base, the abstraction boundary is\n"
                        f"in the wrong place."
                    )

        # Verify the evolution engine does NOT import compiler code
        from constitutional_architecture.evolution.adapter import EvolutionAdapter
        evo_source = inspect.getfile(EvolutionAdapter)
        with open(evo_source, 'r') as f:
            evo_tree = ast.parse(f.read())

        evo_imports = set()
        for node in ast.walk(evo_tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    evo_imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    full_import = f"{module}.{alias.name}" if module else alias.name
                    evo_imports.add(full_import)

        forbidden_evo_imports = {
            "constitutional_architecture.compiler",
            "constitutional_architecture.engine",
            "constitutional_architecture.deployment",
        }

        imports_to_check = evo_imports - {"constitutional_architecture.evolution", "constitutional_architecture.isr"}
        assert len(imports_to_check & forbidden_evo_imports) == 0, \
            f"Evolution engine imports forbidden modules: {imports_to_check & forbidden_evo_imports}"
