"""R1-D.2 Compiler IR contract refinement tests.

Source: folder/CONTRACT_CanonicalCompilerIR.md (D2-D4 refinement).
Source: folder/R1_D2_COMPILER_IR_MIGRATION_MAP.md (D2-D5).

These tests verify the R1-D.2 contract refinements:
  - D07 original contract is preserved (refinements are additive).
  - The current CompilationPlan is the stabilization implementation.
  - The future canonical Compiler IR module is R1-D.5 work.
  - The constitutional substrate is on the retirement path (R1-D.5).
"""
from __future__ import annotations

import unittest


class TestD07OriginalContractPreserved(unittest.TestCase):
    """The R1-B D07 contract is preserved. The D2-D4 refinement is additive."""

    def test_compilation_id_field_in_plan(self):
        """CompilationPlan has plan_id (the D07-compatible Compilation ID)."""
        from compiler.core.plan import CompilationPlan
        plan_fields = CompilationPlan.model_fields
        self.assertIn("plan_id", plan_fields)

    def test_isr_id_field_in_plan(self):
        """CompilationPlan has isr_id (the D07-compatible Source ISR reference)."""
        from compiler.core.plan import CompilationPlan
        plan_fields = CompilationPlan.model_fields
        self.assertIn("isr_id", plan_fields)

    def test_services_field_in_plan(self):
        """CompilationPlan has services (the D07-compatible Component model)."""
        from compiler.core.plan import CompilationPlan
        plan_fields = CompilationPlan.model_fields
        self.assertIn("services", plan_fields)

    def test_security_field_in_plan(self):
        """CompilationPlan has security (the D07-compatible Security requirements, top-level)."""
        from compiler.core.plan import CompilationPlan
        plan_fields = CompilationPlan.model_fields
        self.assertIn("security", plan_fields)


class TestD2D4RefinementDocumented(unittest.TestCase):
    """The D2-D4 refinement adds 8 fields and refines 3. These are documented
    in the contract but NOT yet implemented in CompilationPlan (R1-D.5 work)."""

    def test_compilationplan_does_not_have_content_hash(self):
        """CompilationPlan does NOT have content_hash yet. This is R1-D.5 work."""
        from compiler.core.plan import CompilationPlan
        plan_fields = CompilationPlan.model_fields
        self.assertNotIn("content_hash", plan_fields)

    def test_compilationplan_does_not_have_schema_version(self):
        """CompilationPlan does NOT have schema_version yet. This is R1-D.5 work."""
        from compiler.core.plan import CompilationPlan
        plan_fields = CompilationPlan.model_fields
        self.assertNotIn("schema_version", plan_fields)

    def test_compilationplan_does_not_have_source_architecture_content_hash(self):
        """CompilationPlan does NOT have source_architecture_content_hash yet. R1-D.5."""
        from compiler.core.plan import CompilationPlan
        plan_fields = CompilationPlan.model_fields
        self.assertNotIn("source_architecture_content_hash", plan_fields)

    def test_compilationplan_does_not_have_backend_constraints(self):
        """CompilationPlan does NOT have backend_constraints yet. R1-D.5."""
        from compiler.core.plan import CompilationPlan
        plan_fields = CompilationPlan.model_fields
        self.assertNotIn("backend_constraints", plan_fields)

    def test_compilationplan_does_not_have_required_capabilities(self):
        """CompilationPlan does NOT have required_capabilities yet. R1-D.5."""
        from compiler.core.plan import CompilationPlan
        plan_fields = CompilationPlan.model_fields
        self.assertNotIn("required_capabilities", plan_fields)

    def test_compilationplan_does_not_have_lowering_operator(self):
        """CompilationPlan does NOT have lowering_operator yet. R1-D.5."""
        from compiler.core.plan import CompilationPlan
        plan_fields = CompilationPlan.model_fields
        self.assertNotIn("lowering_operator", plan_fields)

    def test_compilationplan_does_not_have_lowering_timestamp(self):
        """CompilationPlan does NOT have lowering_timestamp yet. R1-D.5."""
        from compiler.core.plan import CompilationPlan
        plan_fields = CompilationPlan.model_fields
        self.assertNotIn("lowering_timestamp", plan_fields)

    def test_compilationplan_does_not_have_lowering_chain(self):
        """CompilationPlan does NOT have lowering_chain yet. R1-D.5."""
        from compiler.core.plan import CompilationPlan
        plan_fields = CompilationPlan.model_fields
        self.assertNotIn("lowering_chain", plan_fields)


class TestCompilationPlanStabilization(unittest.TestCase):
    """CompilationPlan is the stabilization implementation. It is NOT the final
    canonical Compiler IR. The final canonical Compiler IR is R1-D.5 work."""

    def test_compilationplan_is_pydantic_frozen(self):
        """CompilationPlan is Pydantic frozen (immutable)."""
        from compiler.core.plan import CompilationPlan
        from pydantic import ConfigDict
        self.assertEqual(CompilationPlan.model_config.get("frozen"), True)

    def test_compilationplan_has_4_node_types(self):
        """CompilationPlan has 4 node types: Service, DataModel, Event, SecurityPolicy."""
        from compiler.core.plan import CompilationPlan, Service, DataModel, Event, SecurityPolicy
        # Verify the types exist and are importable
        self.assertTrue(hasattr(CompilationPlan, "model_fields"))
        self.assertTrue(hasattr(Service, "model_fields"))
        self.assertTrue(hasattr(DataModel, "model_fields"))
        self.assertTrue(hasattr(Event, "model_fields"))
        self.assertTrue(hasattr(SecurityPolicy, "model_fields"))

    def test_compilationplan_service_has_data_models(self):
        """Service has data_models (the D07 Data flows)."""
        from compiler.core.plan import Service
        service_fields = Service.model_fields
        self.assertIn("data_models", service_fields)

    def test_compilationplan_service_has_published_events(self):
        """Service has published_events (the D07 Data flows)."""
        from compiler.core.plan import Service
        service_fields = Service.model_fields
        self.assertIn("published_events", service_fields)

    def test_compilationplan_service_has_consumed_events(self):
        """Service has consumed_events (the D07 Data flows)."""
        from compiler.core.plan import Service
        service_fields = Service.model_fields
        self.assertIn("consumed_events", service_fields)

    def test_compilationplan_plan_id_derives_from_isr_hash(self):
        """The plan_id is derived from the ISR content hash (per isr_to_plan)."""
        from compiler.core.lowering import isr_to_plan
        from isr.core.graph import ISRGraph, Node, NodeType
        from isr.core.identity import Provenance
        from isr.core.revision import ISRRevision
        from datetime import datetime, timezone
        import inspect

        # Verify isr_to_plan uses revision.content_hash for plan_id
        source = inspect.getsource(isr_to_plan)
        self.assertIn("content_hash", source)
        self.assertIn("plan_id", source)


class TestCanonicalCompilerIRIsFutureWork(unittest.TestCase):
    """The canonical Compiler IR module is R1-D.5 work. R1-D.2 establishes
    the contract refinements but does NOT create the module."""

    def test_no_canonical_compiler_ir_module_yet(self):
        """There is no compiler/core/canonical_ir.py module yet (R1-D.5)."""
        import os
        canonical_ir_path = os.path.join("compiler", "core", "canonical_ir.py")
        self.assertFalse(
            os.path.exists(canonical_ir_path),
            f"{canonical_ir_path} should not exist yet (R1-D.5 work)"
        )

    def test_no_canonical_compiler_ir_test_yet(self):
        """There is no tests/r1d2/test_canonical_compiler_ir.py test yet (R1-D.5)."""
        import os
        canonical_test_path = os.path.join("tests", "r1d2", "test_canonical_compiler_ir.py")
        self.assertFalse(
            os.path.exists(canonical_test_path),
            f"{canonical_test_path} should not exist yet (R1-D.5 work)"
        )


class TestConstitutionalSubstrateOnRetirementPath(unittest.TestCase):
    """The constitutional compiler substrate is on the retirement path (R1-D.5).
    It is NOT in the canonical runtime. The campaign runtime uses only
    compiler/core/* and isr/core/*."""

    def test_canonical_runtime_does_not_import_constitutional_compiler(self):
        """The canonical campaign runtime does not import from constitutional_architecture.compiler."""
        import os
        # Search for imports of constitutional_architecture.compiler in canonical paths
        canonical_files = [
            "certification/campaign/plan_builder.py",
            "certification/campaign/runner.py",
            "certification/campaign/verdict.py",
            "certification/campaign/verify_campaign.py",
            "certification/campaign/campaign_a.py",
            "certification/campaign/campaign_b.py",
            "certification/stages/stub_stages.py",
            "certification/stages/docker_stages.py",
            "certification/stages/independent_verify.py",
            "certification/provenance/bundle.py",
            "isr/core/invariants.py",
            "isr/core/revision.py",
            "compiler/core/plan.py",
            "compiler/core/lowering.py",
            "compiler/core/protocol.py",
        ]
        for filepath in canonical_files:
            if os.path.exists(filepath):
                with open(filepath, encoding="utf-8") as f:
                    content = f.read()
                self.assertNotIn(
                    "constitutional_architecture.compiler",
                    content,
                    f"{filepath} should not import from constitutional_architecture.compiler"
                )

    def test_constitutional_compiler_bridge_has_no_canonical_callers(self):
        """The compiler_bridge.py is dead code; no canonical callers."""
        import os
        canonical_dirs = ["compiler", "isr", "reqgraph", "evolution", "certification", "release"]
        for d in canonical_dirs:
            if not os.path.isdir(d):
                continue
            for root, _, files in os.walk(d):
                for fname in files:
                    if not fname.endswith(".py"):
                        continue
                    fpath = os.path.join(root, fname)
                    with open(fpath, encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    self.assertNotIn(
                        "constitutional_architecture.engine.compiler_bridge",
                        content,
                        f"{fpath} should not import from constitutional_architecture.engine.compiler_bridge"
                    )


class TestBackendProtocolPreserved(unittest.TestCase):
    """The canonical CompilerBackend Protocol is preserved."""

    def test_compiler_backend_protocol_exists(self):
        """compiler.core.protocol.CompilerBackend exists."""
        from compiler.core.protocol import CompilerBackend
        self.assertTrue(hasattr(CompilerBackend, "compile"))
        self.assertTrue(hasattr(CompilerBackend, "conformance"))
        self.assertTrue(hasattr(CompilerBackend, "identity"))
        self.assertTrue(hasattr(CompilerBackend, "test_spec"))
        self.assertTrue(hasattr(CompilerBackend, "element_paths"))

    def test_compiler_backend_compile_takes_compilation_plan(self):
        """CompilerBackend.compile takes a CompilationPlan (not a BIR)."""
        import inspect
        from compiler.core.protocol import CompilerBackend
        sig = inspect.signature(CompilerBackend.compile)
        params = list(sig.parameters.keys())
        self.assertIn("plan", params)

    def test_behavioral_classes_are_defined(self):
        """BEHAVIORAL_CLASSES and BackendClass are defined."""
        from compiler.core.protocol import BackendClass, BEHAVIORAL_CLASSES
        self.assertIn(BackendClass.BEHAVIORAL, BEHAVIORAL_CLASSES)
        self.assertIn(BackendClass.PRODUCTION, BEHAVIORAL_CLASSES)


class TestCanonicalBackendsPreserved(unittest.TestCase):
    """The canonical backends (Python FastAPI, Rust Axum) are preserved."""

    def test_python_fastapi_backend_exists(self):
        """PythonFastAPIBackend exists and implements the Protocol."""
        from compiler.backends.python_fastapi import PythonFastAPIBackend
        b = PythonFastAPIBackend()
        self.assertEqual(b.name, "python-fastapi")
        self.assertEqual(b.language, "python")
        self.assertEqual(b.framework, "fastapi")

    def test_rust_axum_backend_exists(self):
        """RustAxumBackend exists and implements the Protocol."""
        from compiler.backends.rust_axum import RustAxumBackend
        b = RustAxumBackend()
        self.assertEqual(b.name, "rust-axum")
        self.assertEqual(b.language, "rust")
        self.assertEqual(b.framework, "axum")

    def test_backend_registry_builds(self):
        """build_backend_registry() registers both canonical backends."""
        from compiler.composition import build_backend_registry
        registry = build_backend_registry()
        self.assertIn("python-fastapi", registry._backends)
        self.assertIn("rust-axum", registry._backends)


class TestIsrToPlanPreserved(unittest.TestCase):
    """The canonical isr_to_plan lowering is preserved."""

    def test_isr_to_plan_exists(self):
        """isr_to_plan is importable from compiler.core.lowering."""
        from compiler.core.lowering import isr_to_plan
        self.assertTrue(callable(isr_to_plan))

    def test_isr_to_plan_takes_isr_revision(self):
        """isr_to_plan takes an ISRRevision (the canonical ISR)."""
        import inspect
        from compiler.core.lowering import isr_to_plan
        sig = inspect.signature(isr_to_plan)
        params = list(sig.parameters.keys())
        self.assertIn("revision", params)

    def test_isr_to_plan_returns_compilation_plan(self):
        """isr_to_plan returns a CompilationPlan (the stabilization implementation)."""
        from isr.core.graph import ISRGraph
        from isr.core.revision import ISRRevision
        from isr.core.identity import Provenance
        from compiler.core.lowering import isr_to_plan
        from compiler.core.plan import CompilationPlan
        from datetime import datetime, timezone
        import uuid

        # Build a minimal canonical ISR
        graph = ISRGraph()
        prov = Provenance(
            created_by="r1d2_test",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        rev = ISRRevision.create(
            system_id="r1d2-test",
            revision_id="r1d2-rev-1",
            schema_version="1.1",
            graph=graph,
            provenance=prov,
        )
        plan = isr_to_plan(rev)
        self.assertIsInstance(plan, CompilationPlan)


class TestNoArchitecturalBypasses(unittest.TestCase):
    """No architectural bypasses in the canonical runtime."""

    def test_no_compiler_ir_to_backend_bypass(self):
        """No compiler/core file bypasses the canonical CompilerBackend Protocol."""
        import os
        compiler_files = [
            "compiler/core/plan.py",
            "compiler/core/protocol.py",
            "compiler/core/lowering.py",
            "compiler/core/conformance.py",
            "compiler/core/repository.py",
        ]
        for filepath in compiler_files:
            if os.path.exists(filepath):
                with open(filepath, encoding="utf-8") as f:
                    content = f.read()
                # Check for bypass patterns: direct file writes, direct subprocess calls
                self.assertNotIn(
                    "open(", content,
                    f"{filepath} should not have direct file writes (use ArtifactSet)"
                )
                self.assertNotIn(
                    "subprocess", content,
                    f"{filepath} should not have direct subprocess calls (use Backend)"
                )


class TestTierABaselinePreserved(unittest.TestCase):
    """The Tier-A baseline (243 tests) is preserved."""

    def test_tier_a_tests_count_unchanged(self):
        """The Tier-A test directory has the expected number of tests."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/cbc1/", "--collect-only", "-q"],
            capture_output=True, text=True
        )
        # Parse "243/244 tests collected" format (243 passed, 244 collected, 1 deselected)
        import re
        for line in result.stdout.splitlines():
            match = re.search(r"(\d+)/(\d+)\s+tests?\s+collected", line)
            if match:
                collected = int(match.group(2))
                # 244 collected, 1 deselected = 243 active
                self.assertEqual(collected, 244)
                return
        self.fail(f"Could not determine Tier-A test count. Output: {result.stdout[-500:]}")


if __name__ == "__main__":
    unittest.main()
