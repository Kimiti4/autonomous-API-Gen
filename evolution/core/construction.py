"""Genome construction from ISR — deterministic reference implementation."""

from __future__ import annotations

from isr.core.graph import NodeType
from isr.core.revision import ISRRevision
from evolution.core.genome import Chromosome, ChromosomeFamily, Gene, Genome


class ReferenceGenomeConstructor:
    """Deterministic: same ISR revision -> same genome."""

    def construct(self, isr: ISRRevision) -> Genome:
        domains = [
            n.id
            for n in sorted(isr.graph.nodes.values(), key=lambda x: x.id)
            if n.type == NodeType.DOMAIN
        ]

        # Strip "domain:" prefix to produce clean gene IDs.
        domain_names = [d.split(":", 1)[1] if ":" in d else d for d in domains]

        chroms: dict[str, Chromosome] = {}

        chroms[ChromosomeFamily.ARCHITECTURE.value] = Chromosome(
            family=ChromosomeFamily.ARCHITECTURE,
            genes={
                name: Gene(gene_id=name, decision="decomposition", value="bounded-context")
                for name in domain_names
            },
        )

        chroms[ChromosomeFamily.PERSISTENCE.value] = Chromosome(
            family=ChromosomeFamily.PERSISTENCE,
            genes={"baseline": Gene(gene_id="baseline", decision="storage", value="json")},
        )

        chroms[ChromosomeFamily.SECURITY.value] = Chromosome(
            family=ChromosomeFamily.SECURITY,
            genes={"baseline": Gene(gene_id="baseline", decision="authn", value="token")},
        )

        if len(domains) >= 2:
            chroms[ChromosomeFamily.MESSAGING.value] = Chromosome(
                family=ChromosomeFamily.MESSAGING,
                genes={"style": Gene(gene_id="style", decision="protocol", value="event-driven")},
            )

        return Genome(system_id=isr.system_id, chromosomes=chroms)
