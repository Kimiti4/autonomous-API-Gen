"""Materialize a genome candidate into an ISRGraph (ADR-011 §Genome→ISR bridge)."""

from __future__ import annotations

from typing import Mapping

from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from evolution.core.genome import ChromosomeFamily, Genome


class ReferenceGenomeMaterializer:
    def materialize(self, genome: Genome) -> ISRGraph:
        nodes: dict[str, Node] = {}
        edges: dict[str, Edge] = {}

        # --- architecture: domain + service nodes ---
        arch = genome.chromosomes.get(ChromosomeFamily.ARCHITECTURE.value)
        domain_names: list[str] = []
        if arch:
            domain_names = sorted(arch.genes.keys())
        for d in domain_names:
            nodes[f"domain:{d}"] = Node(
                id=f"domain:{d}", type=NodeType.DOMAIN, properties={"label": d}
            )
            style = arch.genes[d].value if arch else "bounded-context"
            source_nodes = genome.source_graph.get("nodes", {}) if isinstance(genome.source_graph, Mapping) else {}
            domain_requirement = next(
                (
                    value for value in source_nodes.values()
                    if isinstance(value, Mapping)
                    and value.get("type") == NodeType.REQUIREMENT_REF.value
                    and value.get("properties", {}).get("requirement_id") == d
                ),
                None,
            )
            source_statement = (
                domain_requirement.get("properties", {}).get("semantic_content")
                if isinstance(domain_requirement, Mapping)
                and isinstance(domain_requirement.get("properties"), Mapping)
                else None
            )
            service_properties = {"style": style}
            if isinstance(source_statement, str) and source_statement.strip():
                service_properties["responsibility"] = source_statement
                service_properties["source_requirement_ref"] = f"requirement_ref:{d}"
            nodes[f"service:{d}"] = Node(
                id=f"service:{d}",
                type=NodeType.SERVICE,
                properties=service_properties,
            )

        # --- persistence: data_model + PERSISTS edge per service ---
        pers = genome.chromosomes.get(ChromosomeFamily.PERSISTENCE.value)
        if pers:
            for d in domain_names:
                dm_id = f"dm:{d}"
                nodes[dm_id] = Node(
                    id=dm_id, type=NodeType.DATA_MODEL, properties={"storage": pers.genes.get("baseline", pers.genes.get("baseline")).value}
                )
                edges[f"persist-{d}"] = Edge(
                    id=f"persist-{d}",
                    type=EdgeType.PERSISTS,
                    source_id=f"service:{d}",
                    target_id=dm_id,
                )

        # --- security: policy + SECURED_BY edge per service ---
        sec = genome.chromosomes.get(ChromosomeFamily.SECURITY.value)
        if sec:
            sec_id = "sec:policy"
            nodes[sec_id] = Node(
                id=sec_id,
                type=NodeType.SECURITY_POLICY,
                properties={"authn": sec.genes.get("baseline", sec.genes["baseline"]).value},
            )
            for d in domain_names:
                edges[f"sec-{d}"] = Edge(
                    id=f"sec-{d}",
                    type=EdgeType.SECURED_BY,
                    source_id=f"service:{d}",
                    target_id=sec_id,
                )

        # --- messaging: events + PUBLISHES / CONSUMED_BY edges ---
        msg = genome.chromosomes.get(ChromosomeFamily.MESSAGING.value)
        if msg and len(domain_names) >= 2:
            style_gene = msg.genes.get("style")
            style = style_gene.value if style_gene else "event-driven"
            if style == "event-driven":
                nodes["event:domain"] = Node(
                    id="event:domain", type=NodeType.EVENT, properties={}
                )
                edges["pub"] = Edge(
                    id="pub",
                    type=EdgeType.PUBLISHES,
                    source_id=f"service:{domain_names[0]}",
                    target_id="event:domain",
                )
                edges["con"] = Edge(
                    id="con",
                    type=EdgeType.CONSUMED_BY,
                    source_id="event:domain",
                    target_id=f"service:{domain_names[-1]}",
                )

        # --- depends_on: baseline cross-service dependency for >=3 services ---
        if len(domain_names) >= 3:
            src, tgt = domain_names[0], domain_names[2]
            edges[f"dep-svc-{src}-{tgt}"] = Edge(
                id=f"dep-svc-{src}-{tgt}",
                type=EdgeType.DEPENDS_ON,
                source_id=f"service:{src}",
                target_id=f"service:{tgt}",
            )

        # Preserve the authoritative semantic substrate through materialization.
        # Evolution may add derived nodes, but it must not erase requirement refs,
        # source semantics, or typed relationships merely because they are not genes.
        source_graph = genome.source_graph
        if source_graph:
            if not isinstance(source_graph, Mapping):
                raise ValueError("genome source_graph must be a mapping")
            source_nodes = source_graph.get("nodes")
            source_edges = source_graph.get("edges")
            if not isinstance(source_nodes, Mapping) or not isinstance(source_edges, Mapping):
                raise ValueError("genome source_graph requires explicit nodes and edges")
            preserved_nodes = {
                str(key): Node.model_validate(value)
                for key, value in source_nodes.items()
            }
            preserved_edges = {
                str(key): Edge.model_validate(value)
                for key, value in source_edges.items()
            }
            # The source graph is authoritative on collisions. Derived nodes
            # fill gaps but cannot silently overwrite source semantics.
            for key, value in nodes.items():
                preserved_nodes.setdefault(key, value)
            for key, value in edges.items():
                preserved_edges.setdefault(key, value)
            nodes, edges = preserved_nodes, preserved_edges

            # Requirement refinements are authoritative source relationships.
            # When a functional requirement refines a domain requirement, bind
            # its capability to the service generated for that domain. No
            # lexical name matching is used.
            for source_edge in list(preserved_edges.values()):
                if source_edge.type is not EdgeType.REQUIREMENT_REFINES:
                    continue
                source_ref = preserved_nodes.get(source_edge.source_id)
                target_ref = preserved_nodes.get(source_edge.target_id)
                if source_ref is None or target_ref is None:
                    continue
                source_props = source_ref.properties
                target_props = target_ref.properties
                capability_id = f"capability:{source_props.get('requirement_id', '')}"
                service_id = f"service:{target_props.get('requirement_id', '')}"
                if (
                    source_props.get("requirement_kind") == "functional"
                    and target_props.get("requirement_kind") == "domain_concept"
                    and capability_id in nodes
                    and service_id in nodes
                ):
                    edge_id = f"implemented-by:{source_props.get('requirement_id')}"
                    edges.setdefault(
                        edge_id,
                        Edge(
                            id=edge_id,
                            type=EdgeType.IMPLEMENTED_BY,
                            source_id=capability_id,
                            target_id=service_id,
                            properties={
                                "derived_from_requirement_edge": source_edge.id,
                                "source_requirement_ref": source_edge.source_id,
                                "target_requirement_ref": source_edge.target_id,
                            },
                        ),
                    )

        return ISRGraph(nodes=nodes, edges=edges)
