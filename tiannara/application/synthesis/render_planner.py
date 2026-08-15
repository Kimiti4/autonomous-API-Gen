"""Render planning and defect accounting.

``build_render_plan`` materializes a sketch's planted defects into concrete
rendering instructions for a persona. ``measure_defect_rates`` aggregates
planted-defect frequencies across a corpus so injection rates are measurable
and can be compared against the configured DefectRates.
"""

from __future__ import annotations

from tiannara.domain.models.requirement_sketch import (
    PlantedDefectKind,
    RequirementSketch,
)

from .render_schemas import Persona, RenderMention, RenderPlan


def build_render_plan(sketch: RequirementSketch, persona: Persona) -> RenderPlan:
    omitted_refs: list[str] = []
    ambiguity_targets: list[str] = []
    contradiction_refs: list[str] = []

    for defect in sketch.planted_defects:
        if defect.kind is PlantedDefectKind.MISSING_MUST:
            omitted_refs.append(defect.target_ref)
        elif defect.kind is PlantedDefectKind.AMBIGUITY:
            ambiguity_targets.append(defect.target_ref)
        elif defect.kind is PlantedDefectKind.CONTRADICTION:
            contradiction_refs.append(defect.target_ref)

    ref_to_topic = {r.ref_id: r.topic for r in sketch.expected_requirements}
    mentions = [
        RenderMention(topic=r.topic, priority=r.priority.value)
        for r in sketch.expected_requirements
        if r.ref_id not in omitted_refs
    ]

    contradictions: list[list[str]] = []
    for combined in contradiction_refs:
        parts = [p.strip() for p in combined.split(" x ")]
        if len(parts) != 2:
            continue
        topic_a = ref_to_topic.get(parts[0], parts[0])
        topic_b = ref_to_topic.get(parts[1], parts[1])
        contradictions.append([topic_a, topic_b])

    return RenderPlan(
        persona=persona,
        domain=sketch.assignment.domain,
        capabilities=list(sketch.expected_capabilities),
        data_entities=list(sketch.expected_data_entities),
        mentions=mentions,
        contradictions=contradictions,
        ambiguities=ambiguity_targets,
        omitted_refs=omitted_refs,
    )


def measure_defect_rates(sketches: list[RequirementSketch]) -> dict[str, float]:
    totals = {kind.value: 0 for kind in PlantedDefectKind}
    count = len(sketches)
    if count == 0:
        return {key: 0.0 for key in totals}
    for sketch in sketches:
        present = {defect.kind.value for defect in sketch.planted_defects}
        for kind_value in present:
            totals[kind_value] += 1
    return {key: totals[key] / count for key in totals}
