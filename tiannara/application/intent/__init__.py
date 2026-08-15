"""Intent Compiler (Cap-B3): stages 1-6 over the LanguageModelProvider port.

Public re-export surface. Each stage lives in its own module so it can be
replaced independently; this package only composes them.
"""

from .compiler import IntentCompiler
from .config import IntentCompilerConfig
from .errors import IntentCompilationError, RepairBudgetExceeded
from .graph_builder import attempt_graph, graph_from_extraction, prevalidate
from .prompts import (
    build_elicitation_request,
    build_extraction_request,
    build_repair_request,
    derive_system_id,
    normalize,
)
from .schemas import (
    ElicitationOutput,
    ExtractionOutput,
    IntentCompilationResult,
    NormalizedIntent,
    RepairOutput,
)
from .synthesis import synthesize_system_model

__all__ = [
    "IntentCompiler",
    "IntentCompilerConfig",
    "IntentCompilationError",
    "RepairBudgetExceeded",
    "attempt_graph",
    "graph_from_extraction",
    "prevalidate",
    "build_elicitation_request",
    "build_extraction_request",
    "build_repair_request",
    "derive_system_id",
    "normalize",
    "ElicitationOutput",
    "ExtractionOutput",
    "IntentCompilationResult",
    "NormalizedIntent",
    "RepairOutput",
    "synthesize_system_model",
]
