from __future__ import annotations

import hashlib
from typing import Any, Dict, List

from constitutional_architecture.core.models.genome import (
    APIDesign, ApplicationArchitecture, ArchitectureGenome,
    IntegrationArchitecture, SecurityArchitecture,
)
from constitutional_architecture.core.models.intent import IntentModel, QualityAttribute
from constitutional_architecture.core.models.isr import (
    EdgeType, ISREdge, ISRNode, NodeType, UniversalISR,
)


class ISRTranspiler:
    """Pass 6: Genome-to-ISR Transpiler.

    Pure function: f(IntentModel, ArchitectureGenome) -> UniversalISR.
    Maps abstract genome alleles to concrete ISR graph topology.
    """

    def transpile(self, intent: IntentModel, genome: ArchitectureGenome) -> UniversalISR:
        isr = UniversalISR(
            intent_hash=hashlib.sha256(intent.model_dump_json().encode()).hexdigest()[:12],
            genome_hash=hashlib.sha256(str(genome.serialize()).encode()).hexdigest()[:12],
        )

        self._materialize_domains(isr, intent)
        self._materialize_services(isr, intent, genome)
        self._materialize_messaging(isr, genome)
        self._materialize_security(isr, intent, genome)
        self._materialize_infrastructure(isr, genome)
        self._materialize_frontend(isr, intent, genome)
        self._materialize_operational(isr, intent, genome)

        return isr

    def _materialize_domains(self, isr: UniversalISR, intent: IntentModel) -> None:
        for domain in intent.data_domains:
            domain_id = f"domain_{domain.name.lower()}"
            isr.add_node(ISRNode(
                id=domain_id,
                type=NodeType.DOMAIN,
                semantic_attributes={"boundary_context": domain.name},
            ))

            for entity_name in domain.entities:
                entity_id = f"entity_{entity_name.lower()}"
                isr.add_node(ISRNode(
                    id=entity_id,
                    type=NodeType.DATA_ENTITY,
                    semantic_attributes={"consistency": domain.consistency_requirement},
                ))
                isr.add_edge(ISREdge(source_id=domain_id, target_id=entity_id, type=EdgeType.OWNS))

    def _materialize_services(self, isr: UniversalISR, intent: IntentModel,
                              genome: ArchitectureGenome) -> None:
        app_arch = genome.get_gene("app_arch")
        is_micro = app_arch in (ApplicationArchitecture.MICROSERVICES,
                                ApplicationArchitecture.EVENT_DRIVEN,
                                ApplicationArchitecture.SOA)

        for cap in intent.core_capabilities:
            svc_id = f"svc_{cap.name.lower().replace(' ', '_')}"
            svc_type = NodeType.SERVICE if is_micro else NodeType.COMPONENT

            isr.add_node(ISRNode(
                id=svc_id,
                type=svc_type,
                semantic_attributes={
                    "capability": cap.name,
                    "security_classification": cap.security_classification,
                },
            ))

            api_id = f"api_{cap.name.lower().replace(' ', '_')}"
            api_design = genome.get_gene("api_design")
            protocol = "rest_or_graphql"
            if api_design == APIDesign.GRPC:
                protocol = "grpc"
            elif api_design == APIDesign.EVENT_STREAM:
                protocol = "event_stream"
            elif api_design == APIDesign.GRAPHQL:
                protocol = "graphql"

            isr.add_node(ISRNode(
                id=api_id, type=NodeType.API_ENDPOINT,
                semantic_attributes={"protocol": protocol},
            ))
            isr.add_edge(ISREdge(source_id=svc_id, target_id=api_id, type=EdgeType.EXPOSES))

    def _materialize_messaging(self, isr: UniversalISR, genome: ArchitectureGenome) -> None:
        integration = genome.get_gene("integration_arch")
        if integration in (IntegrationArchitecture.MESSAGE_BUS,
                          IntegrationArchitecture.EVENT_STORE):
            bus_id = "infra_event_bus"
            isr.add_node(ISRNode(
                id=bus_id,
                type=NodeType.INFRA_REQUIREMENT,
                semantic_attributes={"topology": "async_event_bus"},
            ))

    def _materialize_security(self, isr: UniversalISR, intent: IntentModel,
                              genome: ArchitectureGenome) -> None:
        sec_arch = genome.get_gene("security_arch")
        model_val = sec_arch.value if sec_arch else "defense_in_depth"

        policy_id = f"sec_policy_{model_val}"
        isr.add_node(ISRNode(
            id=policy_id,
            type=NodeType.SECURITY_POLICY,
            semantic_attributes={
                "model": model_val,
                "encryption_at_rest": intent.encryption_at_rest,
                "encryption_in_transit": intent.encryption_in_transit,
                "audit_logging": intent.audit_logging_required,
            },
        ))

        for node_id, node in isr.nodes.items():
            if node.type in (NodeType.SERVICE, NodeType.COMPONENT, NodeType.API_ENDPOINT):
                isr.add_edge(ISREdge(source_id=policy_id, target_id=node_id, type=EdgeType.SECURES))

    def _materialize_infrastructure(self, isr: UniversalISR, genome: ArchitectureGenome) -> None:
        dep = genome.get_gene("deployment_topology")
        dep_val = dep.value if dep else "single_region"
        consistency = genome.get_gene("consistency_level")
        fault = genome.get_gene("fault_tolerance")

        infra_id = f"infra_{dep_val}"
        isr.add_node(ISRNode(
            id=infra_id,
            type=NodeType.INFRA_REQUIREMENT,
            semantic_attributes={
                "deployment": dep_val,
                "consistency": consistency,
                "fault_tolerance": fault,
            },
        ))

    def _materialize_frontend(self, isr: UniversalISR, intent: IntentModel,
                              genome: ArchitectureGenome) -> None:
        api_design = genome.get_gene("api_design")
        fe_topology = "spa"
        if api_design == APIDesign.GRAPHQL:
            fe_topology = "graphql_client"
        elif api_design == APIDesign.EVENT_STREAM:
            fe_topology = "reactive_client"

        fe_id = f"fe_{fe_topology}"
        isr.add_node(ISRNode(
            id=fe_id,
            type=NodeType.FRONTEND_VIEW,
            semantic_attributes={
                "topology": fe_topology,
                "target_personas": [p.role for p in intent.personas],
            },
        ))

    def _materialize_operational(self, isr: UniversalISR, intent: IntentModel,
                                 genome: ArchitectureGenome) -> None:
        """Operational ISR Projection: deterministically expands the Operational
        Chromosome into SLODefinition, TelemetryRequirement, and OperationalPolicy
        nodes within the Universal ISR. The Universal ISR remains the sole source
        of truth; no parallel Operational Model exists.

        Constitutional Alignment:
        - "Observability by Design... Operational visibility should exist from the first generated version."
        """
        reliability = genome.get_gene("reliability_target") or 0.99
        depth = genome.get_gene("observability_depth") or 0.5
        posture = genome.get_gene("resilience_posture")
        posture_val = posture.value if posture else "circuit_breaker"
        audit = genome.get_gene("auditability_level")
        audit_val = audit.value if audit else "standard"
        cost = genome.get_gene("cost_monitoring_intensity") or 0.5
        latency_ms = genome.get_gene("latency_tolerance_ms") or 200.0
        performance = intent.quality_priorities.get(QualityAttribute.PERFORMANCE, 0.5)

        op_id = f"op_policy_{posture_val}"
        isr.add_node(ISRNode(
            id=op_id,
            type=NodeType.OPERATIONAL_POLICY,
            semantic_attributes={
                "resilience_posture": posture_val,
                "auditability_level": audit_val,
                "cost_monitoring_intensity": cost,
                "observability_depth": depth,
            },
        ))

        tel_id = "telemetry_core"
        isr.add_node(ISRNode(
            id=tel_id,
            type=NodeType.TELEMETRY_REQUIREMENT,
            semantic_attributes={
                "trace_sampling_percentage": round(depth * 100.0, 2),
                "latency_tolerance_ms": latency_ms,
                "performance_priority": performance,
            },
        ))
        isr.add_edge(ISREdge(source_id=tel_id, target_id=op_id, type=EdgeType.GOVERNED_BY))

        for node_id, node in list(isr.nodes.items()):
            if node.type == NodeType.API_ENDPOINT:
                slo_id = f"slo_{node_id}"
                isr.add_node(ISRNode(
                    id=slo_id,
                    type=NodeType.SLO_DEFINITION,
                    semantic_attributes={
                        "reliability_target": reliability,
                        "error_budget": round(1.0 - reliability, 4),
                        "latency_tolerance_ms": latency_ms,
                    },
                ))
                isr.add_edge(ISREdge(source_id=node_id, target_id=slo_id, type=EdgeType.MONITORS))
                isr.add_edge(ISREdge(source_id=slo_id, target_id=op_id, type=EdgeType.GOVERNED_BY))
