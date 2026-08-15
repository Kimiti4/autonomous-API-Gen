from __future__ import annotations

from typing import List, Optional

from constitutional_architecture.core.constitution import FORBIDDEN_LEXICON
from constitutional_architecture.core.models.genome import ArchitectureGenome


class GenomeConstitutionalViolation(ValueError):
    pass


class GenomeValidator:
    def __init__(self, forbidden_lexicon: tuple[str, ...] = FORBIDDEN_LEXICON) -> None:
        self._forbidden = forbidden_lexicon

    def validate_genome(self, genome: ArchitectureGenome) -> None:
        violations: List[str] = []
        serialized = genome.serialize()
        values_to_check: List[str] = []

        for cat_data in serialized.get("categorical", {}).values():
            val = cat_data.get("value", "")
            if isinstance(val, str):
                values_to_check.append(val)

        for term in self._forbidden:
            if len(term) < 4:
                continue
            for val in values_to_check:
                tokens = val.lower().split("_")
                if term.lower() in tokens:
                    violations.append(
                        f"Forbidden term '{term}' found in gene value '{val}'"
                    )

        if violations:
            raise GenomeConstitutionalViolation("; ".join(violations))

    def has_violation(self, genome: ArchitectureGenome) -> bool:
        try:
            self.validate_genome(genome)
            return False
        except GenomeConstitutionalViolation:
            return True
