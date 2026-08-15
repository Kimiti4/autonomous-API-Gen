"""
Frontend ISR Profile Validator.

Validates that a FrontendISRProfile satisfies structural and constitutional rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from constitutional_architecture.isr.profiles.frontend_model import (
    FrontendISRProfile, Component, Page, TokenDefinition,
)


@dataclass(frozen=True)
class ProfileValidationResult:
    passed: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)


class FrontendProfileValidator:
    """Validates frontend ISR profiles against constitutional rules."""

    MIN_REQUIRED_COMPONENTS = 5
    MAX_PAGE_DATA_REFS = 20

    def validate(self, profile: FrontendISRProfile) -> ProfileValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        # Design system must have at least one token category
        if not profile.design_system.tokens:
            errors.append("Design system must define at least one token category")

        # Color tokens must have accessibility constraints
        color_tokens = profile.design_system.tokens.get("color", {})
        for token_id, token in color_tokens.items():
            if not token.accessibility_constraints:
                warnings.append(f"Color token '{token_id}' lacks accessibility constraints")

        # Each component must have a purpose, states, and accessibility
        for comp in profile.components:
            self._validate_component(comp, errors, warnings)

        # Each page must reference a valid layout and component
        layout_ids = {l.id for l in profile.layouts}
        component_ids = {c.id for c in profile.components}
        for page in profile.pages:
            self._validate_page(page, layout_ids, component_ids, errors, warnings)

        # At minimum components required
        if len(profile.components) < self.MIN_REQUIRED_COMPONENTS:
            warnings.append(
                f"Profile has {len(profile.components)} components; "
                f"recommended minimum is {self.MIN_REQUIRED_COMPONENTS}"
            )

        return ProfileValidationResult(
            passed=len(errors) == 0,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    def _validate_component(self, comp: Component, errors: list[str], warnings: list[str]) -> None:
        if not comp.purpose:
            errors.append(f"Component '{comp.id}' must have a purpose")
        if "default" not in comp.states:
            errors.append(f"Component '{comp.id}' must define a 'default' state")
        if not comp.accessibility_contract.aria_role:
            warnings.append(f"Component '{comp.id}' has no ARIA role defined")

    def _validate_page(
        self,
        page: Page,
        layout_ids: set[str],
        component_ids: set[str],
        errors: list[str],
        warnings: list[str],
    ) -> None:
        if not page.route_pattern:
            errors.append(f"Page '{page.id}' must have a route pattern")
        if page.layout_ref not in layout_ids:
            errors.append(f"Page '{page.id}' references unknown layout '{page.layout_ref}'")
        if len(page.data_requirements) > self.MAX_PAGE_DATA_REFS:
            warnings.append(
                f"Page '{page.id}' has {len(page.data_requirements)} data requirements; "
                f"max recommended is {self.MAX_PAGE_DATA_REFS}"
            )
