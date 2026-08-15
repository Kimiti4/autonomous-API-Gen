"""Stratification taxonomy -- authored, versioned description of the
software-problem space the calibration corpus samples from.

The axes of variation are designed (authored YAML); the project instances
are generated (sampler). Taxonomy content is data, evolvable per version;
schema changes here are ADR-worthy.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator


class TaxonomyValidationError(ValueError):
    pass


class DomainProfile(BaseModel):
    capabilities: list[str] = Field(min_length=1)
    data_entities: list[str] = Field(min_length=1)
    quality_focus: list[str] = Field(min_length=1)


class ComplexityProfile(BaseModel):
    expected_requirement_range: tuple[int, int]
    extra_topics: list[str] = Field(default_factory=list)


class CapabilityClassProfile(BaseModel):
    primary_interaction: str
    topics: list[str] = Field(default_factory=list)


class ScaleProfile(BaseModel):
    expected_services: int = Field(ge=1)
    throughput_class: str
    availability_posture: str


class IntegrationProfile(BaseModel):
    topics: list[str] = Field(default_factory=list)


class ComplianceProfile(BaseModel):
    topics: list[str] = Field(default_factory=list)


class AxesSpec(BaseModel):
    domain: list[str] = Field(min_length=1)
    complexity_tier: list[str] = Field(min_length=1)
    capability_class: list[str] = Field(min_length=1)
    scale_tier: list[str] = Field(min_length=1)
    integration_pattern: list[str] = Field(min_length=1)
    compliance_regime: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_values(self) -> "AxesSpec":
        for axis_name, values in self.model_dump().items():
            if len(values) != len(set(values)):
                raise TaxonomyValidationError(
                    f"axis '{axis_name}' contains duplicate values"
                )
        return self

    @property
    def axis_names(self) -> tuple[str, ...]:
        return tuple(type(self).model_fields.keys())


class ProfilesBundle(BaseModel):
    domains: dict[str, DomainProfile]
    complexity_tiers: dict[str, ComplexityProfile]
    capability_classes: dict[str, CapabilityClassProfile]
    scale_tiers: dict[str, ScaleProfile]
    integration_patterns: dict[str, IntegrationProfile]
    compliance_regimes: dict[str, ComplianceProfile]


class TaxonomyConstraint(BaseModel):
    forbidden: dict[str, str] = Field(min_length=1)


class StratificationTaxonomy(BaseModel):
    taxonomy_version: str = Field(min_length=1)
    axes: AxesSpec
    profiles: ProfilesBundle
    constraints: list[TaxonomyConstraint] = Field(default_factory=list)

    @model_validator(mode="after")
    def _profile_completeness(self) -> "StratificationTaxonomy":
        pairs = (
            ("domain", self.axes.domain, self.profiles.domains),
            ("complexity_tier", self.axes.complexity_tier,
             self.profiles.complexity_tiers),
            ("capability_class", self.axes.capability_class,
             self.profiles.capability_classes),
            ("scale_tier", self.axes.scale_tier,
             self.profiles.scale_tiers),
            ("integration_pattern", self.axes.integration_pattern,
             self.profiles.integration_patterns),
            ("compliance_regime", self.axes.compliance_regime,
             self.profiles.compliance_regimes),
        )
        for axis_name, values, profile_map in pairs:
            axis_set, profile_set = set(values), set(profile_map.keys())
            missing = axis_set - profile_set
            unknown = profile_set - axis_set
            if missing or unknown:
                raise TaxonomyValidationError(
                    f"axis '{axis_name}' profile mismatch -- "
                    f"missing profiles: {sorted(missing)}, "
                    f"unknown profiles: {sorted(unknown)}"
                )
        for constraint in self.constraints:
            for axis_name in constraint.forbidden:
                if axis_name not in self.axes.axis_names:
                    raise TaxonomyValidationError(
                        f"constraint references unknown axis '{axis_name}'"
                    )
        return self

    @classmethod
    def load(cls, path: str | Path) -> "StratificationTaxonomy":
        with open(path, "r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
        try:
            return cls.model_validate(raw)
        except TaxonomyValidationError:
            raise
        except Exception as exc:
            raise TaxonomyValidationError(str(exc)) from exc
