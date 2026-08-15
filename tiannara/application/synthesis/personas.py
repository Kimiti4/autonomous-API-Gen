"""Persona pool loading and deterministic selection.

Personas are authored, versioned configuration describing *how* a stakeholder
speaks. Selection is seeded from the sketch's provenance so the same sketch
always draws the same persona, keeping replay byte-stable.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from tiannara.domain.models.requirement_sketch import RequirementSketch
from tiannara.domain.services.canonical import sha256_hex

from .render_schemas import Persona, PersonaPool


class PersonaPoolValidationError(ValueError):
    pass


def load_persona_pool(path: str | Path) -> PersonaPool:
    with open(path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    try:
        pool = PersonaPool.model_validate(raw)
    except Exception as exc:
        raise PersonaPoolValidationError(str(exc)) from exc
    if not pool.personas:
        raise PersonaPoolValidationError("persona pool is empty")
    ids = [p.id for p in pool.personas]
    if len(ids) != len(set(ids)):
        raise PersonaPoolValidationError("duplicate persona ids")
    return pool


def select_persona(pool: PersonaPool, sketch: RequirementSketch) -> Persona:
    personas = pool.sorted_personas()
    digest = sha256_hex(
        "persona|"
        f"{sketch.provenance.taxonomy_version}|"
        f"{sketch.provenance.seed}|"
        f"{sketch.provenance.instance_index}"
    )
    index = int(digest, 16) % len(personas)
    return personas[index]
