"""
Phase 1 — Intent Model Constitutional Validator

Extends the Phase 0 ConstitutionValidator to enforce constitutional
invariants on the IntentModel before it reaches the Topology Resolver.
"""

from __future__ import annotations

import re
from typing import List

from constitutional_architecture.core.governance import FORBIDDEN_LEXICON as GOV_FORBIDDEN_LEXICON
from constitutional_architecture.core.models.intent import IntentModel, QualityAttribute
from constitutional_architecture.validators.constitution_validator import ConstitutionalViolation


class IntentConstitutionalViolation(ConstitutionalViolation):
    pass


class IntentValidator:
    """Validates IntentModel instances against constitutional invariants.

    Runs as a gate between Pass 2 (Intent Analysis) and Pass 3 (Topology Resolution).
    """

    def validate(self, intent: IntentModel) -> None:
        self._check_technology_neutrality(intent)
        self._check_security_by_design(intent)
        self._check_observability_by_design(intent)
        self._check_quality_completeness(intent)
        self._check_capability_coherence(intent)

    def _check_technology_neutrality(self, intent: IntentModel) -> None:
        text = intent.model_dump_json().lower()
        for term in GOV_FORBIDDEN_LEXICON:
            if re.search(rf'\b{re.escape(term)}\b', text):
                raise IntentConstitutionalViolation(
                    f"IntentModel contains forbidden technology term '{term}'. "
                    f"The Intent Model must be implementation-agnostic."
                )

    def _check_security_by_design(self, intent: IntentModel) -> None:
        if intent.authentication_required and intent.authorization_model == "none":
            raise IntentConstitutionalViolation(
                "Authentication is required but authorization model is 'none'. "
                "Security by Design requires explicit authorization."
            )

        has_restricted = any(
            c.security_classification == "restricted"
            for c in intent.core_capabilities
        )
        if has_restricted and not intent.encryption_at_rest:
            raise IntentConstitutionalViolation(
                "Restricted capabilities require encryption at rest. "
                "Security by Design is non-negotiable."
            )

    def _check_observability_by_design(self, intent: IntentModel) -> None:
        if not intent.structured_logging_required:
            raise IntentConstitutionalViolation(
                "Structured logging is required by the Constitution "
                "(Observability by Design). Cannot be disabled."
            )
        if not intent.health_checks_required:
            raise IntentConstitutionalViolation(
                "Health checks are required by the Constitution "
                "(Observability by Design). Cannot be disabled."
            )

    def _check_quality_completeness(self, intent: IntentModel) -> None:
        missing = [
            attr for attr in QualityAttribute
            if attr not in intent.quality_priorities
        ]
        if missing:
            raise IntentConstitutionalViolation(
                f"Quality priorities missing for: {[m.value for m in missing]}. "
                f"Multi-objective optimization requires explicit weights for all dimensions."
            )

    def _check_capability_coherence(self, intent: IntentModel) -> None:
        cap_names = {c.name for c in intent.core_capabilities}
        for cap in intent.core_capabilities:
            for dep in cap.dependencies:
                if dep not in cap_names:
                    raise IntentConstitutionalViolation(
                        f"Capability '{cap.name}' depends on unknown capability '{dep}'."
                    )
