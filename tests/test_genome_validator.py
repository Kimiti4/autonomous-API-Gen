import pytest

from constitutional_architecture.core.models.genome import (
    ApplicationArchitecture, ArchitectureGenome, DataArchitecture,
)
from constitutional_architecture.validators.genome_validator import (
    GenomeConstitutionalViolation, GenomeValidator,
)


class TestGenomeValidator:
    def test_valid_genome_passes(self):
        g = ArchitectureGenome()
        validator = GenomeValidator()
        validator.validate_genome(g)

    def test_forbidden_term_in_gene_value(self):
        g = ArchitectureGenome()
        g.categorical_genes["data_arch"].value = DataArchitecture.POLYGLOT_PERSISTENCE
        validator = GenomeValidator(forbidden_lexicon=())
        validator.validate_genome(g)
        g.categorical_genes["data_arch"].value = "polyglot_persistence_with_react"
        validator = GenomeValidator(forbidden_lexicon=("react",))
        with pytest.raises(GenomeConstitutionalViolation):
            validator.validate_genome(g)

    def test_has_violation_returns_false_for_valid(self):
        g = ArchitectureGenome()
        validator = GenomeValidator(forbidden_lexicon=())
        assert not validator.has_violation(g)

    def test_has_violation_returns_true_for_violation(self):
        g = ArchitectureGenome()
        g.categorical_genes["data_arch"].value = DataArchitecture.DATABASE_PER_SERVICE
        validator = GenomeValidator(forbidden_lexicon=("react",))
        g.categorical_genes["data_arch"].value = "react"
        assert validator.has_violation(g)

    def test_forbidden_term_in_categorical_value(self):
        g = ArchitectureGenome()
        g.categorical_genes["data_arch"].value = "react"
        validator = GenomeValidator(forbidden_lexicon=("react",))
        with pytest.raises(GenomeConstitutionalViolation):
            validator.validate_genome(g)

    def test_empty_forbidden_lexicon(self):
        g = ArchitectureGenome()
        validator = GenomeValidator(forbidden_lexicon=())
        validator.validate_genome(g)

    def test_violation_message_contains_term(self):
        g = ArchitectureGenome()
        g.categorical_genes["data_arch"].value = "react"
        validator = GenomeValidator(forbidden_lexicon=("react",))
        with pytest.raises(GenomeConstitutionalViolation) as exc:
            validator.validate_genome(g)
        assert "react" in str(exc.value)
