"""IntentCompiler -- orchestrates stages 1-6 over the LanguageModelProvider port.

Stage flow:
  1. normalize (deterministic)
  2. elicit   (LLM) -> capabilities, explicit assumptions
  3. extract  (LLM) -> candidate requirement graph
  4. pre-validate (deterministic) -> issues
  5. repair loop (bounded, LLM) -> corrected graph
  6. synthesize (deterministic) -> SystemModel, wrapped via from_system_model

Every LLM call is captured as a ModelCallRecord; their provenance tags are
written into RequirementGraph.provenance.model_versions. Authoritative
requirement analysis is deliberately NOT performed here -- it belongs to the
Evolution Engine's first stage.
"""

from __future__ import annotations

from tiannara.domain.models.isr import IntermediateSoftwareRepresentation
from tiannara.domain.models.requirement_graph import RequirementKind
from tiannara.domain.ports.language_model import LanguageModelProvider

from .config import IntentCompilerConfig
from .errors import RepairBudgetExceeded
from .graph_builder import attempt_graph
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
)
from .synthesis import synthesize_system_model


class IntentCompiler:
    def __init__(
        self,
        provider: LanguageModelProvider,
        config: IntentCompilerConfig | None = None,
    ) -> None:
        self._provider = provider
        self._config = config or IntentCompilerConfig()

    def compile(self, statement: str, hints: dict) -> IntermediateSoftwareRepresentation:
        """Port-compatible entry point (matches the domain IntentCompiler port)."""
        system_id = hints.get("system_id") or derive_system_id(statement)
        return self.compile_full(statement, system_id).isr

    def compile_full(self, statement: str, system_id: str) -> IntentCompilationResult:
        normalized = normalize(statement)
        records: list = []

        # 2. Elicitation
        if self._config.enable_elicitation:
            elicitation = self._provider.complete_structured(
                build_elicitation_request(normalized, self._config), ElicitationOutput
            )
            records.append(elicitation.record)
            elicitation_output = elicitation.output
        else:
            elicitation_output = ElicitationOutput()

        # 3. Extraction
        extraction_result = self._provider.complete_structured(
            build_extraction_request(normalized, elicitation_output, self._config),
            ExtractionOutput,
        )
        records.append(extraction_result.record)
        extraction: ExtractionOutput = extraction_result.output

        # 4/5. Pre-validation + bounded repair loop
        tags = [r.provenance_tag() for r in records]
        graph, issues = attempt_graph(
            extraction,
            elicitation_output.assumptions,
            tags,
            normalized.source_statement_hash,
        )
        iterations = 0
        while issues and iterations < self._config.max_repair_iterations:
            iterations += 1
            repair_result = self._provider.complete_structured(
                build_repair_request(
                    normalized, extraction, issues, iterations, self._config
                ),
                ExtractionOutput,
            )
            records.append(repair_result.record)
            extraction = repair_result.output
            tags = [r.provenance_tag() for r in records]
            graph, issues = attempt_graph(
                extraction,
                elicitation_output.assumptions,
                tags,
                normalized.source_statement_hash,
            )
        if issues or graph is None:
            raise RepairBudgetExceeded(issues, iterations)

        # 6. Synthesis + boundary enforcement
        model = synthesize_system_model(graph, elicitation_output, normalized)
        isr = IntermediateSoftwareRepresentation.from_system_model(
            system_id,
            model,
            lineage=[f"intent:{normalized.source_statement_hash}"],
        )

        assumption_ids = [
            node.id
            for node in graph.nodes
            if node.kind is RequirementKind.ASSUMPTION
        ]
        return IntentCompilationResult(
            system_id=system_id,
            isr=isr,
            requirement_graph=graph,
            call_records=records,
            repair_iterations=iterations,
            assumption_ids=assumption_ids,
        )
