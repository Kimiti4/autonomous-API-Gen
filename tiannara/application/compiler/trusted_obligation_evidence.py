"""Cryptographically verify execution evidence before compiler certification.

Evidence bytes and their metadata must be obtained from an authorized,
auditable evidence store. The HMAC attestation binds those bytes to the source
graph, obligation, scenario, consumer, build, environment, and an allow-listed
runner. This proves provenance/integrity under the configured key trust model;
it does not prove the runner's test logic is correct.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, replace
from typing import Mapping, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tiannara.application.compiler.obligation_certification import (
    ObligationCertificationVerdict,
    assemble_obligation_certification,
)
from tiannara.application.compiler.obligation_evidence import (
    ObligationEvidenceVerdict,
    verify_obligation_evidence,
)
from tiannara.domain.models.compiler_obligation import (
    CompilerObligationRecord,
    Disposition,
    ScenarioEvidence,
)


class TrustedEvidenceAttestation(BaseModel):
    """Runner-signed statement binding a test result to exact evidence bytes."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    attestation_id: str = Field(min_length=16, max_length=256)
    key_id: str = Field(min_length=1, max_length=128)
    runner_id: str = Field(min_length=1, max_length=256)
    source_graph_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    obligation_id: str = Field(min_length=1, max_length=256)
    scenario_id: str = Field(min_length=1, max_length=256)
    outcome: str = Field(pattern=r"^(PASS|FAIL|ERROR|NOT_RUN|INCONCLUSIVE)$")
    evidence_ref: str = Field(min_length=1, max_length=2048)
    evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    consumer_binding: str = Field(min_length=1, max_length=512)
    build_id: str = Field(min_length=1, max_length=256)
    environment_fingerprint: str = Field(min_length=1, max_length=256)
    issued_at: str = Field(min_length=1, max_length=64)
    signature_hmac_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identifier(self):
        if not self.attestation_id.strip():
            raise ValueError("attestation_id cannot be blank")
        return self

    def signed_payload(self) -> dict[str, str]:
        """Canonical fields covered by the runner's HMAC; excludes signature."""
        return {
            "attestation_id": self.attestation_id,
            "key_id": self.key_id,
            "runner_id": self.runner_id,
            "source_graph_hash": self.source_graph_hash,
            "obligation_id": self.obligation_id,
            "scenario_id": self.scenario_id,
            "outcome": self.outcome,
            "evidence_ref": self.evidence_ref,
            "evidence_sha256": self.evidence_sha256,
            "consumer_binding": self.consumer_binding,
            "build_id": self.build_id,
            "environment_fingerprint": self.environment_fingerprint,
            "issued_at": self.issued_at,
        }

    def canonical_signed_bytes(self) -> bytes:
        return json.dumps(
            self.signed_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")


@dataclass(frozen=True)
class RetrievedTrustedEvidence:
    """One payload and its attestation returned by the configured evidence store."""

    payload: bytes
    attestation: TrustedEvidenceAttestation


class TrustedEvidenceStore(Protocol):
    """Trusted, authorized, auditable evidence retrieval boundary."""

    def read(self, evidence_ref: str) -> RetrievedTrustedEvidence | None:
        """Resolve a reference or return None; implementations must audit reads."""


@dataclass(frozen=True)
class TrustedObligationSuitePolicy:
    """Trusted suite definition loaded from reviewed, versioned configuration."""

    suite_id: str
    required_obligation_ids: tuple[str, ...]
    expected_consumer_bindings: Mapping[str, str]
    required_scenario_ids: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True)
class TrustedObligationCertificationRequest:
    """Source-derived obligation records for one compile; no caller-selected suite."""

    records: tuple[CompilerObligationRecord, ...]
    previously_used_attestation_ids: frozenset[str] = frozenset()


def verify_attestation(
    attestation: TrustedEvidenceAttestation,
    *,
    evidence: bytes,
    expected_source_graph_hash: str,
    expected_obligation_id: str,
    expected_scenario: ScenarioEvidence,
    expected_consumer_binding: str,
    trusted_hmac_keys: Mapping[str, bytes],
    allowed_runner_ids: frozenset[str],
) -> tuple[bool, str]:
    """Validate signature, runner allow-list, and every scenario binding."""
    key = trusted_hmac_keys.get(attestation.key_id)
    if key is None or not isinstance(key, bytes) or not key:
        return False, "attestation key is absent from the trusted key registry"
    if attestation.runner_id not in allowed_runner_ids:
        return False, "attestation runner is not allow-listed"
    if not hmac.compare_digest(
        hmac.new(key, attestation.canonical_signed_bytes(), hashlib.sha256).hexdigest(),
        attestation.signature_hmac_sha256,
    ):
        return False, "attestation HMAC signature is invalid"

    expected_fields = (
        (attestation.source_graph_hash, expected_source_graph_hash, "source graph"),
        (attestation.obligation_id, expected_obligation_id, "obligation"),
        (attestation.scenario_id, expected_scenario.scenario_id, "scenario"),
        (attestation.outcome, expected_scenario.outcome, "outcome"),
        (attestation.evidence_ref, expected_scenario.evidence_ref, "evidence reference"),
        (attestation.evidence_sha256, expected_scenario.evidence_sha256, "evidence hash"),
        (attestation.consumer_binding, expected_consumer_binding, "consumer"),
        (attestation.build_id, expected_scenario.build_id, "build"),
        (
            attestation.environment_fingerprint,
            expected_scenario.environment_fingerprint,
            "environment",
        ),
    )
    for actual, expected, label in expected_fields:
        if actual != expected:
            return False, f"attestation {label} binding does not match the obligation record"

    if not isinstance(evidence, bytes):
        return False, "evidence store returned a non-bytes payload"
    actual_hash = hashlib.sha256(evidence).hexdigest()
    if not hmac.compare_digest(actual_hash, attestation.evidence_sha256):
        return False, "retrieved evidence bytes do not match the signed evidence hash"
    return True, ""


def certify_trusted_obligation_suite(
    request: TrustedObligationCertificationRequest,
    *,
    policy: TrustedObligationSuitePolicy,
    expected_source_graph_hash: str,
    evidence_store: TrustedEvidenceStore,
    trusted_hmac_keys: Mapping[str, bytes],
    allowed_runner_ids: frozenset[str],
) -> ObligationCertificationVerdict:
    """Verify signed evidence for each required obligation, then aggregate.

    All evidence references are resolved through the configured trusted store
    and must have a signed attestation from an allow-listed runner. The suite
    fails closed on duplicate/missing records, missing attestations, untrusted
    runners, invalid signatures,
    stale source/consumer bindings, or unverified evidence.
    """
    records_by_id: dict[str, CompilerObligationRecord] = {}
    duplicate_ids: set[str] = set()
    seen_attestation_ids: set[str] = set()
    replayed_attestation_ids: set[str] = set()
    for record in request.records:
        if record.obligation_id in records_by_id:
            duplicate_ids.add(record.obligation_id)
        else:
            records_by_id[record.obligation_id] = record

    evaluations = []
    for obligation_id in policy.required_obligation_ids:
        record = records_by_id.get(obligation_id)
        if record is None:
            continue
        scenario_ids = policy.required_scenario_ids.get(obligation_id, ())
        expected_consumer = policy.expected_consumer_bindings.get(obligation_id, "")
        trust_blockers: list[str] = []
        evidence_for_verifier: dict[str, bytes] = {}

        for scenario in record.acceptance_scenarios:
            try:
                retrieved = evidence_store.read(scenario.evidence_ref)
            except Exception as exc:
                trust_blockers.append(
                    f"{obligation_id}/{scenario.scenario_id}: evidence retrieval failed "
                    f"({type(exc).__name__})"
                )
                continue
            if retrieved is None:
                trust_blockers.append(
                    f"{obligation_id}/{scenario.scenario_id}: missing retrieved bytes or signed attestation"
                )
                continue
            if not isinstance(retrieved, RetrievedTrustedEvidence) or not isinstance(
                retrieved.attestation, TrustedEvidenceAttestation
            ):
                trust_blockers.append(
                    f"{obligation_id}/{scenario.scenario_id}: evidence store returned an invalid bundle"
                )
                continue
            evidence = retrieved.payload
            attestation = retrieved.attestation
            if attestation.attestation_id in seen_attestation_ids:
                trust_blockers.append(
                    f"{obligation_id}/{scenario.scenario_id}: duplicate attestation ID in suite"
                )
                continue
            seen_attestation_ids.add(attestation.attestation_id)
            if attestation.attestation_id in request.previously_used_attestation_ids:
                replayed_attestation_ids.add(attestation.attestation_id)
                trust_blockers.append(
                    f"{obligation_id}/{scenario.scenario_id}: attestation ID was already consumed"
                )
                continue
            valid, reason = verify_attestation(
                attestation,
                evidence=evidence,
                expected_source_graph_hash=expected_source_graph_hash,
                expected_obligation_id=obligation_id,
                expected_scenario=scenario,
                expected_consumer_binding=expected_consumer,
                trusted_hmac_keys=trusted_hmac_keys,
                allowed_runner_ids=allowed_runner_ids,
            )
            if valid:
                evidence_for_verifier[scenario.evidence_ref] = evidence
            else:
                trust_blockers.append(f"{obligation_id}/{scenario.scenario_id}: {reason}")

        if obligation_id in duplicate_ids:
            trust_blockers.append(f"{obligation_id}: duplicate obligation records")
        if not expected_consumer:
            trust_blockers.append(f"{obligation_id}: no expected consumer binding configured")

        verdict = verify_obligation_evidence(
            record,
            expected_source_graph_hash=expected_source_graph_hash,
            required_scenario_ids=tuple(scenario_ids),
            evidence_bytes_by_ref=evidence_for_verifier,
            expected_consumer_binding=expected_consumer or None,
        )
        if trust_blockers:
            # Preserve an observed failure. Otherwise downgrade any claimed pass.
            disposition = (
                Disposition.FAIL
                if verdict.disposition is Disposition.FAIL
                else Disposition.UNKNOWN
            )
            verdict = ObligationEvidenceVerdict(
                disposition=disposition,
                verified_scenarios=verdict.verified_scenarios,
                missing_scenarios=verdict.missing_scenarios,
                invalid_evidence_refs=verdict.invalid_evidence_refs,
                blockers=tuple((*verdict.blockers, *trust_blockers)),
            )
        evaluations.append((record, verdict))

    aggregate = assemble_obligation_certification(
        evaluations,
        expected_source_graph_hash=expected_source_graph_hash,
        required_obligation_ids=policy.required_obligation_ids,
    )
    if not duplicate_ids and not replayed_attestation_ids:
        return aggregate

    # Duplicate IDs and replay are contradictory input even if the first
    # record passed.
    extra_blockers = []
    if duplicate_ids:
        extra_blockers.append(f"duplicate obligation IDs: {sorted(duplicate_ids)}")
    if replayed_attestation_ids:
        extra_blockers.append(
            f"replayed attestation IDs: {sorted(replayed_attestation_ids)}"
        )
    disposition = (
        Disposition.FAIL
        if aggregate.disposition is Disposition.FAIL
        else Disposition.UNKNOWN
    )
    return replace(
        aggregate,
        disposition=disposition,
        blockers=tuple((*aggregate.blockers, *extra_blockers)),
    )
