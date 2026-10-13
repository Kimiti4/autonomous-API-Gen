"""Independent verification of compiler-obligation evidence references.

This module verifies evidence bytes supplied by a trusted retrieval boundary.
It does not fetch URLs, trust a record's claimed outcome by itself, or treat
missing evidence as success. Callers must retrieve bytes from an authorized,
auditable evidence store before invoking this verifier.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping

from tiannara.domain.models.compiler_obligation import (
    CompilerObligationRecord,
    Disposition,
)


@dataclass(frozen=True)
class ObligationEvidenceVerdict:
    """Independent verdict for one record against an expected source and suite."""

    disposition: Disposition
    verified_scenarios: tuple[str, ...]
    missing_scenarios: tuple[str, ...]
    invalid_evidence_refs: tuple[str, ...]
    blockers: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return self.disposition is Disposition.PASS and not self.blockers


def verify_obligation_evidence(
    record: CompilerObligationRecord,
    *,
    expected_source_graph_hash: str,
    required_scenario_ids: tuple[str, ...],
    evidence_bytes_by_ref: Mapping[str, bytes],
    expected_consumer_binding: str | None = None,
) -> ObligationEvidenceVerdict:
    """Recompute evidence hashes and enforce source/consumer/scenario binding.

    A record that claims PASS is not trusted. PASS is returned only when the
    obligation is required, its source hash matches, a consumer is bound,
    every required scenario is present and PASS, and each evidence reference
    resolves to bytes whose SHA-256 matches the record.
    """
    blockers: list[str] = []
    invalid_refs: list[str] = []
    verified: list[str] = []

    if not required_scenario_ids:
        blockers.append("at least one required acceptance scenario must be specified")
    if record.source_graph_hash != expected_source_graph_hash:
        blockers.append("source graph hash does not match the expected source")
    if record.applicability.value != "required":
        blockers.append("only required obligations can pass")
    if not record.consumer_binding.strip():
        blockers.append("consumer binding is missing")
    if expected_consumer_binding and record.consumer_binding != expected_consumer_binding:
        blockers.append("consumer binding does not match the expected consumer")
    if not record.enforcement_points:
        blockers.append("no enforcement point is bound")

    scenarios = {scenario.scenario_id: scenario for scenario in record.acceptance_scenarios}
    if len(scenarios) != len(record.acceptance_scenarios):
        blockers.append("duplicate acceptance scenario IDs are present")

    missing = sorted(set(required_scenario_ids) - set(scenarios))
    if missing:
        blockers.append("required acceptance scenarios are missing")

    for scenario_id, scenario in sorted(scenarios.items()):
        if scenario.outcome != "PASS":
            blockers.append(f"scenario {scenario_id} outcome is {scenario.outcome}, not PASS")
            continue
        evidence = evidence_bytes_by_ref.get(scenario.evidence_ref)
        if evidence is None:
            invalid_refs.append(scenario.evidence_ref)
            blockers.append(f"evidence bytes are unavailable for scenario {scenario_id}")
            continue
        if not isinstance(evidence, bytes):
            invalid_refs.append(scenario.evidence_ref)
            blockers.append(f"evidence payload is not bytes for scenario {scenario_id}")
            continue
        actual_hash = hashlib.sha256(evidence).hexdigest()
        if actual_hash != scenario.evidence_sha256:
            invalid_refs.append(scenario.evidence_ref)
            blockers.append(f"evidence hash mismatch for scenario {scenario_id}")
            continue
        if not scenario.build_id.strip() or not scenario.environment_fingerprint.strip():
            blockers.append(f"build/environment binding is missing for scenario {scenario_id}")
            continue
        verified.append(scenario_id)

    if record.disposition is Disposition.FAIL:
        blockers.append("source record is already marked FAIL")
        disposition = Disposition.FAIL
    elif record.disposition in (
        Disposition.BLOCKED_NO_CONSUMER,
        Disposition.BLOCKED_UNRESOLVED,
        Disposition.UNSUPPORTED,
        Disposition.NOT_APPLICABLE,
    ):
        blockers.append(f"source record disposition is {record.disposition.value}")
        disposition = record.disposition
    elif blockers:
        disposition = Disposition.UNKNOWN
    elif set(required_scenario_ids) - set(verified):
        blockers.append("not every required scenario has independently verified evidence")
        disposition = Disposition.UNKNOWN
    else:
        disposition = Disposition.PASS

    return ObligationEvidenceVerdict(
        disposition=disposition,
        verified_scenarios=tuple(sorted(verified)),
        missing_scenarios=tuple(missing),
        invalid_evidence_refs=tuple(sorted(set(invalid_refs))),
        blockers=tuple(blockers),
    )
