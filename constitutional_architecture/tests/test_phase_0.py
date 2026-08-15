"""
Tests for Phase 0: Constitutional Stabilization.

Validates all 7 axioms of the core constitution via the ConstitutionValidator:
  I.   ISR Supremacy — Forbidden Lexicon enforcement
  II.  Genome Isolation — evolution through Transcriber only
  III. Compiler Purity — compilers don't modify ISR
  IV.  Knowledge Externality — hardcoded heuristics
  V.   Dual-Track Evolution — both tracks required
  VI.  Boundary Integrity — pipeline stage ordering
  VII. Auditability — provenance completeness
"""

from constitutional_architecture.validators.constitution_validator import (
    ConstitutionValidator, ValidationResult, Violation,
)
from constitutional_architecture.core.constitution import (
    CONSTITUTION_VERSION, AXIOMS, Axiom, FORBIDDEN_LEXICON,
    PASSES, MINIMUM_FUNCTIONAL_EVALUATORS, MINIMUM_NON_FUNCTIONAL_EVALUATORS,
    MINIMUM_CONSTITUTIONAL_THRESHOLD,
)


# ==============================================================================
# Core Constitution Structure Tests
# ==============================================================================

class TestConstitutionDefinition:
    def test_contains_exactly_seven_axioms(self):
        assert len(AXIOMS) == 7

    def test_axiom_version_is_set(self):
        assert CONSTITUTION_VERSION == "v1.0.0"

    def test_axiom_enum_values(self):
        assert Axiom.ISR_SUPREMACY.value == "I"
        assert Axiom.AUDITABILITY.value == "VII"

    def test_all_axioms_have_descriptions(self):
        for key, desc in AXIOMS.items():
            assert len(desc) > 10

    def test_pass_definitions_have_ten_stages(self):
        assert len(PASSES) == 10

    def test_minimum_evaluator_constants(self):
        assert MINIMUM_FUNCTIONAL_EVALUATORS == 1
        assert MINIMUM_NON_FUNCTIONAL_EVALUATORS >= 1
        assert 0.0 < MINIMUM_CONSTITUTIONAL_THRESHOLD <= 1.0


# ==============================================================================
# Forbidden Lexicon Tests
# ==============================================================================

class TestForbiddenLexicon:
    def test_cloud_providers_are_forbidden(self):
        assert "aws" in FORBIDDEN_LEXICON
        assert "azure" in FORBIDDEN_LEXICON
        assert "gcp" in FORBIDDEN_LEXICON

    def test_databases_are_forbidden(self):
        assert "postgres" in FORBIDDEN_LEXICON
        assert "redis" in FORBIDDEN_LEXICON

    def test_ui_frameworks_are_forbidden(self):
        assert "react" in FORBIDDEN_LEXICON
        assert "vue" in FORBIDDEN_LEXICON

    def test_api_frameworks_are_forbidden(self):
        assert "fastapi" in FORBIDDEN_LEXICON
        assert "django" in FORBIDDEN_LEXICON

    def test_specific_lexicon_terms(self):
        assert "terraform" in FORBIDDEN_LEXICON
        assert "kubernetes" in FORBIDDEN_LEXICON
        assert "tailwind" in FORBIDDEN_LEXICON
        assert "docker" in FORBIDDEN_LEXICON


# ==============================================================================
# Axiom I: ISR Supremacy Tests
# ==============================================================================

class TestAxiomIISRPurity:
    def test_clean_isr_passes(self):
        validator = ConstitutionValidator()
        clean_isr = """
        {
            "system": {
                "id": "sys-1",
                "name": "E-Commerce System",
                "modules": [
                    {"id": "mod-catalog", "name": "Catalog"}
                ]
            }
        }
        """
        violations = validator.check_isr_purity(clean_isr)
        assert len(violations) == 0

    def test_forbidden_term_detected(self):
        validator = ConstitutionValidator()
        dirty_isr = '{"name": "My React App", "database": "postgres"}'
        violations = validator.check_isr_purity(dirty_isr)
        assert len(violations) > 0
        assert any("react" in v.description for v in violations)
        assert any("postgres" in v.description for v in violations)

    def test_forbidden_term_in_nested_field(self):
        validator = ConstitutionValidator()
        dirty = '{"deployment": {"provider": "aws", "region": "us-east-1"}}'
        violations = validator.check_isr_purity(dirty)
        assert any("aws" in v.description for v in violations)

    def test_term_in_compiler_backend_permitted(self):
        """Terms in compiler files should not be checked by ISR scanner."""
        validator = ConstitutionValidator()
        text = 'module.exports = { theme: { colors: { ... } } }'
        violations = validator.check_isr_purity(text)
        assert len(violations) == 0  # Not a JSON ISR

    def test_case_insensitive_detection(self):
        validator = ConstitutionValidator()
        text = '{"framework": "REACT", "db": "PostgreSQL"}'
        violations = validator.check_isr_purity(text)
        assert any("react" in v.description.lower() for v in violations)


# ==============================================================================
# Axiom II: Genome Isolation Tests
# ==============================================================================

class TestAxiomIIGenomeIsolation:
    def test_transcriber_code_passes(self):
        validator = ConstitutionValidator()
        source = """
class FrontendGenomeTranscriber:
    def transcribe(self, genome):
        profile = FrontendISRProfile(design_system=ds)
        return profile
"""
        violations = validator.check_genome_isolation(source)
        assert len(violations) == 0

    def test_direct_isr_construction_outside_transcriber(self):
        validator = ConstitutionValidator()
        source = """
class SomeMutator:
    def mutate(self, genome):
        isr = ISR(system=my_system)
        return isr
"""
        violations = validator.check_genome_isolation(source)
        assert len(violations) > 0

    def test_empty_source_returns_empty(self):
        validator = ConstitutionValidator()
        assert validator.check_genome_isolation("") == []

    def test_syntax_error_skipped(self):
        validator = ConstitutionValidator()
        assert validator.check_genome_isolation("this is not valid python {{{") == []


# ==============================================================================
# Axiom III: Compiler Purity Tests
# ==============================================================================

class TestAxiomIIICompilerPurity:
    def test_compiler_imports_isr_profile_allowed(self):
        validator = ConstitutionValidator()
        source = """
from constitutional_architecture.isr.profiles.frontend_model import FrontendISRProfile

class TailwindCompiler:
    def compile(self, profile: FrontendISRProfile):
        pass
"""
        violations = validator.check_compiler_purity(source, "compilers/tailwind.py")
        assert len(violations) == 0

    def test_compiler_imports_isr_model_rejected(self):
        validator = ConstitutionValidator()
        source = """
from constitutional_architecture.isr.model.system import System

class BadCompiler:
    def compile(self, system: System):
        system.name = "hacked"
"""
        violations = validator.check_compiler_purity(source, "compilers/bad.py")
        assert len(violations) > 0

    def test_non_compiler_file_skipped(self):
        validator = ConstitutionValidator()
        source = "import System"
        violations = validator.check_compiler_purity(source, "evaluators/test.py")
        assert len(violations) == 0


# ==============================================================================
# Axiom IV: Knowledge Externality Tests
# ==============================================================================

class TestAxiomIVKnowledgeExternality:
    def test_hardcoded_genome_allele_detected(self):
        validator = ConstitutionValidator()
        source = """
genome = FrontendGenome()
genome.presentation.typography_scale._allele = 1.25
"""
        violations = validator.check_knowledge_externality(source)
        assert len(violations) > 0
        assert any("typography_scale" in v.description for v in violations)

    def test_ckb_query_not_flagged(self):
        validator = ConstitutionValidator()
        source = """
patterns = ckb.resolve_archetype(["dashboard"])
HeuristicInjector().inject(patterns, genome)
"""
        violations = validator.check_knowledge_externality(source)
        assert len(violations) == 0


# ==============================================================================
# Axiom V: Dual-Track Evolution Tests
# ==============================================================================

class TestAxiomVDualTrack:
    def test_both_tracks_present_passes(self):
        validator = ConstitutionValidator()
        evaluators = ["TokenConsistencyEvaluator", "AccessibilityEvaluator"]
        violations = validator.check_dual_track_evolution(evaluators)
        assert len(violations) == 0

    def test_missing_functional_fails(self):
        validator = ConstitutionValidator()
        violations = validator.check_dual_track_evolution(["AccessibilityEvaluator"])
        assert len(violations) > 0
        assert any("functional" in v.description for v in violations)

    def test_missing_non_functional_fails(self):
        validator = ConstitutionValidator()
        violations = validator.check_dual_track_evolution(["TokenConsistencyEvaluator"])
        assert len(violations) > 0
        assert any("non-functional" in v.description for v in violations)

    def test_empty_evaluator_list_fails(self):
        validator = ConstitutionValidator()
        violations = validator.check_dual_track_evolution([])
        assert len(violations) == 2


# ==============================================================================
# Axiom VI: Boundary Integrity Tests
# ==============================================================================

class TestAxiomVIBoundary:
    def test_no_violations_for_clean_graph(self):
        validator = ConstitutionValidator()
        graph = {
            "transcriber.py": {"isr", "genome"},
            "compiler.py": {"isr"},  # Pass 8-9 reads ISR
        }
        violations = validator.check_boundary_integrity(graph)
        assert len(violations) == 0

    def test_shortcut_detected(self):
        validator = ConstitutionValidator()
        graph = {
            "intent_analyzer.py": {"compiler"},  # Pass 2 -> Pass 8 (skip 3-7)
        }
        violations = validator.check_boundary_integrity(graph)
        assert len(violations) > 0

    def test_genome_to_code_shortcut(self):
        validator = ConstitutionValidator()
        graph = {
            "genome_processor.py": {"code_generator"},  # Pass 4 -> Pass 9
        }
        violations = validator.check_boundary_integrity(graph)
        assert len(violations) > 0


# ==============================================================================
# Axiom VII: Auditability Tests
# ==============================================================================

class TestAxiomVIIAuditability:
    def test_complete_provenance_passes(self):
        validator = ConstitutionValidator()
        data = {
            "genome-v1": {
                "parent_hash": "abc123",
                "version": 2,
                "created_at": "2026-07-31T00:00:00Z",
                "source_pass": "Pass 4",
            }
        }
        violations = validator.check_auditability(data)
        assert len(violations) == 0

    def test_missing_parent_hash_fails(self):
        validator = ConstitutionValidator()
        data = {
            "artifact-1": {
                "version": 1,
                "created_at": "2026-07-31T00:00:00Z",
                "source_pass": "Pass 6",
            }
        }
        violations = validator.check_auditability(data)
        assert len(violations) > 0
        assert any("parent_hash" in v.description for v in violations)

    def test_null_field_fails(self):
        validator = ConstitutionValidator()
        data = {
            "artifact-1": {
                "parent_hash": None,
                "version": 1,
                "created_at": None,
                "source_pass": "Pass 6",
            }
        }
        violations = validator.check_auditability(data)
        assert len(violations) >= 2

    def test_empty_provenance_returns_empty(self):
        validator = ConstitutionValidator()
        assert validator.check_auditability({}) == []


# ==============================================================================
# Full Validation Integration Tests
# ==============================================================================

class TestFullValidation:
    def test_clean_input_passes(self):
        validator = ConstitutionValidator()
        result = validator.validate_all(
            isr_text='{"system": {"id": "sys-1"}}',
            evaluator_names=["TokenConsistencyEvaluator", "AccessibilityEvaluator"],
        )
        assert result.passed is True

    def test_forbidden_lexicon_causes_failure(self):
        validator = ConstitutionValidator()
        result = validator.validate_all(
            isr_text='{"framework": "react", "db": "postgres"}',
            evaluator_names=["TokenConsistencyEvaluator", "AccessibilityEvaluator"],
        )
        assert result.passed is False

    def test_missing_evaluator_track_causes_failure(self):
        validator = ConstitutionValidator()
        result = validator.validate_all(
            isr_text='{"system": {"id": "sys-1"}}',
            evaluator_names=["TokenConsistencyEvaluator"],
        )
        assert result.passed is False

    def test_multiple_violations_reported(self):
        validator = ConstitutionValidator()
        result = validator.validate_all(
            isr_text='{"name": "React App", "db": "postgres"}',
            python_files={
                "mutator.py": """
class BadMutator:
    def evolve(self):
        isr = ISR(system=System("sys-1"))
        return isr
"""
            },
            evaluator_names=[],
        )
        assert result.passed is False
        assert len(result.violations) > 0

    def test_constitution_version_in_result(self):
        result = ValidationResult()
        assert result.constitution_version == "v1.0.0"


# ==============================================================================
# Pre-commit Runner Tests
# ==============================================================================

class TestValidationResult:
    def test_default_passed(self):
        r = ValidationResult()
        assert r.passed is True
        assert r.violations == []

    def test_violation_creation(self):
        v = Violation(axiom="I", description="Test violation", file="test.py", line=42, severity="error")
        assert v.axiom == "I"
        assert v.severity == "error"
        assert v.line == 42
