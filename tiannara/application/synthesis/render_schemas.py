"""Schemas for statement rendering (B4).

Pure data models. The renderer orchestrates the LLM call; the planner builds
a ``RenderPlan``; personas are authored configuration. The
``RenderedInstance`` pairs the rendered statement with its ground-truth sketch
for downstream fidelity scoring, but the statement alone is what the
IntentCompiler ever receives.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from tiannara.domain.models.model_call import ModelCallRecord
from tiannara.domain.models.requirement_sketch import RequirementSketch
from tiannara.domain.services.canonical import canonical_hash


class Persona(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = ""
    style_directives: list[str] = Field(default_factory=list)


class PersonaPool(BaseModel):
    version: str = Field(min_length=1)
    personas: list[Persona] = Field(default_factory=list)

    def sorted_personas(self) -> list[Persona]:
        return sorted(self.personas, key=lambda p: p.id)

    def by_id(self, persona_id: str) -> Persona:
        for persona in self.personas:
            if persona.id == persona_id:
                return persona
        raise KeyError(f"Unknown persona id: {persona_id}")


class RenderMention(BaseModel):
    topic: str = Field(min_length=1)
    priority: str = "must"


class RenderPlan(BaseModel):
    """Deterministic materialization of a sketch for one persona.

    ``omitted_refs`` is carried for accounting and auditability but is
    deliberately excluded from ``prompt_payload()`` so the rendered statement
    cannot leak which requirements were intentionally hidden.
    """

    persona: Persona
    domain: str
    capabilities: list[str] = Field(default_factory=list)
    data_entities: list[str] = Field(default_factory=list)
    mentions: list[RenderMention] = Field(default_factory=list)
    contradictions: list[list[str]] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    omitted_refs: list[str] = Field(default_factory=list)

    def prompt_payload(self) -> dict:
        return {
            "domain": self.domain,
            "persona": {
                "name": self.persona.name,
                "style_directives": self.persona.style_directives,
            },
            "capabilities": self.capabilities,
            "data_entities": self.data_entities,
            "mentions": [m.model_dump(mode="json") for m in self.mentions],
            "contradictions": self.contradictions,
            "ambiguities": self.ambiguities,
        }

    def plan_hash(self) -> str:
        return canonical_hash(self.prompt_payload())


class RenderedStatementOutput(BaseModel):
    statement: str = Field(min_length=1)


class RenderedInstance(BaseModel):
    """A rendered statement paired with its ground truth (harness-side only)."""

    sketch_id: str
    statement: str
    persona_id: str
    plan_hash: str
    render_record: ModelCallRecord
    sketch: RequirementSketch

    def content_hash(self) -> str:
        return canonical_hash(
            {
                "sketch_id": self.sketch_id,
                "statement": self.statement,
                "persona_id": self.persona_id,
                "plan_hash": self.plan_hash,
            }
        )
