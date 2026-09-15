"""Genome overview + detail projections (pure functions).

Read-only derived state over recorded genome events. Display only: this
view never mutates genomes, selects architectures, or authorizes
evolution. Unrecorded dimensions stay absent/unknown, never defaulted
to a healthy state.
"""
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
    "Architecture", "Persistence", "Infrastructure", "Security",
    "Messaging", "Observability", "AI", "Testing", "Deployment",
    "Frontend", "Backend", "Governance", "Documentation", "Performance",
    "Reliability",
]

KNOWN_CHROMOSOME_ORDER = {
    name.lower(): index for index, name in enumerate(KNOWN_CHROMOSOME_FAMILIES)
}

GENOME_PROPOSAL_TYPES = {"genome_proposed", "genome_defined", "genome_created"}
MUTATION_TYPES = {"gene_mutated", "mutation_recorded", "genome_mutated"}
CROSSOVER_TYPES = {"gene_crossover", "crossover_recorded", "genome_crossover"}
SELECTION_TYPES = {"selection_observed", "selection_recorded",
                   "candidate_selected", "candidate_rejected"}
REJECTION_TYPES = {"genome_rejected", "candidate_rejected",
                   "selection_rejected"}
PARETO_TYPES = {"pareto_observed", "pareto_updated"}
REJECTED_OUTCOMES = {"rejected", "reject", "denied", "blocked"}


def _merge_unique(*lists: List[str]) -> List[str]:
    merged = set()
    for values in lists:
        for value in values:
            if value is None:
                continue
            merged.add(str(value))
    return sorted(merged)


def _first_str(payload: Dict[str, Any], keys: tuple,
               default: Optional[str] = None) -> Optional[str]:
    for key in keys:
        value = payload_get(payload, key)
        if value is not None:
            return str(value)
    return default


def _latest_payload_value(events: List[Event], key: str,
                          default: Any = None) -> Any:
    for event in reversed(events):
        value = payload_get(event.payload, key)
        if value is not None:
            return value
    return default


def extract_genome_id(event: Event) -> Optional[str]:
    for key in ("genome_id", "genome_identity", "candidate_genome_id"):
        value = payload_get(event.payload, key)
        if value is not None:
            return str(value)
    if event.type.startswith(("genome_", "chromosome_", "mutation_",
                              "crossover_")):
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
    for key in ("gene_id", "gene_name", "gene"):
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
    for key in ("chromosome", "chromosome_family", "family", "domain"):
        value = payload_get(event.payload, key)
        if value is not None:
            return str(value)
    return None


def chromosome_sort_key(name: str) -> tuple:
    normalized = name.strip().lower()
    return (KNOWN_CHROMOSOME_ORDER.get(normalized, len(KNOWN_CHROMOSOME_FAMILIES)),
            normalized)


def derive_genome_status(events: List[Event]) -> str:
    explicit_status = _latest_payload_value(events, "status")
    if explicit_status is not None:
        return str(explicit_status)
    for event in reversed(events):
        # Rejection checked first: candidate_rejected belongs to both sets
        # and must never default to "selected" when no outcome is recorded.
        if event.type in REJECTION_TYPES:
            return "rejected"
        if event.type in SELECTION_TYPES:
            outcome = payload_get(event.payload, "outcome",
                                  payload_get(event.payload, "decision"))
            if outcome is not None and str(outcome).strip().lower() in REJECTED_OUTCOMES:
                return "rejected"
            return "selected"
        if event.type in CROSSOVER_TYPES:
            return "crossed_over"
        if event.type in MUTATION_TYPES:
            return "mutated"
        if event.type in GENOME_PROPOSAL_TYPES:
            return "proposed"
    return "unknown"


def derive_pareto_state(events: List[Event]) -> str:
    explicit_state = _latest_payload_value(
        events, "pareto_state",
        _latest_payload_value(events, "pareto_status"))
    if explicit_state is not None:
        return str(explicit_state)
    for event in reversed(events):
        if event.type in PARETO_TYPES:
            return str(payload_get(event.payload, "pareto_status", "observed"))
    return "unknown"


def build_genome_unknowns(events: List[Event]) -> List[Dict[str, Any]]:
    unknowns: List[Dict[str, Any]] = []
    for event in events:
        if (event.epistemic_status == EpistemicStatus.UNKNOWN
                or event.type.startswith("unknown_")):
            unknowns.append({
                "unknown_id": str(payload_get(event.payload, "unknown_id",
                                              event.id)),
                "question": str(_first_str(
                    event.payload,
                    ("question", "unknown", "statement", "summary"),
                    default="Unknown genome condition")),
                "timestamp": event.timestamp,
            })
    return unknowns


def build_genome_contradictions(events: List[Event]) -> List[Dict[str, Any]]:
    contradictions: List[Dict[str, Any]] = []
    for event in events:
        if (event.epistemic_status == EpistemicStatus.CONTRADICTION
                or event.type.startswith("contradiction_")):
            contradictions.append({
                "contradiction_id": str(payload_get(
                    event.payload, "contradiction_id", event.id)),
                "statement": str(_first_str(
                    event.payload, ("statement", "summary"),
                    default="Genome evidence contradiction")),
                "timestamp": event.timestamp,
            })
    return contradictions


def build_timeline(events: List[Event]) -> List[Dict[str, Any]]:
    return [{
        "event_id": event.id,
        "timestamp": event.timestamp,
        "category": event.category.value,
        "type": event.type,
        "subject_id": event.subject_id,
        "epistemic_status": event.epistemic_status.value,
        "severity": event.severity.value,
        "summary": str(payload_get(event.payload, "summary",
                                   f"{event.type}: {event.subject_id}")),
    } for event in reversed(events)]


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
        # Newest information wins per event (a mutation's new_value
        # supersedes an older defined value even at equal timestamps).
        value = None
        for event in reversed(sorted_events):
            for key in ("value", "allele", "new_value", "current_value"):
                candidate = payload_get(event.payload, key)
                if candidate is not None:
                    value = candidate
                    break
            if value is not None:
                break
        previous_value = _latest_payload_value(
            sorted_events, "previous_value",
            _latest_payload_value(sorted_events, "from_value"))
        mutation_count = sum(
            1 for event in sorted_events if event.type in MUTATION_TYPES)
        crossover_count = sum(
            1 for event in sorted_events if event.type in CROSSOVER_TYPES)
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
            status = "unknown"
        genes.append({
            "gene_id": gene_id,
            "chromosome": chromosome or "Unknown",
            "value": value,
            "previous_value": previous_value,
            "status": status,
            "mutation_count": mutation_count,
            "crossover_count": crossover_count,
            "updated_at": latest.timestamp,
        })
    return sorted(genes, key=lambda item: (item["chromosome"], item["gene_id"]))


def build_genome_chromosomes(events: List[Event],
                             genes: Optional[List[Dict[str, Any]]] = None
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
        chromosomes[name] = {"name": name, "genes": [], "gene_count": 0,
                             "mutation_count": 0, "crossover_count": 0,
                             "status": "unknown"}
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
        chromosome["genes"] = sorted(chromosome["genes"],
                                     key=lambda item: item["gene_id"])
        chromosome["gene_count"] = len(chromosome["genes"])
        result.append(chromosome)
    return sorted(result, key=lambda item: chromosome_sort_key(item["name"]))


def build_genome_mutations(events: List[Event]) -> List[Dict[str, Any]]:
    mutations: List[Dict[str, Any]] = []
    for event in events:
        if event.type not in MUTATION_TYPES and not event.type.startswith(
                "mutation_"):
            continue
        mutations.append({
            "mutation_id": str(payload_get(event.payload, "mutation_id",
                                           event.id)),
            "timestamp": event.timestamp,
            "chromosome": extract_chromosome(event),
            "gene_id": extract_gene_id(event),
            "previous_value": payload_get(
                event.payload, "previous_value",
                payload_get(event.payload, "from_value")),
            "new_value": payload_get(
                event.payload, "new_value",
                payload_get(event.payload, "to_value",
                            payload_get(event.payload, "value"))),
            "reason": payload_get(event.payload, "reason"),
            "evidence_refs": list(event.evidence_refs),
        })
    return mutations


def build_genome_crossovers(events: List[Event]) -> List[Dict[str, Any]]:
    crossovers: List[Dict[str, Any]] = []
    for event in events:
        if (event.type not in CROSSOVER_TYPES
                and not event.type.startswith("crossover_")):
            continue
        parent_genomes = payload_get(
            event.payload, "parent_genome_ids",
            payload_get(event.payload, "source_genome_ids", []))
        if not isinstance(parent_genomes, list):
            parent_genomes = [parent_genomes]
        crossovers.append({
            "crossover_id": str(payload_get(event.payload, "crossover_id",
                                            event.id)),
            "timestamp": event.timestamp,
            "chromosome": extract_chromosome(event),
            "gene_id": extract_gene_id(event),
            "parent_genome_ids": [str(parent) for parent in parent_genomes
                                  if parent is not None],
            "evidence_refs": list(event.evidence_refs),
        })
    return crossovers


def build_genome_selections(events: List[Event]) -> List[Dict[str, Any]]:
    selections: List[Dict[str, Any]] = []
    for event in events:
        if (event.type not in SELECTION_TYPES
                and not event.type.startswith("selection_")):
            continue
        outcome = payload_get(event.payload, "outcome",
                              payload_get(event.payload, "decision"))
        selections.append({
            "selection_id": str(payload_get(event.payload, "selection_id",
                                            event.id)),
            "timestamp": event.timestamp,
            "candidate_id": payload_get(event.payload, "candidate_id",
                                        event.subject_id),
            "outcome": outcome,
            "reason": payload_get(event.payload, "reason"),
            "evidence_refs": list(event.evidence_refs),
        })
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
        objective = _first_str(latest.payload, ("objective", "summary", "title"),
                               default=genome_id)
        genes = build_genome_genes(sorted_events)
        chromosome_names = {gene["chromosome"] for gene in genes}
        for event in sorted_events:
            chromosome = extract_chromosome(event)
            if chromosome is not None:
                chromosome_names.add(chromosome)
        epistemic_state = count_epistemic(sorted_events)
        summaries.append({
            "genome_id": genome_id,
            "status": derive_genome_status(sorted_events),
            "candidate_id": candidate_id,
            "generation": generation,
            "objective": objective,
            "pareto_state": derive_pareto_state(sorted_events),
            "chromosome_count": len(chromosome_names),
            "gene_count": len(genes),
            "mutation_count": sum(
                1 for event in sorted_events if event.type in MUTATION_TYPES),
            "crossover_count": sum(
                1 for event in sorted_events if event.type in CROSSOVER_TYPES),
            "selection_count": sum(
                1 for event in sorted_events if event.type in SELECTION_TYPES),
            "fitness_count": len(build_fitness_links(sorted_events)),
            "evidence_count": len(collect_evidence_refs(sorted_events)),
            "unknown_count": epistemic_state["unknown"],
            "contradiction_count": epistemic_state["contradiction"],
            "updated_at": latest.timestamp,
        })
    return sorted(summaries, key=lambda item: item["genome_id"])


def build_genome_detail(genome_id: str,
                        events: List[Event]) -> Optional[Dict[str, Any]]:
    relevant = [event for event in events
                if extract_genome_id(event) == genome_id
                or event.subject_id == genome_id]
    if not relevant:
        return None
    relevant_sorted = sort_asc(relevant)
    latest = latest_event(relevant_sorted)
    if latest is None:
        return None
    objective = _first_str(latest.payload, ("objective", "summary", "title"),
                           default=genome_id)
    genes = build_genome_genes(relevant_sorted)
    return {
        "genome_id": genome_id,
        "status": derive_genome_status(relevant_sorted),
        "candidate_id": _latest_payload_value(relevant_sorted, "candidate_id"),
        "generation": _latest_payload_value(relevant_sorted, "generation"),
        "objective": objective,
        "description": _latest_payload_value(relevant_sorted, "description"),
        "environment": _latest_payload_value(relevant_sorted, "environment"),
        "requirement_links": _merge_unique(
            collect_payload_list(relevant_sorted, "requirement_id"),
            collect_payload_list(relevant_sorted, "objective_id")),
        "pareto_state": derive_pareto_state(relevant_sorted),
        "epistemic_state": count_epistemic(relevant_sorted),
        "chromosomes": build_genome_chromosomes(relevant_sorted, genes),
        "genes": genes,
        "mutations": build_genome_mutations(relevant_sorted),
        "crossovers": build_genome_crossovers(relevant_sorted),
        "selections": build_genome_selections(relevant_sorted),
        "fitness_links": build_fitness_links(relevant_sorted),
        "evidence_refs": _merge_unique(
            collect_evidence_refs(relevant_sorted),
            collect_payload_list(relevant_sorted, "evidence_id"),
            collect_payload_list(relevant_sorted, "evidence_refs")),
        "unknowns": build_genome_unknowns(relevant_sorted),
        "contradictions": build_genome_contradictions(relevant_sorted),
        "timeline": build_timeline(relevant_sorted),
        "provenance": latest.provenance,
        "sources": sorted({event.source for event in relevant_sorted}),
        "first_observed_at": relevant_sorted[0].timestamp,
        "updated_at": latest.timestamp,
    }
