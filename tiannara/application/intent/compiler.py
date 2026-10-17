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

from collections.abc import Callable
from tiannara.domain.models.isr import IntermediateSoftwareRepresentation
from tiannara.application.compiler.source_projection import create_source_projection_context
from tiannara.domain.models.requirement_graph import RequirementGraph, RequirementKind
from tiannara.domain.models.semantic_resolution import (
    SemanticResolutionRecord,
    build_initial_resolution_record,
    require_taskflow_semantics,
    resolutions_by_field,
)
from tiannara.domain.models.taskflow_semantic_contract import (
    validate_taskflow_semantic_contract,
)
from tiannara.domain.models.authorization_semantic_obligations import (
    AuthorizationSemanticObligations,
    consume_authorization_semantics,
)
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
    NormalizedIntent,
    TaskFlowSemanticProjection,
)
from .synthesis import synthesize_system_model


class IntentCompiler:
    def __init__(
        self,
        provider: LanguageModelProvider,
        config: IntentCompilerConfig | None = None,
        taskflow_semantic_resolver: Callable[[RequirementGraph, SemanticResolutionRecord], SemanticResolutionRecord] | None = None,
        taskflow_semantic_projector: Callable[[RequirementGraph, ElicitationOutput, NormalizedIntent, SemanticResolutionRecord], TaskFlowSemanticProjection] | None = None,
        taskflow_semantic_gate_required: bool = False,
    ) -> None:
        self._provider = provider
        self._config = config or IntentCompilerConfig()
        self._taskflow_semantic_resolver = taskflow_semantic_resolver
        self._taskflow_semantic_projector = taskflow_semantic_projector
        # A TaskFlow-scoped compiler instance cannot be downgraded by choosing
        # the generic port method or passing taskflow_semantic_gate=False.
        # Generic projects retain the existing default unless they opt into
        # this explicit profile at composition time.
        self._taskflow_semantic_gate_required = taskflow_semantic_gate_required

    def compile(self, statement: str, hints: dict) -> IntermediateSoftwareRepresentation:
        """Port-compatible entry point (matches the domain IntentCompiler port)."""
        system_id = hints.get("system_id") or derive_system_id(statement)
        return self.compile_full(
            statement,
            system_id,
            taskflow_semantic_gate=self._taskflow_semantic_gate_required,
        ).isr

    def compile_full(
        self,
        statement: str,
        system_id: str,
        *,
        taskflow_semantic_gate: bool = False,
    ) -> IntentCompilationResult:
        # The instance-level profile is authoritative. A caller may enable the
        # gate for a single call, but cannot disable a gate required by the
        # composition root.
        taskflow_semantic_gate = (
            taskflow_semantic_gate or self._taskflow_semantic_gate_required
        )
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

        # Mandatory source/graph identity check for every project, before any
        # semantic synthesis or backend-facing SystemModel is created. This
        # detects stale or substituted graph provenance; it does not by itself
        # prove semantic extraction fidelity, which remains a separate gate.
        if graph.provenance.source_statement_hash != normalized.source_statement_hash:
            raise ValueError(
                "requirement graph source provenance does not match the active normalized source snapshot"
            )

        # 6. TaskFlow semantic gate must run before SystemModel synthesis.
        # Without a configured native resolver, every mandatory field remains
        # explicitly unresolved and this entry point fails closed.
        semantic_resolution_record = None
        authorization_obligations: AuthorizationSemanticObligations | None = None
        if taskflow_semantic_gate:
            semantic_resolution_record = build_initial_resolution_record(graph)
            if self._taskflow_semantic_resolver is not None:
                semantic_resolution_record = self._taskflow_semantic_resolver(
                    graph, semantic_resolution_record
                )
            if not isinstance(semantic_resolution_record, SemanticResolutionRecord):
                raise TypeError("TaskFlow semantic resolver must return SemanticResolutionRecord")
            require_taskflow_semantics(graph, semantic_resolution_record)
            # Resolution alone proves that fields are present, not that each
            # field carries the minimum structured contract needed by the
            # TaskFlow projection. Reject malformed/placeholder payloads before
            # invoking any projector or constructing a SystemModel.
            validate_taskflow_semantic_contract(semantic_resolution_record)
            # Consume authorization entries into a typed, graph-bound contract
            # before projection. This is not runtime enforcement; the downstream
            # backend/runtime gate remains blocked until it enforces the contract.
            authorization_obligations = consume_authorization_semantics(
                semantic_resolution_record
            )

        # Freeze exact caller source bytes and the canonical requirement graph
        # before SystemModel synthesis. Generic projects receive an empty
        # resolution ledger; this preserves UNKNOWN rather than inventing
        # semantic decisions. TaskFlow carries its reviewed resolution ledger.
        projection_resolution = semantic_resolution_record or SemanticResolutionRecord(
            graph_id=graph.graph_id,
            graph_hash=graph.content_hash(),
            required_fields=(),
            resolutions=(),
        )
        source_projection_context = create_source_projection_context(
            source_id=f"intent:{normalized.source_statement_hash}",
            source_bytes=statement.encode("utf-8"),
            graph=graph,
            semantic_resolution=projection_resolution,
        )

        # 7. Synthesis + boundary enforcement. A resolved ledger is not enough:
        # the ordinary heuristic synthesizer does not consume TaskFlow's
        # mandatory semantic values. Require an explicit, auditable projection
        # contract before allowing the gate-enabled path to construct a model.
        if taskflow_semantic_gate:
            if self._taskflow_semantic_projector is None:
                raise ValueError(
                    "TaskFlow semantic projection is not configured; resolved semantics "
                    "must be explicitly projected into SystemModel before synthesis"
                )
            projection = self._taskflow_semantic_projector(
                graph, elicitation_output, normalized, semantic_resolution_record
            )
            if not isinstance(projection, TaskFlowSemanticProjection):
                raise TypeError(
                    "TaskFlow semantic projector must return TaskFlowSemanticProjection"
                )
            expected_fields = set(semantic_resolution_record.required_fields)
            projected_values = projection.projected_values
            projected_fields = set(projected_values)
            if projected_fields != expected_fields:
                missing = sorted(expected_fields - projected_fields)
                unexpected = sorted(projected_fields - expected_fields)
                raise ValueError(
                    "TaskFlow semantic projection coverage mismatch; "
                    f"missing={missing}, unexpected={unexpected}"
                )
            reviewed_values = {
                path: resolution.value
                for path, resolution in resolutions_by_field(
                    semantic_resolution_record
                ).items()
            }
            if projected_values != reviewed_values:
                raise ValueError(
                    "TaskFlow semantic projection changed or omitted reviewed values"
                )
            model = projection.system_model
            if (
                model.requirements_ref.graph_id != graph.graph_id
                or model.requirements_ref.graph_hash != graph.content_hash()
            ):
                raise ValueError(
                    "TaskFlow projected SystemModel is not bound to the active requirement graph"
                )
        else:
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
            semantic_resolution_record=semantic_resolution_record,
            authorization_semantic_obligations=authorization_obligations,
            source_projection_context=source_projection_context,
        )
