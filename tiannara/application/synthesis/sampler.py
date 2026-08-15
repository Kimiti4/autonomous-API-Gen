"""Seeded stratified sampler: taxonomy x seed -> RequirementSketch corpus.

Semantics:
  * coverage-first -- strata are enumerated canonically, permuted by a seeded
    RNG, and consumed in order; the corpus wraps to a new epoch only after
    every valid stratum has appeared. No stratum repeats before full coverage.
  * determinism -- per-instance RNG streams are derived from
    sha256(taxonomy_version | seed | index | epoch | stratum_key); no
    wall-clock, no uuid4, no shared-stream coupling.
"""

from __future__ import annotations

import itertools
import random

from pydantic import BaseModel, Field

from tiannara.domain.models.requirement_graph import RequirementKind
from tiannara.domain.models.requirement_sketch import (
    ComplexityBudget,
    ExpectedRequirement,
    PlantedDefect,
    PlantedDefectKind,
    RequirementSketch,
    SketchProvenance,
    StratumAssignment,
)
from tiannara.domain.services.canonical import sha256_hex
from tiannara.domain.models.system_model import Priority

from .taxonomy import StratificationTaxonomy


class DefectRates(BaseModel):
    contradiction: float = Field(default=0.10, ge=0.0, le=1.0)
    missing_must: float = Field(default=0.10, ge=0.0, le=1.0)
    ambiguity: float = Field(default=0.15, ge=0.0, le=1.0)


def _derive_rng(*parts: object) -> random.Random:
    digest = sha256_hex("|".join(str(part) for part in parts))
    return random.Random(int(digest, 16) % (2**64))


class StratifiedSampler:
    def __init__(
        self,
        taxonomy: StratificationTaxonomy,
        rates: DefectRates | None = None,
    ) -> None:
        self._taxonomy = taxonomy
        self._rates = rates or DefectRates()

    # -- stratum space -----------------------------------------------------

    def enumerate_strata(self) -> list[StratumAssignment]:
        axes = self._taxonomy.axes
        strata: list[StratumAssignment] = []
        for combo in itertools.product(
            axes.domain,
            axes.complexity_tier,
            axes.capability_class,
            axes.scale_tier,
            axes.integration_pattern,
            axes.compliance_regime,
        ):
            assignment = StratumAssignment(
                domain=combo[0],
                complexity_tier=combo[1],
                capability_class=combo[2],
                scale_tier=combo[3],
                integration_pattern=combo[4],
                compliance_regime=combo[5],
            )
            if not self._forbidden(assignment):
                strata.append(assignment)
        return sorted(strata, key=lambda s: s.key())

    def _forbidden(self, assignment: StratumAssignment) -> bool:
        values = assignment.model_dump()
        return any(
            all(values[axis] == value for axis, value in constraint.forbidden.items())
            for constraint in self._taxonomy.constraints
        )

    # -- sampling ----------------------------------------------------------

    def sample(self, count: int, seed: int) -> list[RequirementSketch]:
        if count < 0:
            raise ValueError("count must be >= 0")
        strata = self.enumerate_strata()
        permutation = strata[:]
        _derive_rng("permutation", self._taxonomy.taxonomy_version, seed).shuffle(permutation)
        sketches: list[RequirementSketch] = []
        for index in range(count):
            assignment = permutation[index % len(permutation)]
            epoch = index // len(permutation)
            sketches.append(self._build(assignment, seed, index, epoch))
        return sketches

    def _build(
        self,
        assignment: StratumAssignment,
        seed: int,
        index: int,
        epoch: int,
    ) -> RequirementSketch:
        profiles = self._taxonomy.profiles
        domain = profiles.domains[assignment.domain]
        complexity = profiles.complexity_tiers[assignment.complexity_tier]
        capability_class = profiles.capability_classes[assignment.capability_class]
        scale = profiles.scale_tiers[assignment.scale_tier]
        integration = profiles.integration_patterns[assignment.integration_pattern]
        compliance = profiles.compliance_regimes[assignment.compliance_regime]

        requirements: list[ExpectedRequirement] = []
        for capability in domain.capabilities:
            requirements.append(
                ExpectedRequirement(
                    ref_id=f"req-cap-{capability}",
                    kind=RequirementKind.FUNCTIONAL,
                    priority=_priority("must"),
                    topic=capability,
                )
            )
        for position, focus in enumerate(domain.quality_focus):
            requirements.append(
                ExpectedRequirement(
                    ref_id=f"req-quality-{focus}",
                    kind=RequirementKind.QUALITY,
                    priority=_priority("must" if position == 0 else "should"),
                    topic=focus,
                )
            )
        requirements.append(
            ExpectedRequirement(
                ref_id=f"req-scale-{assignment.scale_tier}",
                kind=RequirementKind.QUALITY,
                priority=_priority("should"),
                topic=f"throughput_{scale.throughput_class}",
            )
        )
        for topic in compliance.topics:
            requirements.append(
                ExpectedRequirement(
                    ref_id=f"req-compliance-{topic}",
                    kind=RequirementKind.COMPLIANCE,
                    priority=_priority("must"),
                    topic=topic,
                )
            )
        for topic in integration.topics:
            requirements.append(
                ExpectedRequirement(
                    ref_id=f"req-integration-{topic}",
                    kind=RequirementKind.INTEGRATION,
                    priority=_priority("must"),
                    topic=topic,
                )
            )
        for topic in capability_class.topics:
            requirements.append(
                ExpectedRequirement(
                    ref_id=f"req-class-{topic}",
                    kind=RequirementKind.FUNCTIONAL,
                    priority=_priority("should"),
                    topic=topic,
                )
            )
        for topic in complexity.extra_topics:
            requirements.append(
                ExpectedRequirement(
                    ref_id=f"req-extra-{topic}",
                    kind=RequirementKind.FUNCTIONAL,
                    priority=_priority("should"),
                    topic=topic,
                )
            )

        sketch = RequirementSketch(
            sketch_id=self._sketch_id(seed, index, epoch, assignment),
            provenance=SketchProvenance(
                taxonomy_version=self._taxonomy.taxonomy_version,
                stratum=assignment,
                seed=seed,
                instance_index=index,
                epoch=epoch,
            ),
            assignment=assignment,
            expected_capabilities=list(domain.capabilities),
            expected_data_entities=list(domain.data_entities),
            expected_requirements=requirements,
            planted_defects=[],
            budget=ComplexityBudget(
                expected_services=scale.expected_services,
                expected_requirements_range=tuple(
                    complexity.expected_requirement_range
                ),
                throughput_class=scale.throughput_class,
                availability_posture=scale.availability_posture,
            ),
        )
        sketch.planted_defects = self._plant_defects(sketch, seed, index, epoch)
        return sketch

    def _sketch_id(
        self, seed: int, index: int, epoch: int, assignment: StratumAssignment
    ) -> str:
        material = (
            f"{self._taxonomy.taxonomy_version}|{seed}|{index}|{epoch}|"
            f"{assignment.key()}"
        )
        return f"sk-{sha256_hex(material)[:16]}"

    def _plant_defects(
        self,
        sketch: RequirementSketch,
        seed: int,
        index: int,
        epoch: int,
    ) -> list[PlantedDefect]:
        rng = _derive_rng(
            "defects",
            self._taxonomy.taxonomy_version,
            seed,
            index,
            epoch,
            sketch.assignment.key(),
        )
        defects: list[PlantedDefect] = []

        quality_refs = [
            r.ref_id
            for r in sketch.expected_requirements
            if r.kind is RequirementKind.QUALITY
        ]
        if rng.random() < self._rates.contradiction and len(quality_refs) >= 2:
            pair = rng.sample(quality_refs, 2)
            defects.append(
                PlantedDefect(
                    kind=PlantedDefectKind.CONTRADICTION,
                    target_ref=f"{pair[0]} x {pair[1]}",
                    description=(
                        "Rendered statement will assert mutually exclusive "
                        "postures for these quality requirements."
                    ),
                )
            )

        must_refs = [
            r.ref_id
            for r in sketch.expected_requirements
            if r.priority is Priority.MUST and r.kind is RequirementKind.FUNCTIONAL
        ]
        if rng.random() < self._rates.missing_must and must_refs:
            target = rng.choice(must_refs)
            defects.append(
                PlantedDefect(
                    kind=PlantedDefectKind.MISSING_MUST,
                    target_ref=target,
                    description=(
                        "Rendered statement will omit this MUST requirement; "
                        "the compiler should surface it as a gap or assumption."
                    ),
                )
            )

        if rng.random() < self._rates.ambiguity and sketch.expected_capabilities:
            target = rng.choice(sketch.expected_capabilities)
            defects.append(
                PlantedDefect(
                    kind=PlantedDefectKind.AMBIGUITY,
                    target_ref=target,
                    description=(
                        "Rendered statement will describe this capability "
                        "vaguely; the compiler should record an assumption."
                    ),
                )
            )
        return defects


def _priority(level: str) -> Priority:
    return Priority(level)
