"""Digest authority verification and cross-domain policy (ADR-R1-01)."""

from __future__ import annotations

import json

from isr.core.canonicalization_registry import (
    F01_ISR_REVISION,
    get_canonicalization_contract,
)
from isr.core.digest_envelope import (
    AUTHORITY_DOMAIN_CERTIFICATION,
    DigestEnvelope,
)
from isr.core.graph import ISRGraph
from isr.core.identity import compute_content_hash
from isr.core.revision import ISRRevision


class DigestVerificationError(ValueError):
    """Fail-closed digest or authority violation."""


class DigestPolicyViolation(DigestVerificationError):
    """Policy forbids the attempted digest comparison or substitution."""


def canonical_bytes_f01(schema_version: str, graph: ISRGraph) -> bytes:
    """Reproducible canonical payload bytes for F-01/F-02 (ADR-R1-02)."""
    contract = get_canonicalization_contract(F01_ISR_REVISION.isr_family_id)
    if schema_version not in contract.schema_versions_supported:
        raise DigestVerificationError(
            f"unsupported-schema-version: {schema_version!r} for {contract.isr_family_id}"
        )
    canonical = {
        "schema_version": schema_version,
        "nodes": {
            key: node.model_dump(mode="json")
            for key, node in sorted(graph.nodes.items())
        },
        "edges": {
            key: edge.model_dump(mode="json")
            for key, edge in sorted(graph.edges.items())
        },
    }
    return json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def build_digest_envelope_for_revision(revision: ISRRevision) -> DigestEnvelope:
    """Build certification-path envelope for a governed ISRRevision."""
    contract = get_canonicalization_contract(F01_ISR_REVISION.isr_family_id)
    if revision.schema_version not in contract.schema_versions_supported:
        raise DigestVerificationError("revision-schema-version-not-supported")
    return DigestEnvelope(
        hash_algorithm=contract.hash_algorithm,
        authority_domain=contract.authority_domain,
        isr_family_id=contract.isr_family_id,
        schema_version=revision.schema_version,
        canonicalization_id=contract.canonicalization_id,
        canonicalization_version=contract.canonicalization_version,
        content_digest=revision.content_hash,
        revision_id=revision.revision_id,
        provenance_ref=revision.provenance.created_by,
    )


def recompute_certification_content_digest(schema_version: str, graph: ISRGraph) -> str:
    return compute_content_hash(schema_version, graph)


def verify_revision_content_integrity(revision: ISRRevision) -> DigestEnvelope:
    """Recompute digest and fail closed on mismatch with stored content_hash."""
    contract = get_canonicalization_contract(F01_ISR_REVISION.isr_family_id)
    if revision.schema_version not in contract.schema_versions_supported:
        raise DigestVerificationError("unsupported-schema-version")
    recomputed = recompute_certification_content_digest(
        revision.schema_version, revision.graph
    )
    if recomputed != revision.content_hash:
        raise DigestVerificationError("content-digest-mismatch")
    envelope = build_digest_envelope_for_revision(revision)
    if envelope.content_digest != recomputed:
        raise DigestVerificationError("envelope-digest-mismatch")
    return envelope


def assert_certification_digest_envelope(revision: ISRRevision) -> DigestEnvelope:
    """Trust-boundary helper for orchestration / certification ingress."""
    envelope = verify_revision_content_integrity(revision)
    if envelope.authority_domain != AUTHORITY_DOMAIN_CERTIFICATION:
        raise DigestVerificationError("wrong-authority-domain")
    if envelope.isr_family_id != F01_ISR_REVISION.isr_family_id:
        raise DigestPolicyViolation("wrong-isr-family")
    return envelope


def assert_cross_domain_digest_substitution_forbidden(
    left: DigestEnvelope,
    right: DigestEnvelope,
) -> None:
    """Digest equality must not be interpreted across authority domains."""
    if left.authority_domain != right.authority_domain:
        raise DigestPolicyViolation("cross-domain-digest-interchange-forbidden")
    if left.isr_family_id != right.isr_family_id:
        raise DigestPolicyViolation("cross-family-digest-substitution-forbidden")
    if left.canonicalization_id != right.canonicalization_id:
        raise DigestVerificationError("canonicalization-id-mismatch")
    if left.canonicalization_version != right.canonicalization_version:
        raise DigestVerificationError("canonicalization-version-mismatch")


def digest_equivalence_is_not_semantic_equivalence() -> None:
    """Documented guard — matching digests never imply semantic equivalence alone."""


def verify_envelope_against_revision(
    envelope: DigestEnvelope,
    revision: ISRRevision,
) -> None:
    """Verify an envelope matches an in-memory revision (e.g. stale digest detection)."""
    if envelope.revision_id and envelope.revision_id != revision.revision_id:
        raise DigestVerificationError("revision-id-mismatch")
    fresh = build_digest_envelope_for_revision(revision)
    if envelope.content_digest != fresh.content_digest:
        raise DigestVerificationError("stale-or-tampered-content-digest")
    assert_cross_domain_digest_substitution_forbidden(envelope, fresh)
