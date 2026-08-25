"""Materialize a genome candidate into an ISRGraph (ADR-011 §Genome→ISR bridge)."""

from __future__ import annotations

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
            nodes[f"service:{d}"] = Node(
                id=f"service:{d}",
                type=NodeType.SERVICE,
                properties={"style": style},
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

        return ISRGraph(nodes=nodes, edges=edges)
