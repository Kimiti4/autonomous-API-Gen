"""B1-B4 synthesis surface: taxonomy, sampler, personas, rendering.

Re-exports the versioned configuration, the seeded sampler, the persona pool,
and the statement renderer so Cap-B stages import from a single, stable
location.
"""

from .personas import PersonaPoolValidationError, load_persona_pool, select_persona
from .render_planner import build_render_plan, measure_defect_rates
from .render_schemas import (
    Persona,
    PersonaPool,
    RenderMention,
    RenderPlan,
    RenderedInstance,
    RenderedStatementOutput,
)
from .sampler import DefectRates, StratifiedSampler
from .statement_renderer import (
    RenderConfig,
    StatementRenderer,
    build_render_request,
)
from .taxonomy import StratificationTaxonomy

__all__ = [
    "PersonaPoolValidationError",
    "load_persona_pool",
    "select_persona",
    "Persona",
    "PersonaPool",
    "RenderMention",
    "RenderPlan",
    "RenderedInstance",
    "RenderedStatementOutput",
    "build_render_plan",
    "measure_defect_rates",
    "DefectRates",
    "StratifiedSampler",
    "RenderConfig",
    "StatementRenderer",
    "build_render_request",
    "StratificationTaxonomy",
]
