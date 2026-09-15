Yes — proceeding with the **Evolution Genome view**.

This view gives the Observatory a read-only surface for inspecting the architectural genome model described in the Constitution:

```text
genome identity
candidate linkage
chromosome families
genes
mutations
crossovers
selection outcomes
fitness linkage
Pareto state
unknowns
contradictions
```

This view does **not** mutate genomes.

It does **not** select architectures.

It does **not** authorize evolution.

It only renders recorded genome evidence.

---

# 1. Constitutional alignment

The Constitution states:

```text
The genome represents architectural decisions rather than implementation details.
Genes should evolve independently whenever possible.
Evolution stages include genome construction, mutation, crossover, selection,
fitness evaluation, Pareto optimisation, architecture refinement, and
candidate generation.
```

Therefore the Genome view must expose:

```text
Architecture
Persistence
Infrastructure
Security
Messaging
Observability
AI
Testing
Deployment
Frontend
Backend
Governance
Documentation
Performance
Reliability
```

as chromosome families, while still allowing repository-specific chromosome names.

---

# 2. What this adds

This step adds:

```text
backend genome projection
backend genome overview endpoint
backend genome detail endpoint
frontend genome list page
frontend genome detail page
genome event contract
```

New backend endpoints:

```text
GET /observatory/genomes
GET /observatory/genomes/{genome_id}
```

New frontend routes:

```text
/genomes
/genomes/{genome_id}
```

---

# 3. Backend: genome projection

Create:

**`observatory/backend/projections_genomes.py`**

```python
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .domain import EpistemicStatus, Event
from .projections import (
    collect_evidence_refs,
    collect_payload_list,
    count_epistemic,
    latest_event,
    payload_get,
    sort_asc,
)

KNOWN_CHROMOSOME_FAMILIES = [
    "Architecture",
    "Persistence",
    "Infrastructure",
    "Security",
    "Messaging",
    "Observability",
    "AI",
    "Testing",
    "Deployment",
    "Frontend",
    "Backend",
    "Governance",
    "Documentation",
    "Performance",
    "Reliability",
]

KNOWN_CHROMOSOME_ORDER = {
    name.lower(): index
    for index, name in enumerate(KNOWN_CHROMOSOME_FAMILIES)
}

GENOME_PROPOSAL_TYPES = {
    "genome_proposed",
    "genome_defined",
    "genome_created",
}

MUTATION_TYPES = {
    "gene_mutated",
    "mutation_recorded",
    "genome_mutated",
}

CROSSOVER_TYPES = {
    "gene_crossover",
    "crossover_recorded",
    "genome_crossover",
}

SELECTION_TYPES = {
    "selection_observed",
    "selection_recorded",
    "candidate_selected",
    "candidate_rejected",
}

REJECTION_TYPES = {
    "genome_rejected",
    "candidate_rejected",
    "selection_rejected",
}

PARETO_TYPES = {
    "pareto_observed",
    "pareto_updated",
}

REJECTED_OUTCOMES = {
    "rejected",
    "reject",
    "denied",
    "blocked",
}


def _merge_unique(*lists: List[str]) -> List[str]:
    merged = set()

    for values in lists:
        for value in values:
            if value is None:
                continue

            merged.add(str(value))

    return sorted(merged)


def _first_str(
    payload: Dict[str, Any],
    keys: tuple[str, ...],
    default: Optional[str] = None,
) -> Optional[str]:
    for key in keys:
        value = payload_get(payload, key)

        if value is not None:
            return str(value)

    return default


def _latest_payload_value(
    events: List[Event],
    key: str,
    default: Any = None,
) -> Any:
    for event in reversed(events):
        value = payload_get(event.payload, key)

        if value is not None:
            return value

    return default


def extract_genome_id(event: Event) -> Optional[str]:
    for key in (
        "genome_id",
        "genome_identity",
        "candidate_genome_id",
    ):
        value = payload_get(event.payload, key)

        if value is not None:
            return str(value)

    if event.type.startswith(
        (
            "genome_",
            "chromosome_",
            "mutation_",
            "crossover_",
        )
    ):
        return str(event.subject_id)

    if event.type.startswith("gene_"):
        genome_id = payload_get(event.payload, "genome_id")

        if genome_id is not None:
            return str(genome_id)

    subject = str(event.subject_id)

    if subject.startswith(("GEN-", "GENOME-", "CAND-")):
        return subject

    return None


def extract_gene_id(event: Event) -> Optional[str]:
    for key in (
        "gene_id",
        "gene_name",
        "gene",
    ):
        value = payload_get(event.payload, key)

        if value is not None:
            return str(value)

    if event.type.startswith("gene_"):
        genome_id = payload_get(event.payload, "genome_id")

        if genome_id is not None and str(event.subject_id) != str(genome_id):
            return str(event.subject_id)

    subject = str(event.subject_id)

    if subject.startswith("GENE-"):
        return subject

    return None


def extract_chromosome(event: Event) -> Optional[str]:
    for key in (
        "chromosome",
        "chromosome_family",
        "family",
        "domain",
    ):
        value = payload_get(event.payload, key)

        if value is not None:
            return str(value)

    return None


def chromosome_sort_key(name: str) -> tuple[int, str]:
    normalized = name.strip().lower()

    return (
        KNOWN_CHROMOSOME_ORDER.get(normalized, len(KNOWN_CHROMOSOME_FAMILIES)),
        normalized,
    )


def derive_genome_status(events: List[Event]) -> str:
    explicit_status = _latest_payload_value(events, "status")

    if explicit_status is not None:
        return str(explicit_status)

    for event in reversed(events):
        if event.type in REJECTION_TYPES:
            return "rejected"

        if event.type in SELECTION_TYPES:
            outcome = payload_get(
                event.payload,
                "outcome",
                payload_get(event.payload, "decision"),
            )

            if outcome is not None and str(outcome).strip().lower() in REJECTED_OUTCOMES:
                return "rejected"

            return "selected"

        if event.type in CROSSOVER_TYPES:
            return "crossed_over"

        if event.type in MUTATION_TYPES:
            return "mutated"

        if event.type in GENOME_PROPOSAL_TYPES:
            return "proposed"

    return "observed"


def derive_pareto_state(events: List[Event]) -> str:
    explicit_state = _latest_payload_value(
        events,
        "pareto_state",
        _latest_payload_value(events, "pareto_status"),
    )

    if explicit_state is not None:
        return str(explicit_state)

    for event in reversed(events):
        if event.type in PARETO_TYPES:
            return str(
                payload_get(event.payload, "pareto_status", "observed")
            )

    return "unknown"


def build_genome_unknowns(events: List[Event]) -> List[Dict[str, Any]]:
    unknowns: List[Dict[str, Any]] = []

    for event in events:
        if (
            event.epistemic_status == EpistemicStatus.UNKNOWN
            or event.type.startswith("unknown_")
        ):
            unknowns.append(
                {
                    "unknown_id": str(
                        payload_get(event.payload, "unknown_id", event.id)
                    ),
                    "question": str(
                        _first_str(
                            event.payload,
                            ("question", "unknown", "statement", "summary"),
                            default="Unknown genome condition",
                        )
                    ),
                    "timestamp": event.timestamp,
                }
            )

    return unknowns


def build_genome_contradictions(events: List[Event]) -> List[Dict[str, Any]]:
    contradictions: List[Dict[str, Any]] = []

    for event in events:
        if (
            event.epistemic_status == EpistemicStatus.CONTRADICTION
            or event.type.startswith("contradiction_")
        ):
            contradictions.append(
                {
                    "contradiction_id": str(
                        payload_get(
                            event.payload,
                            "contradiction_id",
                            event.id,
                        )
                    ),
                    "statement": str(
                        _first_str(
                            event.payload,
                            ("statement", "summary"),
                            default="Genome evidence contradiction",
                        )
                    ),
                    "timestamp": event.timestamp,
                }
            )

    return contradictions


def build_timeline(events: List[Event]) -> List[Dict[str, Any]]:
    return [
        {
            "event_id": event.id,
            "timestamp": event.timestamp,
            "category": event.category.value,
            "type": event.type,
            "subject_id": event.subject_id,
            "epistemic_status": event.epistemic_status.value,
            "severity": event.severity.value,
            "summary": str(
                payload_get(
                    event.payload,
                    "summary",
                    f"{event.type}: {event.subject_id}",
                )
            ),
        }
        for event in reversed(events)
    ]


def build_genome_genes(events: List[Event]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Event]] = {}

    for event in events:
        gene_id = extract_gene_id(event)

        if gene_id is None:
            continue

        grouped.setdefault(gene_id, []).append(event)

    genes: List[Dict[str, Any]] = []

    for gene_id, gene_events in grouped.items():
        sorted_events = sort_asc(gene_events)
        latest = latest_event(sorted_events)

        if latest is None:
            continue

        chromosome = None

        for event in reversed(sorted_events):
            extracted = extract_chromosome(event)

            if extracted is not None:
                chromosome = extracted
                break

        value = _latest_payload_value(
            sorted_events,
            "value",
            _latest_payload_value(
                sorted_events,
                "allele",
                _latest_payload_value(
                    sorted_events,
                    "new_value",
                    _latest_payload_value(sorted_events, "current_value"),
                ),
            ),
        )

        previous_value = _latest_payload_value(
            sorted_events,
            "previous_value",
            _latest_payload_value(sorted_events, "from_value"),
        )

        mutation_count = sum(
            1 for event in sorted_events if event.type in MUTATION_TYPES
        )

        crossover_count = sum(
            1 for event in sorted_events if event.type in CROSSOVER_TYPES
        )

        explicit_status = _latest_payload_value(sorted_events, "status")

        if explicit_status is not None:
            status = str(explicit_status)
        elif crossover_count > 0:
            status = "crossed_over"
        elif mutation_count > 0:
            status = "mutated"
        elif any(event.type.startswith("gene_defined") for event in sorted_events):
            status = "defined"
        else:
            status = "observed"

        genes.append(
            {
                "gene_id": gene_id,
                "chromosome": chromosome or "Unknown",
                "value": value,
                "previous_value": previous_value,
                "status": status,
                "mutation_count": mutation_count,
                "crossover_count": crossover_count,
                "updated_at": latest.timestamp,
            }
        )

    return sorted(genes, key=lambda item: (item["chromosome"], item["gene_id"]))


def build_genome_chromosomes(
    events: List[Event],
    genes: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    if genes is None:
        genes = build_genome_genes(events)

    chromosome_names = set()

    for gene in genes:
        chromosome_names.add(gene["chromosome"])

    for event in events:
        chromosome = extract_chromosome(event)

        if chromosome is not None:
            chromosome_names.add(chromosome)

    chromosomes: Dict[str, Dict[str, Any]] = {}

    for name in chromosome_names:
        chromosomes[name] = {
            "name": name,
            "genes": [],
            "gene_count": 0,
            "mutation_count": 0,
            "crossover_count": 0,
            "status": "observed",
        }

    for gene in genes:
        chromosomes[gene["chromosome"]]["genes"].append(gene)

    for event in events:
        chromosome = extract_chromosome(event)

        if chromosome is None or chromosome not in chromosomes:
            continue

        if event.type in MUTATION_TYPES:
            chromosomes[chromosome]["mutation_count"] += 1

        if event.type in CROSSOVER_TYPES:
            chromosomes[chromosome]["crossover_count"] += 1

    result: List[Dict[str, Any]] = []

    for chromosome in chromosomes.values():
        chromosome["genes"] = sorted(
            chromosome["genes"],
            key=lambda item: item["gene_id"],
        )
        chromosome["gene_count"] = len(chromosome["genes"])
        result.append(chromosome)

    return sorted(result, key=lambda item: chromosome_sort_key(item["name"]))


def build_genome_mutations(events: List[Event]) -> List[Dict[str, Any]]:
    mutations: List[Dict[str, Any]] = []

    for event in events:
        if event.type not in MUTATION_TYPES and not event.type.startswith("mutation_"):
            continue

        mutations.append(
            {
                "mutation_id": str(
                    payload_get(event.payload, "mutation_id", event.id)
                ),
                "timestamp": event.timestamp,
                "chromosome": extract_chromosome(event),
                "gene_id": extract_gene_id(event),
                "previous_value": payload_get(
                    event.payload,
                    "previous_value",
                    payload_get(event.payload, "from_value"),
                ),
                "new_value": payload_get(
                    event.payload,
                    "new_value",
                    payload_get(
                        event.payload,
                        "to_value",
                        payload_get(event.payload, "value"),
                    ),
                ),
                "reason": payload_get(event.payload, "reason"),
                "evidence_refs": list(event.evidence_refs),
            }
        )

    return mutations


def build_genome_crossovers(events: List[Event]) -> List[Dict[str, Any]]:
    crossovers: List[Dict[str, Any]] = []

    for event in events:
        if (
            event.type not in CROSSOVER_TYPES
            and not event.type.startswith("crossover_")
        ):
            continue

        parent_genomes = payload_get(
            event.payload,
            "parent_genome_ids",
            payload_get(event.payload, "source_genome_ids", []),
        )

        if not isinstance(parent_genomes, list):
            parent_genomes = [parent_genomes]

        crossovers.append(
            {
                "crossover_id": str(
                    payload_get(event.payload, "crossover_id", event.id)
                ),
                "timestamp": event.timestamp,
                "chromosome": extract_chromosome(event),
                "gene_id": extract_gene_id(event),
                "parent_genome_ids": [
                    str(parent) for parent in parent_genomes if parent is not None
                ],
                "evidence_refs": list(event.evidence_refs),
            }
        )

    return crossovers


def build_genome_selections(events: List[Event]) -> List[Dict[str, Any]]:
    selections: List[Dict[str, Any]] = []

    for event in events:
        if (
            event.type not in SELECTION_TYPES
            and not event.type.startswith("selection_")
        ):
            continue

        outcome = payload_get(
            event.payload,
            "outcome",
            payload_get(event.payload, "decision"),
        )

        selections.append(
            {
                "selection_id": str(
                    payload_get(event.payload, "selection_id", event.id)
                ),
                "timestamp": event.timestamp,
                "candidate_id": payload_get(
                    event.payload,
                    "candidate_id",
                    event.subject_id,
                ),
                "outcome": outcome,
                "reason": payload_get(event.payload, "reason"),
                "evidence_refs": list(event.evidence_refs),
            }
        )

    return selections


def build_fitness_links(events: List[Event]) -> List[str]:
    fitness_ids = set()

    for event in events:
        fitness_id = payload_get(event.payload, "fitness_id")

        if fitness_id is not None:
            fitness_ids.add(str(fitness_id))

    return sorted(fitness_ids)


def build_genomes_overview(events: List[Event]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Event]] = {}

    for event in events:
        genome_id = extract_genome_id(event)

        if genome_id is None:
            continue

        grouped.setdefault(genome_id, []).append(event)

    summaries: List[Dict[str, Any]] = []

    for genome_id, genome_events in grouped.items():
        sorted_events = sort_asc(genome_events)
        latest = latest_event(sorted_events)

        if latest is None:
            continue

        candidate_id = _latest_payload_value(sorted_events, "candidate_id")
        generation = _latest_payload_value(sorted_events, "generation")
        objective = _first_str(
            latest.payload,
            ("objective", "summary", "title"),
            default=genome_id,
        )

        genes = build_genome_genes(sorted_events)

        chromosome_names = {gene["chromosome"] for gene in genes}

        for event in sorted_events:
            chromosome = extract_chromosome(event)

            if chromosome is not None:
                chromosome_names.add(chromosome)

        epistemic_state = count_epistemic(sorted_events)

        summaries.append(
            {
                "genome_id": genome_id,
                "status": derive_genome_status(sorted_events),
                "candidate_id": candidate_id,
                "generation": generation,
                "objective": objective,
                "pareto_state": derive_pareto_state(sorted_events),
                "chromosome_count": len(chromosome_names),
                "gene_count": len(genes),
                "mutation_count": sum(
                    1 for event in sorted_events if event.type in MUTATION_TYPES
                ),
                "crossover_count": sum(
                    1 for event in sorted_events if event.type in CROSSOVER_TYPES
                ),
                "selection_count": sum(
                    1 for event in sorted_events if event.type in SELECTION_TYPES
                ),
                "fitness_count": len(build_fitness_links(sorted_events)),
                "evidence_count": len(collect_evidence_refs(sorted_events)),
                "unknown_count": epistemic_state["unknown"],
                "contradiction_count": epistemic_state["contradiction"],
                "updated_at": latest.timestamp,
            }
        )

    return sorted(summaries, key=lambda item: item["genome_id"])


def build_genome_detail(
    genome_id: str,
    events: List[Event],
) -> Optional[Dict[str, Any]]:
    relevant = [
        event
        for event in events
        if extract_genome_id(event) == genome_id
        or event.subject_id == genome_id
    ]

    if not relevant:
        return None

    relevant_sorted = sort_asc(relevant)
    latest = latest_event(relevant_sorted)

    if latest is None:
        return None

    candidate_id = _latest_payload_value(relevant_sorted, "candidate_id")
    generation = _latest_payload_value(relevant_sorted, "generation")
    objective = _first_str(
        latest.payload,
        ("objective", "summary", "title"),
        default=genome_id,
    )

    description = _latest_payload_value(relevant_sorted, "description")
    environment = _latest_payload_value(relevant_sorted, "environment")

    requirement_links = _merge_unique(
        collect_payload_list(relevant_sorted, "requirement_id"),
        collect_payload_list(relevant_sorted, "objective_id"),
    )

    genes = build_genome_genes(relevant_sorted)
    chromosomes = build_genome_chromosomes(relevant_sorted, genes)
    mutations = build_genome_mutations(relevant_sorted)
    crossovers = build_genome_crossovers(relevant_sorted)
    selections = build_genome_selections(relevant_sorted)
    fitness_links = build_fitness_links(relevant_sorted)

    evidence_refs = _merge_unique(
        collect_evidence_refs(relevant_sorted),
        collect_payload_list(relevant_sorted, "evidence_id"),
        collect_payload_list(relevant_sorted, "evidence_refs"),
    )

    return {
        "genome_id": genome_id,
        "status": derive_genome_status(relevant_sorted),
        "candidate_id": candidate_id,
        "generation": generation,
        "objective": objective,
        "description": description,
        "environment": environment,
        "requirement_links": requirement_links,
        "pareto_state": derive_pareto_state(relevant_sorted),
        "epistemic_state": count_epistemic(relevant_sorted),
        "chromosomes": chromosomes,
        "genes": genes,
        "mutations": mutations,
        "crossovers": crossovers,
        "selections": selections,
        "fitness_links": fitness_links,
        "evidence_refs": evidence_refs,
        "unknowns": build_genome_unknowns(relevant_sorted),
        "contradictions": build_genome_contradictions(relevant_sorted),
        "timeline": build_timeline(relevant_sorted),
        "provenance": latest.provenance,
        "sources": sorted({event.source for event in relevant_sorted}),
        "first_observed_at": relevant_sorted[0].timestamp,
        "updated_at": latest.timestamp,
    }
```

---

# 4. Backend: gateway additions

Add to:

**`observatory/backend/gateway.py`**

Import:

```python
from .projections_genomes import (
    build_genome_detail,
    build_genomes_overview,
)
```

Add methods inside `ObservatoryGateway`:

```python
    async def genomes_overview(self) -> List[Dict[str, Any]]:
        events = await asyncio.to_thread(
            self.store.events_by_categories,
            ALL_EVENT_CATEGORIES,
            20_000,
        )

        return build_genomes_overview(events)

    async def genome_detail(self, genome_id: str) -> Dict[str, Any]:
        events = await asyncio.to_thread(
            self.store.events_by_categories,
            ALL_EVENT_CATEGORIES,
            20_000,
        )

        detail = build_genome_detail(genome_id, events)

        if detail is None:
            raise NotFoundError(f"genome {genome_id} not found")

        return detail
```

---

# 5. Backend: API routes

Add to:

**`observatory/backend/api/routes.py`**

```python
@router.get("/genomes")
async def genomes_overview(
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.genomes_overview()


@router.get("/genomes/{genome_id}")
async def genome_detail(
    genome_id: str,
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.genome_detail(genome_id)
```

---

# 6. Frontend: type additions

Append to:

**`observatory/frontend/lib/types.ts`**

```typescript
export interface GenomeSummary {
  genome_id: string;
  status: string;
  candidate_id: string | null;
  generation: string | number | null;
  objective: string;
  pareto_state: string;
  chromosome_count: number;
  gene_count: number;
  mutation_count: number;
  crossover_count: number;
  selection_count: number;
  fitness_count: number;
  evidence_count: number;
  unknown_count: number;
  contradiction_count: number;
  updated_at: string | null;
}

export interface GenomeGene {
  gene_id: string;
  chromosome: string;
  value: unknown;
  previous_value: unknown;
  status: string;
  mutation_count: number;
  crossover_count: number;
  updated_at: string | null;
}

export interface GenomeChromosome {
  name: string;
  genes: GenomeGene[];
  gene_count: number;
  mutation_count: number;
  crossover_count: number;
  status: string;
}

export interface GenomeMutation {
  mutation_id: string;
  timestamp: string;
  chromosome: string | null;
  gene_id: string | null;
  previous_value: unknown;
  new_value: unknown;
  reason: string | null;
  evidence_refs: string[];
}

export interface GenomeCrossover {
  crossover_id: string;
  timestamp: string;
  chromosome: string | null;
  gene_id: string | null;
  parent_genome_ids: string[];
  evidence_refs: string[];
}

export interface GenomeSelection {
  selection_id: string;
  timestamp: string;
  candidate_id: string | null;
  outcome: unknown;
  reason: string | null;
  evidence_refs: string[];
}

export interface GenomeUnknown {
  unknown_id: string;
  question: string;
  timestamp: string;
}

export interface GenomeContradiction {
  contradiction_id: string;
  statement: string;
  timestamp: string;
}

export interface GenomeDetail {
  genome_id: string;
  status: string;
  candidate_id: string | null;
  generation: string | number | null;
  objective: string;
  description: string | null;
  environment: string | null;
  requirement_links: string[];
  pareto_state: string;
  epistemic_state: EpistemicCounts;
  chromosomes: GenomeChromosome[];
  genes: GenomeGene[];
  mutations: GenomeMutation[];
  crossovers: GenomeCrossover[];
  selections: GenomeSelection[];
  fitness_links: string[];
  evidence_refs: string[];
  unknowns: GenomeUnknown[];
  contradictions: GenomeContradiction[];
  timeline: TimelineEntry[];
  provenance: Record<string, unknown>;
  sources: string[];
  first_observed_at: string | null;
  updated_at: string | null;
}
```

---

# 7. Frontend: API client additions

Add to the `api` object in:

**`observatory/frontend/lib/api.ts`**

```typescript
  genomes(): Promise<GenomeSummary[]> {
    return request<GenomeSummary[]>("/observatory/genomes");
  },

  genomeDetail(genomeId: string): Promise<GenomeDetail> {
    return request<GenomeDetail>(
      `/observatory/genomes/${encodeURIComponent(genomeId)}`
    );
  }
```

Update the type import in `api.ts`:

```typescript
import type {
  DashboardState,
  EvidenceRecord,
  EvolutionState,
  ExperimentDetail,
  ExperimentSummary,
  FitnessDetail,
  FitnessSummary,
  GenomeDetail,
  GenomeSummary,
  GovernanceState,
  KnowledgeMemory,
  KnowledgeSubjectSummary,
  OverviewState,
  RequirementSummary,
  RequirementTrace,
  RuntimeState,
  TimelineEntry
} from "./types";
```

---

# 8. Frontend: genome list page

Create:

**`observatory/frontend/app/genomes/page.tsx`**

```typescript
"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Section, StatusPill } from "@/components";
import { api } from "@/lib/api";
import type { GenomeSummary } from "@/lib/types";

export default function GenomesPage() {
  const [items, setItems] = useState<GenomeSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  const refresh = useCallback(async () => {
    try {
      const nextItems = await api.genomes();
      setItems(nextItems);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unknown error");
    }
  }, []);

  useEffect(() => {
    refresh();

    const interval = setInterval(refresh, 5000);

    return () => {
      clearInterval(interval);
    };
  }, [refresh]);

  if (error && !items) {
    return <div className="error">Genomes unavailable: {error}</div>;
  }

  if (!items) {
    return <div className="muted">Loading genomes…</div>;
  }

  const normalizedFilter = filter.trim().toLowerCase();

  const visibleItems =
    normalizedFilter.length === 0
      ? items
      : items.filter(item =>
          item.genome_id.toLowerCase().includes(normalizedFilter)
        );

  return (
    <div className="grid">
      {error ? <div className="error">{error}</div> : null}

      <Section title="Evolution Genomes">
        <input
          value={filter}
          onChange={event => setFilter(event.target.value)}
          placeholder="Filter genomes"
        />

        <div style={{ height: 12 }} />

        {visibleItems.length === 0 ? (
          <div className="empty">
            No genomes visible. Emit genome events to populate this view.
          </div>
        ) : (
          <ul className="timeline">
            {visibleItems.map(item => (
              <li key={item.genome_id} className="timeline-item">
                <div className="timeline-top">
                  <Link href={`/genomes/${item.genome_id}`}>
                    {item.genome_id}
                  </Link>

                  <StatusPill status={item.status} />
                </div>

                <div className="timeline-summary">{item.objective}</div>

                <div className="timeline-meta">
                  <span>candidate {item.candidate_id ?? "unknown"}</span>
                  <span>generation {item.generation ?? "unknown"}</span>
                  <span>pareto {item.pareto_state}</span>
                  <span>chromosomes {item.chromosome_count}</span>
                  <span>genes {item.gene_count}</span>
                  <span>mutations {item.mutation_count}</span>
                  <span>crossovers {item.crossover_count}</span>
                  <span>selections {item.selection_count}</span>
                  <span>fitness links {item.fitness_count}</span>
                  <span>unknowns {item.unknown_count}</span>
                  <span>contradictions {item.contradiction_count}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}
```

---

# 9. Frontend: genome detail page

Create:

**`observatory/frontend/app/genomes/[id]/page.tsx`**

```typescript
"use client";

import { useCallback, useEffect, useState } from "react";

import {
  EventTimeline,
  KeyValue,
  Section,
  StatusPill
} from "@/components";
import { api } from "@/lib/api";
import type { GenomeDetail, GenomeGene } from "@/lib/types";

function displayValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "unknown";
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

function GeneRow({ gene }: { gene: GenomeGene }) {
  return (
    <li className="timeline-item">
      <div className="timeline-top">
        <span>{gene.gene_id}</span>
        <StatusPill status={gene.status} />
      </div>

      <div className="timeline-meta">
        <span>value {displayValue(gene.value)}</span>
        <span>previous {displayValue(gene.previous_value)}</span>
        <span>mutations {gene.mutation_count}</span>
        <span>crossovers {gene.crossover_count}</span>
      </div>
    </li>
  );
}

export default function GenomeDetailPage({
  params
}: {
  params: { id: string };
}) {
  const [genome, setGenome] = useState<GenomeDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const nextGenome = await api.genomeDetail(params.id);
      setGenome(nextGenome);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unknown error");
    }
  }, [params.id]);

  useEffect(() => {
    refresh();

    const interval = setInterval(refresh, 5000);

    return () => {
      clearInterval(interval);
    };
  }, [refresh]);

  if (error && !genome) {
    return <div className="error">Genome unavailable: {error}</div>;
  }

  if (!genome) {
    return <div className="muted">Loading genome…</div>;
  }

  return (
    <div className="grid">
      {error ? <div className="error">{error}</div> : null}

      <Section
        title={`Genome ${genome.genome_id}`}
        right={<StatusPill status={genome.status} />}
      >
        <KeyValue
          data={{
            candidate_id: displayValue(genome.candidate_id),
            generation: displayValue(genome.generation),
            pareto_state: genome.pareto_state,
            environment: displayValue(genome.environment),
            updated_at: displayValue(genome.updated_at),
            first_observed_at: displayValue(genome.first_observed_at)
          }}
        />
      </Section>

      <Section title="Objective">
        {genome.objective ? (
          <div>{genome.objective}</div>
        ) : (
          <div className="empty">No objective recorded</div>
        )}
      </Section>

      <Section title="Description">
        {genome.description ? (
          <div>{genome.description}</div>
        ) : (
          <div className="empty">No description recorded</div>
        )}
      </Section>

      <div className="grid grid-2">
        <Section title="Requirement Links">
          {genome.requirement_links.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {genome.requirement_links.map(requirementId => (
                <li key={requirementId}>
                  <a href={`/requirements/${requirementId}`}>{requirementId}</a>
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Epistemic State">
          <KeyValue data={genome.epistemic_state} />
        </Section>
      </div>

      <Section title="Chromosomes">
        {genome.chromosomes.length === 0 ? (
          <div className="empty">No chromosomes recorded</div>
        ) : (
          <ul className="timeline">
            {genome.chromosomes.map(chromosome => (
              <li key={chromosome.name} className="timeline-item">
                <details>
                  <summary>
                    {chromosome.name} — {chromosome.gene_count} genes
                  </summary>

                  <div className="timeline-meta">
                    <span>mutations {chromosome.mutation_count}</span>
                    <span>crossovers {chromosome.crossover_count}</span>
                  </div>

                  <div style={{ height: 8 }} />

                  {chromosome.genes.length === 0 ? (
                    <div className="empty">No genes recorded</div>
                  ) : (
                    <ul className="timeline">
                      {chromosome.genes.map(gene => (
                        <GeneRow key={gene.gene_id} gene={gene} />
                      ))}
                    </ul>
                  )}
                </details>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Mutations">
        {genome.mutations.length === 0 ? (
          <div className="empty">No mutations recorded</div>
        ) : (
          <ul className="timeline">
            {genome.mutations.map(mutation => (
              <li key={mutation.mutation_id} className="timeline-item">
                <div className="timeline-top">
                  <span>{mutation.mutation_id}</span>
                  <span className="timeline-time">
                    {new Date(mutation.timestamp).toLocaleString()}
                  </span>
                </div>

                <div className="timeline-meta">
                  <span>chromosome {mutation.chromosome ?? "unknown"}</span>
                  <span>gene {mutation.gene_id ?? "unknown"}</span>
                  <span>previous {displayValue(mutation.previous_value)}</span>
                  <span>new {displayValue(mutation.new_value)}</span>
                  <span>evidence {mutation.evidence_refs.length}</span>
                </div>

                {mutation.reason ? (
                  <div className="timeline-summary">{mutation.reason}</div>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Crossovers">
        {genome.crossovers.length === 0 ? (
          <div className="empty">No crossovers recorded</div>
        ) : (
          <ul className="timeline">
            {genome.crossovers.map(crossover => (
              <li key={crossover.crossover_id} className="timeline-item">
                <div className="timeline-top">
                  <span>{crossover.crossover_id}</span>
                  <span className="timeline-time">
                    {new Date(crossover.timestamp).toLocaleString()}
                  </span>
                </div>

                <div className="timeline-meta">
                  <span>chromosome {crossover.chromosome ?? "unknown"}</span>
                  <span>gene {crossover.gene_id ?? "unknown"}</span>
                  <span>
                    parents {crossover.parent_genome_ids.join(", ") || "unknown"}
                  </span>
                  <span>evidence {crossover.evidence_refs.length}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Selections">
        {genome.selections.length === 0 ? (
          <div className="empty">No selections recorded</div>
        ) : (
          <ul className="timeline">
            {genome.selections.map(selection => (
              <li key={selection.selection_id} className="timeline-item">
                <div className="timeline-top">
                  <span>{selection.selection_id}</span>
                  <span className="timeline-time">
                    {new Date(selection.timestamp).toLocaleString()}
                  </span>
                </div>

                <div className="timeline-meta">
                  <span>candidate {selection.candidate_id ?? "unknown"}</span>
                  <span>outcome {displayValue(selection.outcome)}</span>
                  <span>evidence {selection.evidence_refs.length}</span>
                </div>

                {selection.reason ? (
                  <div className="timeline-summary">{selection.reason}</div>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </Section>

      <div className="grid grid-2">
        <Section title="Fitness Links">
          {genome.fitness_links.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {genome.fitness_links.map(fitnessId => (
                <li key={fitnessId}>
                  <a href={`/fitness/${fitnessId}`}>{fitnessId}</a>
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Evidence References">
          {genome.evidence_refs.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {genome.evidence_refs.map(evidenceId => (
                <li key={evidenceId}>
                  <a href={`/evidence/${evidenceId}`}>{evidenceId}</a>
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <div className="grid grid-2">
        <Section title="Unknowns">
          {genome.unknowns.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {genome.unknowns.map(unknown => (
                <li key={unknown.unknown_id}>{unknown.question}</li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Contradictions">
          {genome.contradictions.length === 0 ? (
            <div className="empty">None</div>
          ) : (
            <ul className="list">
              {genome.contradictions.map(contradiction => (
                <li key={contradiction.contradiction_id}>
                  {contradiction.statement}
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <Section title="Genome Timeline">
        <EventTimeline items={genome.timeline} />
      </Section>
    </div>
  );
}
```

---

# 10. Add Genomes to navigation

Update the navigation block in:

**`observatory/frontend/app/layout.tsx`**

```tsx
          <nav className="app-nav">
            <a href="/">Overview</a>
            <a href="/runtime">Runtime</a>
            <a href="/requirements">Requirements</a>
            <a href="/knowledge">Knowledge</a>
            <a href="/experiments">Experiments</a>
            <a href="/fitness">Fitness</a>
            <a href="/genomes">Genomes</a>
            <a href="/governance">Governance</a>
          </nav>
```

---

# 11. Genome event contract

The Genome view depends on explicit genome events.

Recommended event types:

```text
genome_proposed
genome_defined
genome_created
genome_updated
genome_rejected
chromosome_updated
gene_defined
gene_mutated
gene_crossover
selection_observed
selection_recorded
candidate_selected
candidate_rejected
fitness_linked
pareto_observed
unknown_recorded
contradiction_recorded
```

Recommended identifiers:

```text
GEN-001
GEN-VS1-OBJ001-CAND-313b
CAND-313b
GENE-PERSISTENCE-ENGINE
GENE-SECURITY-TENANT-ISOLATION
```

---

## Example: define a genome

```python
await adapter.observe(
    category="evolution",
    type="genome_defined",
    subject_id="GEN-VS1-OBJ001-CAND-313b",
    payload={
        "genome_id": "GEN-VS1-OBJ001-CAND-313b",
        "candidate_id": "vs1-obj001-candidate-313b071dd7d4",
        "generation": 1,
        "objective_id": "VS1-OBJ-001",
        "summary": "Genome defined for selected VS1 priority candidate",
    },
)
```

---

## Example: define a gene

```python
await adapter.observe(
    category="evolution",
    type="gene_defined",
    subject_id="GENE-PERSISTENCE-ENGINE",
    payload={
        "genome_id": "GEN-VS1-OBJ001-CAND-313b",
        "gene_id": "GENE-PERSISTENCE-ENGINE",
        "chromosome": "Persistence",
        "value": "sqlite",
        "summary": "Persistence engine gene defined",
    },
)
```

---

## Example: mutate a gene

```python
await adapter.observe(
    category="evolution",
    type="gene_mutated",
    subject_id="GENE-PERSISTENCE-ENGINE",
    payload={
        "genome_id": "GEN-VS1-OBJ001-CAND-313b",
        "gene_id": "GENE-PERSISTENCE-ENGINE",
        "chromosome": "Persistence",
        "previous_value": "sqlite",
        "new_value": "postgresql",
        "reason": "Evaluate stronger persistence backend for multi-tenant durability.",
        "summary": "Persistence gene mutated",
    },
)
```

---

## Example: crossover

```python
await adapter.observe(
    category="evolution",
    type="gene_crossover",
    subject_id="GENE-OBSERVABILITY-TRACING",
    payload={
        "genome_id": "GEN-VS1-OBJ001-CAND-313b",
        "gene_id": "GENE-OBSERVABILITY-TRACING",
        "chromosome": "Observability",
        "parent_genome_ids": [
            "GEN-VS1-OBJ001-CAND-a046",
            "GEN-VS1-OBJ001-CAND-313b",
        ],
        "summary": "Observability gene crossed over",
    },
)
```

---

## Example: selection outcome

```python
await adapter.observe(
    category="evolution",
    type="selection_recorded",
    subject_id="GEN-VS1-OBJ001-CAND-313b",
    payload={
        "genome_id": "GEN-VS1-OBJ001-CAND-313b",
        "candidate_id": "vs1-obj001-candidate-313b071dd7d4",
        "selection_id": "SEL-D24-001",
        "outcome": "selected",
        "reason": "Selected by D24 architecture selection gate.",
        "summary": "Genome selection recorded",
    },
)
```

---

## Example: fitness linkage

```python
await adapter.observe(
    category="evolution",
    type="fitness_linked",
    subject_id="GEN-VS1-OBJ001-CAND-313b",
    payload={
        "genome_id": "GEN-VS1-OBJ001-CAND-313b",
        "fitness_id": "FIT-VS1-PRIORITY-OBJECTIVE",
        "summary": "Genome linked to VS1 priority fitness objective",
    },
)
```

---

# 12. What this view establishes

The Evolution Genome view now exposes:

```text
genome identity
candidate linkage
generation
chromosome families
gene values
gene history
mutations
crossovers
selection outcomes
fitness linkage
Pareto state
unknowns
contradictions
genome timeline
```

It preserves the constitutional separation:

```text
The Observatory displays genome evidence.
The Evolution Engine owns genome mutation.
The Selection gate owns architecture selection.
The Decision gate owns authorization.
```

---

# 13. Verification checklist

Before treating the Genome view as production-ready, verify:

```text
genomes endpoint returns empty list when no genome events exist
genome events populate the list
genome detail returns 404 for unknown genome ID
chromosomes render known constitutional families first
custom chromosomes still render
genes render under chromosomes
gene values render only when recorded
mutations render previous/new values
crossovers render parent genome IDs
selections render outcomes
rejected genomes render rejected status
fitness links resolve to Fitness view
unknowns are preserved
contradictions are preserved
timeline renders newest first
UI does not mutate genome state
UI does not select architectures
UI does not authorize evolution
```

---

# 14. Next recommended step

The next surface should be the **Selection / Decision view**.

That view should expose:

```text
decision identity
decision question
candidate alternatives
selection outcome
evidence sufficiency
unknowns accepted
unknowns rejected
contradictions blocking decision
authorization granted or denied
next gate authorization state
```

This completes the Observatory’s governance loop:

```text
Requirements
Knowledge
Experiments
Fitness
Genomes
Selection / Decisions
Governance
```