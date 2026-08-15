"""
Fitness Update Algorithm.

The bridge between the static genome evaluator and runtime telemetry.

Given the operational ISR Projection (SLODefinition nodes), observed runtime
telemetry, and the static genome fitness, it:

1. Computes per-endpoint SLO attainment (availability ratio, latency ratio,
   error-budget burn).
2. Blends static fitness with runtime attainment into the final fitness.
3. Produces directed MutationDirectives over genes — never over the ISR.

Constitutional Alignment:
- Axiom II (Genome Isolation): the only mutation surface is the Architecture
  Genome.
- Axiom V (Dual-Track Evolution): non-functional fitness is updated from the
  runtime track (Pass 10 instrumentation) in parallel with the functional
  track.
- Axiom VII (Auditability): every directive records its rationale.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from constitutional_architecture.core.evolution.fitness import SystemFitnessEvaluator
from constitutional_architecture.core.learning.models import (
    EndpointObservation, FitnessUpdate, MutationDirective, SLOAttainment,
)
from constitutional_architecture.core.models.genome import (
    APIDesign, ApplicationArchitecture, ArchitectureGenome,
    DeploymentTopology, ObservabilityStrategy, ResiliencePosture,
    StateManagement,
)
from constitutional_architecture.core.models.intent import QualityAttribute
from constitutional_architecture.core.models.isr import (
    EdgeType, ISRNode, NodeType, UniversalISR,
)

# Ordered ladders for directed categorical mutation.
# Moving "increase" steps toward the value that scores higher for the
# quality attribute under pressure (per the CKB scoring map).
GENE_LADDERS: Dict[str, Tuple[Any, ...]] = {
    "resilience_posture": (
        ResiliencePosture.FAIL_FAST,
        ResiliencePosture.RETRY_WITH_BACKOFF,
        ResiliencePosture.CIRCUIT_BREAKER,
        ResiliencePosture.BULKHEAD_ISOLATION,
    ),
    "deployment_topology": (
        DeploymentTopology.SINGLE_REGION,
        DeploymentTopology.ON_PREM,
        DeploymentTopology.EDGE,
        DeploymentTopology.HYBRID,
        DeploymentTopology.MULTI_REGION,
    ),
    "api_design": (
        APIDesign.GRAPHQL,
        APIDesign.REST,
        APIDesign.EVENT_STREAM,
        APIDesign.HYBRID,
        APIDesign.GRPC,
    ),
    "state_management": (
        StateManagement.SESSION_BASED,
        StateManagement.STRONG_CONSISTENCY,
        StateManagement.EVENTUAL_CONSISTENCY,
        StateManagement.DISTRIBUTED_CACHE,
        StateManagement.STATELESS,
    ),
    "observability_strategy": (
        ObservabilityStrategy.LOGS_ONLY,
        ObservabilityStrategy.METRICS_AND_LOGS,
        ObservabilityStrategy.DDA,
        ObservabilityStrategy.FULL_OBSERVABILITY,
    ),
    "app_arch": (
        ApplicationArchitecture.MONOLITHIC,
        ApplicationArchitecture.MODULAR_MONOLITH,
        ApplicationArchitecture.P2P,
        ApplicationArchitecture.SOA,
        ApplicationArchitecture.CQRS,
        ApplicationArchitecture.EVENT_DRIVEN,
        ApplicationArchitecture.LAMBDA,
        ApplicationArchitecture.MICROSERVICES,
    ),
}

CONTINUOUS_GENES: Tuple[str, ...] = (
    "fault_tolerance",
    "observability_depth",
    "cost_monitoring_intensity",
)

MAX_MULTIPLIER = 1.1
MIN_MULTIPLIER = 0.5


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def step_gene(genome: ArchitectureGenome, gene_id: str,
              action: str) -> Optional[Any]:
    """Compute the next gene value one ladder step / 10% range in the
    requested direction. Returns None when the gene is already at the
    extreme (no-op) or is not a mutable gene."""
    direction = 1 if action == "increase" else -1

    if gene_id in genome.categorical_genes:
        ladder = GENE_LADDERS.get(gene_id)
        if ladder is None:
            return None
        current = genome.categorical_genes[gene_id].value
        try:
            index = ladder.index(current)
        except ValueError:
            return None
        target_index = index + direction
        if target_index < 0 or target_index >= len(ladder):
            return None
        return ladder[target_index]

    if gene_id in genome.continuous_genes:
        gene = genome.continuous_genes[gene_id]
        span = gene.max_value - gene.min_value
        if span <= 0:
            return None
        step = span * 0.1
        new_value = _clamp(gene.value + direction * step,
                           gene.min_value, gene.max_value)
        if new_value == gene.value:
            return None
        return new_value

    return None


class FitnessUpdateAlgorithm:
    """The Fitness Update Algorithm: SLO attainment, fitness blending, and
    directed mutation directives."""

    def __init__(self, evaluator: Optional[SystemFitnessEvaluator] = None) -> None:
        self._evaluator = evaluator or SystemFitnessEvaluator()

    # ------------------------------------------------------------------
    # SLO attainment
    # ------------------------------------------------------------------

    def compute_attainment(
        self,
        slo_attrs: Mapping[str, Any],
        observation: Optional[EndpointObservation],
    ) -> SLOAttainment:
        reliability = float(slo_attrs.get("reliability_target", 0.99))
        tolerance = float(slo_attrs.get("latency_tolerance_ms", 200.0))
        error_budget = float(slo_attrs.get("error_budget", 1.0 - reliability))

        if observation is None:
            return SLOAttainment(
                endpoint_id=slo_attrs.get("endpoint_id", ""),
                reliability_target=reliability,
                error_budget=error_budget,
                latency_tolerance_ms=tolerance,
                observed=False,
            )

        availability_attainment = _clamp(
            observation.availability / reliability, 0.0, 1.0)
        latency_attainment = _clamp(
            tolerance / observation.p95_latency_ms, 0.0, 1.0) \
            if observation.p95_latency_ms > 0 else 1.0
        budget_burn = observation.error_rate / error_budget \
            if error_budget > 0 else 0.0

        return SLOAttainment(
            endpoint_id=observation.endpoint_id,
            reliability_target=reliability,
            error_budget=error_budget,
            latency_tolerance_ms=tolerance,
            observed_availability=observation.availability,
            observed_p95_ms=observation.p95_latency_ms,
            error_rate=observation.error_rate,
            availability_attainment=availability_attainment,
            latency_attainment=latency_attainment,
            budget_burn=budget_burn,
            observed=True,
        )

    def _extract_slos(self, isr: UniversalISR) -> List[Dict[str, Any]]:
        slo_nodes: List[ISRNode] = [
            node for node in isr.nodes.values()
            if node.type == NodeType.SLO_DEFINITION
        ]
        monitors: Dict[str, str] = {}
        for edge in isr.edges:
            if edge.type == EdgeType.MONITORS:
                monitors[edge.target_id] = edge.source_id

        extracted = []
        for node in slo_nodes:
            attrs = dict(node.semantic_attributes)
            attrs["slo_id"] = node.id
            attrs["endpoint_id"] = monitors.get(node.id, "")
            extracted.append(attrs)
        return extracted

    # ------------------------------------------------------------------
    # Runtime multiplier + directives
    # ------------------------------------------------------------------

    def _runtime_multiplier(self, attainments: List[SLOAttainment]) -> float:
        if not attainments:
            return 1.0
        observed = [a for a in attainments if a.observed]
        if observed:
            ratios = [
                min(a.availability_attainment, a.latency_attainment)
                for a in observed
            ]
            mean_ratio = sum(ratios) / len(ratios)
        else:
            mean_ratio = 0.0
        coverage = len(observed) / len(attainments)
        return _clamp(0.5 + 0.6 * mean_ratio * coverage,
                      MIN_MULTIPLIER, MAX_MULTIPLIER)

    @staticmethod
    def _breach_severity(attr: SLOAttainment) -> float:
        if not attr.observed or attr.met:
            return 0.0
        availability_gap = max(
            0.0, (attr.reliability_target - attr.observed_availability)
            / attr.reliability_target)
        latency_gap = max(
            0.0, (attr.observed_p95_ms - attr.latency_tolerance_ms)
            / attr.latency_tolerance_ms)
        burn_gap = max(0.0, attr.budget_burn - 1.0)
        return _clamp(max(availability_gap, latency_gap, burn_gap), 0.0, 1.0)

    def _directives_from_attainment(
        self, attainments: List[SLOAttainment],
    ) -> List[MutationDirective]:
        directives: List[MutationDirective] = []
        severity_by_gene: Dict[str, MutationDirective] = {}

        def add(directive: MutationDirective) -> None:
            existing = severity_by_gene.get(directive.gene_id)
            if existing is None or directive.severity > existing.severity:
                severity_by_gene[directive.gene_id] = directive

        observed_count = sum(1 for a in attainments if a.observed)
        missing_telemetry = len(attainments) - observed_count

        for attr in attainments:
            if not attr.observed:
                continue
            severity = self._breach_severity(attr)
            if severity <= 0.0:
                continue

            if attr.observed_availability < attr.reliability_target:
                add(MutationDirective(
                    "fault_tolerance", "increase", severity,
                    f"{attr.endpoint_id} availability {attr.observed_availability:.4f} "
                    f"below target {attr.reliability_target}"))
                add(MutationDirective(
                    "resilience_posture", "increase", severity,
                    f"{attr.endpoint_id} availability breach"))
                add(MutationDirective(
                    "deployment_topology", "increase", severity * 0.6,
                    f"{attr.endpoint_id} availability breach"))

            if attr.observed_p95_ms > attr.latency_tolerance_ms:
                add(MutationDirective(
                    "api_design", "increase", severity,
                    f"{attr.endpoint_id} p95 {attr.observed_p95_ms:.0f}ms "
                    f"above tolerance {attr.latency_tolerance_ms:.0f}ms"))
                add(MutationDirective(
                    "state_management", "increase", severity * 0.8,
                    f"{attr.endpoint_id} latency breach"))
                add(MutationDirective(
                    "observability_depth", "increase", severity * 0.5,
                    f"{attr.endpoint_id} latency breach"))

        if missing_telemetry:
            add(MutationDirective(
                "observability_strategy", "increase", 0.6,
                f"{missing_telemetry} SLO(s) without runtime telemetry"))
            add(MutationDirective(
                "observability_depth", "increase", 0.6,
                f"{missing_telemetry} SLO(s) without runtime telemetry"))

        all_met = all(a.observed and a.met for a in attainments)
        if all_met and not missing_telemetry:
            add(MutationDirective(
                "cost_monitoring_intensity", "decrease", 0.2,
                "all SLOs met; throttle cost monitoring"))
            add(MutationDirective(
                "deployment_topology", "decrease", 0.15,
                "all SLOs met; simplify topology"))

        directives.extend(severity_by_gene.values())
        return directives

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def static_fitness(
        self,
        genome: ArchitectureGenome,
        quality_priorities: Optional[Mapping[QualityAttribute, float]] = None,
    ) -> float:
        if quality_priorities:
            return self._evaluator.evaluate_weighted(genome, quality_priorities)
        scores = self._evaluator.evaluate(genome)
        return sum(scores.values()) / len(scores)

    def evaluate(
        self,
        genome: ArchitectureGenome,
        isr: UniversalISR,
        observations: Sequence[EndpointObservation],
        quality_priorities: Optional[Mapping[QualityAttribute, float]] = None,
    ) -> FitnessUpdate:
        observation_map = {o.endpoint_id: o for o in observations}
        slo_attrs_list = self._extract_slos(isr)

        attainments = [
            self.compute_attainment(
                attrs, observation_map.get(attrs.get("endpoint_id", "")))
            for attrs in slo_attrs_list
        ]

        multiplier = self._runtime_multiplier(attainments)
        static = self.static_fitness(genome, quality_priorities)
        final = round(static * multiplier, 4)
        directives = self._directives_from_attainment(attainments)

        met_count = sum(1 for a in attainments if a.observed and a.met)
        reasoning = (
            f"{len(attainments)} SLO(s), {met_count} met, "
            f"{len(attainments) - observed_count(attainments)} unobserved; "
            f"runtime multiplier {multiplier:.2f}"
        )
        return FitnessUpdate(
            genome_id=genome.genome_id,
            static_fitness=round(static, 4),
            runtime_multiplier=round(multiplier, 4),
            final_fitness=final,
            attainment=tuple(attainments),
            directives=tuple(directives),
            reasoning=reasoning,
        )

    def evaluate_from_signals(
        self,
        genome: ArchitectureGenome,
        dimension_scores: Mapping[str, float],
        reasoning: str = "",
    ) -> FitnessUpdate:
        """Bridge from the Phase 6 sensory layer: FitnessSignal dimensions
        (reliability, performance, observability, deployment_completeness,
        scalability) blended directly into the runtime multiplier."""
        values = [_clamp(float(v), 0.0, 1.0) for v in dimension_scores.values()]
        multiplier = _clamp(sum(values) / len(values) if values else 1.0,
                            MIN_MULTIPLIER, MAX_MULTIPLIER)
        static = self.static_fitness(genome)

        directives: List[MutationDirective] = []
        for dim, score in dimension_scores.items():
            severity = _clamp(1.0 - float(score), 0.0, 1.0)
            if severity <= 0.0:
                continue
            for dim_name, (gene_id, factor) in {
                "reliability": ("fault_tolerance", 0.8),
                "deployment_completeness": ("deployment_topology", 0.7),
                "performance": ("api_design", 0.8),
                "observability": ("observability_strategy", 0.7),
                "scalability": ("app_arch", 0.5),
            }.items():
                if dim == dim_name:
                    directives.append(MutationDirective(
                        gene_id, "increase", severity * factor,
                        f"runtime dimension {dim} at {float(score):.2f}"))

        return FitnessUpdate(
            genome_id=genome.genome_id,
            static_fitness=round(static, 4),
            runtime_multiplier=round(multiplier, 4),
            final_fitness=round(static * multiplier, 4),
            directives=tuple(directives),
            reasoning=reasoning or "blended from Phase 6 fitness signals",
        )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------

    def apply_directives(
        self,
        genome: ArchitectureGenome,
        directives: Sequence[MutationDirective],
        max_severity: Optional[float] = None,
    ) -> Tuple[ArchitectureGenome, List[MutationDirective]]:
        """Apply directives to a clone of the genome. Deduplicates by gene
        (highest severity wins) and never moves a gene past its ladder/range
        extreme. Returns the candidate genome and the directives actually
        applied."""
        best: Dict[str, MutationDirective] = {}
        for directive in directives:
            if max_severity is not None and directive.severity > max_severity:
                continue
            existing = best.get(directive.gene_id)
            if existing is None or directive.severity > existing.severity:
                best[directive.gene_id] = directive

        candidate = genome.clone()
        applied: List[MutationDirective] = []
        for directive in sorted(best.values(),
                                key=lambda d: d.severity, reverse=True):
            new_value = step_gene(candidate, directive.gene_id, directive.action)
            if new_value is None:
                continue
            candidate.set_gene(directive.gene_id, new_value)
            applied.append(directive)

        return candidate, applied


def observed_count(attainments: Sequence[SLOAttainment]) -> int:
    return sum(1 for a in attainments if a.observed)
