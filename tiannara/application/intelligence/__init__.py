"""Autonomous Intelligence Runtime (Cap-D).

Additive on top of the live Cap-B contracts — names no runtime,
accelerator, or vendor. See docs/adr/adr-autonomous-intelligence-runtime.md.
"""

from .accounting import AutonomyAccountant, FULL_THRESHOLD, PARTIAL_THRESHOLD
from .autonomy import AutonomyCertification, certify_no_external_dependency
from .bridge import (
    DEFAULT_TASK_KIND_MAP,
    ContextAwareCompletion,
    LanguageModelBridge,
    LanguageModelIntelligenceAdapter,
)
from .cascade import CascadeExecutor, CascadeExhaustedError
from .context_assembler import (
    ContextAssembler,
    EvidenceSource,
    IsrContextExtractor,
    StaticEvidenceSource,
)
from .context_budgeter import (
    BudgetPlanning,
    ContextBudgetError,
    InstructionOverflowError,
    MustContextOverflowError,
    SchemaOverflowError,
    TokenBudget,
    plan_context_selection,
)
from .prompt_compiler import CompiledPrompt, PromptCompiler, TaskInstruction
from .registry import ProviderRegistry, RegistryError
from .router import (
    COST_MIN_POLICY,
    DEFAULT_POLICY,
    KEYLESS_POLICY,
    LATENCY_MIN_POLICY,
    OFFLINE_POLICY,
    PRIVACY_MAX_POLICY,
    QUALITY_MAX_POLICY,
    RoutingObjective,
    RoutingPolicy,
    order_candidates,
)
from .tokenizing import CharRatioEstimator, WhitespaceEstimator

__all__ = [
    "AutonomyAccountant",
    "AutonomyCertification",
    "FULL_THRESHOLD",
    "PARTIAL_THRESHOLD",
    "DEFAULT_TASK_KIND_MAP",
    "LanguageModelBridge",
    "LanguageModelIntelligenceAdapter",
    "ContextAwareCompletion",
    "CascadeExecutor",
    "CascadeExhaustedError",
    "ProviderRegistry",
    "RegistryError",
    "DEFAULT_POLICY",
    "KEYLESS_POLICY",
    "OFFLINE_POLICY",
    "PRIVACY_MAX_POLICY",
    "COST_MIN_POLICY",
    "LATENCY_MIN_POLICY",
    "QUALITY_MAX_POLICY",
    "RoutingObjective",
    "RoutingPolicy",
    "order_candidates",
    "certify_no_external_dependency",
    "ContextAssembler",
    "EvidenceSource",
    "IsrContextExtractor",
    "StaticEvidenceSource",
    "BudgetPlanning",
    "ContextBudgetError",
    "InstructionOverflowError",
    "MustContextOverflowError",
    "SchemaOverflowError",
    "TokenBudget",
    "plan_context_selection",
    "CompiledPrompt",
    "PromptCompiler",
    "TaskInstruction",
    "CharRatioEstimator",
    "WhitespaceEstimator",
]
