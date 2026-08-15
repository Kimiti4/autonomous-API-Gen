"""Legacy coupling registry -- the frozen boundary of constitutional debt.

Purpose
    Enumerates every known technology-coupled or implementation-detail field
    in the domain layer. The guard test
    (``tests/test_coupling_registry_guard.py``) enforces this registry
    bidirectionally:

      * any coupling found by the scanner but NOT registered fails the build
        (the debt cannot grow silently);
      * any registered entry the scanner no longer finds fails the build
        (paid-off or moved debt must be removed from the registry).

    The registry is therefore a live sunset checklist: it can only shrink
    through explicit removal, never drift.

Governance rules
    1. New domain code must never require a registry entry. If it does, the
       design is constitutionally wrong -- fix the design, not the registry.
    2. Entries are removed only when their sunset condition is measured true
       (see ADR amendment). No date-based removal.
    3. Every entry records the matched token and the exact sunset condition.
"""

from __future__ import annotations

import enum

from pydantic import BaseModel


class CouplingCategory(str, enum.Enum):
    TECHNOLOGY_TOKEN_FIELD_NAME = "technology_token_field_name"
    TECHNOLOGY_TOKEN_DEFAULT_VALUE = "technology_token_default_value"
    TECHNOLOGY_TOKEN_ENUM_VALUE = "technology_token_enum_value"
    IMPLEMENTATION_DETAIL_FIELD = "implementation_detail_field"


class CouplingRegistryEntry(BaseModel):
    qualified_path: str      # "module.ClassName.field_name" (or .EnumName.member)
    category: CouplingCategory
    matched_token: str
    reason: str
    sunset_condition: str


_SUNSET_CAP_C = (
    "Removable when >=1 Cap-C compiler backend compiles purely from SystemModel "
    "sections, the stratified matrix runs with zero legacy envelopes, and this "
    "registry is empty (ADR sunset gates 1-3)."
)

LEGACY_COUPLING_REGISTRY: tuple[CouplingRegistryEntry, ...] = (
    CouplingRegistryEntry(
        qualified_path="tiannara.domain.models.isr.ServiceSpec.port",
        category=CouplingCategory.IMPLEMENTATION_DETAIL_FIELD,
        matched_token="port",
        reason=(
            "Legacy calibration spec exposes transport ports; the typed ISR "
            "expresses endpoints abstractly (SystemModel.apis/services)."
        ),
        sunset_condition=_SUNSET_CAP_C,
    ),
    CouplingRegistryEntry(
        qualified_path="tiannara.domain.models.isr.DeploymentSpec.container_runtime",
        category=CouplingCategory.TECHNOLOGY_TOKEN_DEFAULT_VALUE,
        matched_token="docker",
        reason=(
            "Legacy default value is a technology token; deployment is "
            "abstract in SystemModel.deployment."
        ),
        sunset_condition=_SUNSET_CAP_C,
    ),
)
