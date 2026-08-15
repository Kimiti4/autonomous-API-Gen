"""StatementRenderer -- turns a sketch + persona into a messy NL statement.

Orchestrates a single structured LLM call through the LanguageModelProvider
port. The prompt encodes the RenderPlan's ``prompt_payload()`` (which excludes
omitted refs) plus persona style directives, and instructs the model to
speak in the problem domain without prescribing technology.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from tiannara.domain.models.model_call import (
    DecodingParameters,
    StructuredCompletionRequest,
)
from tiannara.domain.ports.language_model import LanguageModelProvider
from tiannara.domain.services.canonical import canonical_json

from .personas import select_persona
from .render_planner import build_render_plan
from .render_schemas import (
    PersonaPool,
    RenderedInstance,
    RenderedStatementOutput,
    RenderPlan,
)

SYNTHESIS_RENDER_TASK = "synthesis.render"
SYNTHESIS_RENDER_SCHEMA = "synthesis.render.v1"


class RenderConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    model_id: str = "recorded@1"
    decoding: DecodingParameters = Field(default_factory=DecodingParameters)


def build_render_request(
    plan: RenderPlan, config: RenderConfig
) -> StructuredCompletionRequest:
    prompt = (
        "You are the Stakeholder Simulation agent in an evolutionary software "
        "architecture platform.\n"
        "Produce ONE natural-language problem statement spoken by the persona "
        "below, as if in an initial requirements interview.\n"
        "Describe the problem domain only; do NOT prescribe specific "
        "technologies, frameworks, or vendors.\n"
        "Mention the listed capabilities and requirements in the persona's "
        "voice. Honour the contradictions and ambiguities exactly as given.\n"
        "Respond ONLY with JSON conforming to the render schema.\n\n"
        f"RENDER SPECIFICATION:\n{canonical_json(plan.prompt_payload())}\n"
    )
    return StructuredCompletionRequest(
        model_id=config.model_id,
        task=SYNTHESIS_RENDER_TASK,
        prompt=prompt,
        output_schema_id=SYNTHESIS_RENDER_SCHEMA,
        decoding=config.decoding,
    )


class StatementRenderer:
    def __init__(
        self,
        provider: LanguageModelProvider,
        config: RenderConfig | None = None,
    ) -> None:
        self._provider = provider
        self._config = config or RenderConfig()

    def render(self, sketch, persona) -> RenderedInstance:
        plan = build_render_plan(sketch, persona)
        request = build_render_request(plan, self._config)
        result = self._provider.complete_structured(request, RenderedStatementOutput)
        return RenderedInstance(
            sketch_id=sketch.sketch_id,
            statement=result.output.statement,
            persona_id=persona.id,
            plan_hash=plan.plan_hash(),
            render_record=result.record,
            sketch=sketch,
        )

    def render_corpus(self, sketches, pool: PersonaPool) -> list[RenderedInstance]:
        instances = []
        for sketch in sketches:
            persona = select_persona(pool, sketch)
            instances.append(self.render(sketch, persona))
        return instances
