"""
Phase 12 — Operational Intelligence Compiler
Compiles the operational ISR Projection (SLODefinition, TelemetryRequirement,
OperationalPolicy nodes expanded into the Universal ISR by the Pass 6
transpiler) into the complete operational layer: SLO/Alerting Rules, OpenTelemetry
telemetry configuration, Grafana dashboards, and the Semantic Runbook Model.

Because the operational posture flows through the Universal ISR — never a
parallel model — the generated system is operable, diagnosable, and resilient
from generation zero, with no operational drift possible.

Constitutional Alignment:
- "Observability by Design... Operational visibility should exist from the first generated version."
- "The ISR is the sole architectural source of truth."
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from constitutional_architecture.compilers.operational.base import (
    OperationalIntelligenceCompiler as OperationalIntelligenceBase,
)
from constitutional_architecture.core.models.bundle import (
    ArtifactType, CompilationBundle, CompilationManifest,
)
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.intent import IntentModel
from constitutional_architecture.core.models.isr import (
    EdgeType, NodeType, UniversalISR,
)


class OperationalIntelligenceCompiler(OperationalIntelligenceBase):
    def compile(
        self,
        isr: UniversalISR,
        genome: ArchitectureGenome,
        context: Dict[str, Any],
        intent: Optional[IntentModel] = None,
    ) -> CompilationBundle:
        reliability = self._reliability_target(isr, genome)
        posture = self._resilience_posture(isr, genome)
        audit = self._auditability_level(isr, genome)
        depth = self._observability_depth(isr, genome)
        sampling = self._sampling_percentage(isr, genome, depth)

        files: Dict[str, str] = {}

        files["slos/alert_rules.yaml"] = self._generate_alert_rules(isr, genome, reliability, posture, audit)
        files["telemetry/otel-collector.yaml"] = self._generate_otel_config(sampling)
        files["dashboards/system_overview.json"] = self._generate_grafana_dashboard(isr, reliability)
        files["runbooks/incident_response.model.json"] = self._generate_runbook_model(
            reliability, posture, audit,
        )

        manifest = CompilationManifest(
            artifact_type=ArtifactType.CONFIGURATION,
            domain="operational_intelligence",
            files=files,
            metadata={
                "tooling": ["prometheus", "grafana", "opentelemetry"],
                "semantic_runbook_model": "v1",
            },
        )

        exposed = {
            "slo_target": reliability,
            "metrics_endpoint": "/metrics",
            "prometheus_port": 9090,
            "grafana_port": 3001,
        }

        return CompilationBundle(
            compiler_id="operational_intelligence_v1",
            target_technology="prometheus_grafana_otel",
            manifests=[manifest],
            exposed_interfaces=exposed,
        )

    # ─── Operational ISR Projection queries ─────────────────────────────────

    def _slo_nodes(self, isr: UniversalISR) -> List[Any]:
        return sorted(
            (n for n in isr.nodes.values() if n.type == NodeType.SLO_DEFINITION),
            key=lambda n: n.id,
        )

    def _telemetry_nodes(self, isr: UniversalISR) -> List[Any]:
        return sorted(
            (n for n in isr.nodes.values() if n.type == NodeType.TELEMETRY_REQUIREMENT),
            key=lambda n: n.id,
        )

    def _policy_nodes(self, isr: UniversalISR) -> List[Any]:
        return sorted(
            (n for n in isr.nodes.values() if n.type == NodeType.OPERATIONAL_POLICY),
            key=lambda n: n.id,
        )

    def _endpoint_for_slo(self, isr: UniversalISR, slo_id: str) -> Optional[Any]:
        for edge in isr.edges:
            if edge.type == EdgeType.MONITORS and edge.target_id == slo_id:
                return isr.nodes.get(edge.source_id)
        return None

    def _projected(self, nodes: List[Any], key: str) -> Optional[Any]:
        for node in nodes:
            if key in node.semantic_attributes:
                return node.semantic_attributes[key]
        return None

    def _reliability_target(self, isr: UniversalISR, genome: ArchitectureGenome) -> float:
        value = self._projected(self._slo_nodes(isr), "reliability_target")
        if value is None:
            value = genome.reliability_target
        return float(value if value is not None else 0.99)

    def _resilience_posture(self, isr: UniversalISR, genome: ArchitectureGenome) -> str:
        value = self._projected(self._policy_nodes(isr), "resilience_posture")
        if value is None and genome.resilience_posture is not None:
            value = genome.resilience_posture.value
        return str(value if value is not None else "circuit_breaker")

    def _auditability_level(self, isr: UniversalISR, genome: ArchitectureGenome) -> str:
        value = self._projected(self._policy_nodes(isr), "auditability_level")
        if value is None and genome.auditability_level is not None:
            value = genome.auditability_level.value
        return str(value if value is not None else "standard")

    def _observability_depth(self, isr: UniversalISR, genome: ArchitectureGenome) -> float:
        value = self._projected(self._policy_nodes(isr), "observability_depth")
        if value is None:
            value = genome.observability_depth
        return float(value if value is not None else 0.5)

    def _sampling_percentage(
        self,
        isr: UniversalISR,
        genome: ArchitectureGenome,
        depth: float,
    ) -> float:
        value = self._projected(self._telemetry_nodes(isr), "trace_sampling_percentage")
        if value is None:
            value = round(depth * 100.0, 2)
        return float(value)

    def _latency_tolerance_ms(self, isr: UniversalISR, genome: ArchitectureGenome) -> float:
        value = self._projected(self._telemetry_nodes(isr), "latency_tolerance_ms")
        if value is None:
            value = genome.get_gene("latency_tolerance_ms")
        return float(value if value is not None else 200.0)

    # ─── SLO & alerting rules ───────────────────────────────────────────────

    def _generate_alert_rules(
        self,
        isr: UniversalISR,
        genome: ArchitectureGenome,
        reliability: float,
        posture: str,
        audit: str,
    ) -> str:
        error_budget = round(1.0 - reliability, 4)
        latency_s = self._latency_tolerance_ms(isr, genome) / 1000.0

        rules = [
            "  - alert: HighErrorRate",
            f"    expr: sum(rate(http_requests_total{{status=~\"5..\"}}[5m])) / "
            f"sum(rate(http_requests_total[5m])) > {error_budget * 2}",
            "    for: 5m",
            "    labels:",
            "      severity: critical",
            f"      slo_target: \"{reliability}\"",
            '    annotations:',
            '      summary: "Error budget burn rate exceeds 2x threshold"',
        ]

        rules += [
            "  - alert: ErrorBudgetBurn",
            f"    expr: (sum(rate(http_requests_total{{status=~\"5..\"}}[1h])) / "
            f"sum(rate(http_requests_total[1h]))) * 100 > {error_budget * 100} * 14.4",
            "    for: 15m",
            "    labels:",
            "      severity: page",
            f"      slo_target: \"{reliability}\"",
            "    annotations:",
            "      summary: \"Error budget burn rate exceeds 14.4x over 1h\"",
        ]

        for slo in self._slo_nodes(isr):
            endpoint = self._endpoint_for_slo(isr, slo.id)
            route = self._route(endpoint)
            rules += [
                f"  - alert: HighLatency-{self._sanitize(route)}",
                f"    expr: histogram_quantile(0.95, sum by (le) (rate("
                f"http_request_duration_seconds_bucket{{route=\"{route}\"}}[5m]))) "
                f"> {latency_s:.3f}",
                "    for: 10m",
                "    labels:",
                "      severity: warning",
                "    annotations:",
                f"      summary: \"p95 latency for {route} exceeds tolerance\"",
            ]

        if posture == "circuit_breaker":
            rules += [
                "  - alert: CircuitBreakerOpen",
                "    expr: circuit_breaker_open == 1",
                "    for: 1m",
                "    labels:",
                "      severity: critical",
                "    annotations:",
                "      summary: \"Circuit breaker open; downstream dependency degraded\"",
            ]

        if audit == "strict_compliance":
            rules += [
                "  - alert: AuditLogFailures",
                "    expr: rate(audit_log_writes_total{result=\"error\"}[5m]) > 0",
                "    for: 5m",
                "    labels:",
                "      severity: critical",
                "    annotations:",
                "      summary: \"Audit log writes failing; compliance record integrity at risk\"",
            ]

        body = "\n".join(rules)
        return f"groups:\n- name: slo_alerts\n  rules:\n{body}\n"

    # ─── Telemetry configuration ────────────────────────────────────────────

    def _generate_otel_config(self, sampling_percentage: float) -> str:
        return f"""receivers:
  otlp:
    protocols:
      grpc:
exporters:
  otlp:
    endpoint: "otel-collector:4317"
processors:
  probabilistic_sampler:
    sampling_percentage: {sampling_percentage:.1f}
service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [probabilistic_sampler]
      exporters: [otlp]
"""

    # ─── Grafana dashboard ──────────────────────────────────────────────────

    def _generate_grafana_dashboard(self, isr: UniversalISR, reliability: float) -> str:
        panels: List[Dict[str, Any]] = []
        panel_id = 1

        for slo in self._slo_nodes(isr):
            endpoint = self._endpoint_for_slo(isr, slo.id)
            route = self._route(endpoint)
            panels.append(self._panel(
                panel_id, "Request Rate - " + route,
                f"sum(rate(http_requests_total{{route=\"{route}\"}}[5m]))",
            ))
            panel_id += 1
            panels.append(self._panel(
                panel_id, "Error Rate - " + route,
                f"sum(rate(http_requests_total{{route=\"{route}\",status=~\"5..\"}}[5m]))",
            ))
            panel_id += 1
            panels.append(self._panel(
                panel_id, "p95 Latency - " + route,
                f"histogram_quantile(0.95, sum by (le) (rate("
                f"http_request_duration_seconds_bucket{{route=\"{route}\"}}[5m])))",
            ))
            panel_id += 1
            panels.append(self._panel(
                panel_id, "SLO Burn - " + route,
                f"sum(rate(http_requests_total{{route=\"{route}\",status=~\"5..\"}}[5m])) / "
                f"sum(rate(http_requests_total{{route=\"{route}\"}}[5m]))",
            ))
            panel_id += 1

        dashboard = {
            "title": "System Overview",
            "uid": "system-overview",
            "slo_target": reliability,
            "panels": panels,
            "time": {"from": "now-6h", "to": "now"},
        }
        return json.dumps(dashboard, indent=2, sort_keys=True)

    def _panel(self, panel_id: int, title: str, expr: str) -> Dict[str, Any]:
        return {
            "id": panel_id,
            "type": "timeseries",
            "title": title,
            "targets": [{"expr": expr, "legendFormat": "{{route}}"}],
        }

    # ─── Semantic Runbook Model ─────────────────────────────────────────────

    def _generate_runbook_model(
        self,
        reliability: float,
        posture: str,
        audit: str,
    ) -> str:
        runbook: Dict[str, Any] = {
            "title": "System Incident Response",
            "reliability_target": reliability,
            "resilience_posture": posture,
            "auditability_level": audit,
            "steps": [
                {"action": "verify_slo_breach", "tool": "prometheus"},
                {"action": "check_distributed_traces", "tool": "jaeger/tempo"},
                {"action": "inspect_structured_logs", "tool": "loki/elk"},
            ],
        }

        if posture == "circuit_breaker":
            runbook["steps"].append(
                {"action": "check_circuit_breaker_states", "tool": "envoy/hystrix"},
            )

        if audit == "strict_compliance":
            runbook["steps"].append(
                {"action": "verify_audit_log_integrity", "tool": "immutable_audit_store"},
            )

        return json.dumps(runbook, indent=2)

    # ─── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _route(node: Optional[Any]) -> str:
        if node is None:
            return "unknown"
        return str(node.semantic_attributes.get("path") or node.id)

    @staticmethod
    def _sanitize(value: str) -> str:
        import re
        return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_") or "endpoint"
