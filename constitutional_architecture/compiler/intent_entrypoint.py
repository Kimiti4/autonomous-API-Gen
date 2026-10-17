"""Fail-closed orchestration from intent compilation to constitutional compilation.

External language-model providers are used only by the intent compiler's
semantic extraction/resolution boundary. This module owns the deterministic
projection, source binding, and compiler gate. It never treats an LLM response,
a projected ISR, or a compiler's self-reported success as runtime certification.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from constitutional_architecture.compiler.compilation_config import CompilationConfig
from constitutional_architecture.compiler.compiler_result import CompilationResult
from constitutional_architecture.compiler.pipeline import CompilerPipeline
from constitutional_architecture.compiler.source_binding import (
    ConstitutionalBindingReport,
    ConstitutionalSourceBinding,
    verify_constitutional_source_binding,
)
from constitutional_architecture.isr.semantics.intent_projection import (
    IntentProjectionResult,
    project_intent_to_constitutional_isr,
)
from tiannara.application.intent.compiler import IntentCompiler
from tiannara.application.intent.schemas import IntentCompilationResult


@dataclass(frozen=True)
class IntentGenerationResult:
    """Evidence-bearing outcome of the deterministic intent-to-compiler boundary."""

    intent: IntentCompilationResult
    projection: IntentProjectionResult
    binding_report: ConstitutionalBindingReport | None
    compilation: CompilationResult | None
    status: Literal[
        "projection_blocked",
        "binding_blocked",
        "compilation_failed",
        "compiled",
    ]

    @property
    def ready_for_downstream_verification(self) -> bool:
        """Compilation succeeded; independent build/runtime certification is separate."""
        return self.status == "compiled" and self.compilation is not None and self.compilation.success


def compile_intent_to_constitutional_isr(
    *,
    intent_compiler: IntentCompiler,
    source_statement: str,
    system_id: str,
    compiler_pipeline: CompilerPipeline | None = None,
    compilation_config: CompilationConfig | None = None,
    taskflow_semantic_gate: bool = False,
) -> IntentGenerationResult:
    """Run intent semantics, loss-aware projection, source binding, then compile.

    The function intentionally returns without calling the compiler if the
    typed model cannot be projected without blockers or if a recomputed binding
    report is incomplete. It never silently substitutes the legacy ISR envelope.
    """
    intent_result = intent_compiler.compile_full(
        source_statement,
        system_id,
        taskflow_semantic_gate=taskflow_semantic_gate,
    )
    typed_model = intent_result.isr.system_model()
    if typed_model is None:
        raise ValueError(
            "intent compiler returned a legacy ISR without a typed SystemModel; "
            "constitutional compilation is blocked"
        )

    source_bytes = source_statement.encode("utf-8")
    projection = project_intent_to_constitutional_isr(
        source_bytes=source_bytes,
        graph=intent_result.requirement_graph,
        system_model=typed_model,
        system_id=system_id,
    )
    if not projection.ready_for_compilation or projection.candidate_isr is None:
        return IntentGenerationResult(
            intent=intent_result,
            projection=projection,
            binding_report=None,
            compilation=None,
            status="projection_blocked",
        )

    binding = ConstitutionalSourceBinding(
        source_bytes=source_bytes,
        expected_source_sha256=projection.source_sha256,
        graph=intent_result.requirement_graph,
        graph_to_isr_requirement_ids=dict(projection.requirement_id_map),
        system_model=typed_model,
    )
    report = verify_constitutional_source_binding(
        binding=binding,
        isr=projection.candidate_isr,
    )
    if not report.complete:
        return IntentGenerationResult(
            intent=intent_result,
            projection=projection,
            binding_report=report,
            compilation=None,
            status="binding_blocked",
        )

    pipeline = compiler_pipeline or CompilerPipeline()
    config = compilation_config or CompilationConfig(project_name=typed_model.system_name)
    compilation = pipeline.compile_source_bound(
        projection.candidate_isr,
        config,
        source_binding=binding,
    )
    return IntentGenerationResult(
        intent=intent_result,
        projection=projection,
        binding_report=report,
        compilation=compilation,
        status="compiled" if compilation.success else "compilation_failed",
    )
