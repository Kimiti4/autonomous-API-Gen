"""Constitutional ISR digest envelope (F-06) — separate authority domain (ADR-R1-01)."""

from __future__ import annotations

from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.serialization.serializer import ISRSerializer
from constitutional_architecture.isr.versioning.hash import ContentHasher
from isr.core.digest_envelope import (
    AUTHORITY_DOMAIN_CONSTITUTIONAL,
    DigestEnvelope,
)
from isr.core.digest_verification import DigestPolicyViolation

CONSTITUTIONAL_CANONICALIZATION_ID = "constitutional.isr.serializer"
CONSTITUTIONAL_CANONICALIZATION_VERSION = "1.0.0"
CONSTITUTIONAL_FAMILY_ID = "constitutional_architecture.isr.model"


def build_constitutional_digest_envelope(
    isr: ISR,
    *,
    revision_id: str | None = None,
    schema_version: str = "1.0",
) -> DigestEnvelope:
    content_digest = ContentHasher.hash_isr(isr)
    return DigestEnvelope(
        hash_algorithm="sha256",
        authority_domain=AUTHORITY_DOMAIN_CONSTITUTIONAL,
        isr_family_id=CONSTITUTIONAL_FAMILY_ID,
        schema_version=schema_version,
        canonicalization_id=CONSTITUTIONAL_CANONICALIZATION_ID,
        canonicalization_version=CONSTITUTIONAL_CANONICALIZATION_VERSION,
        content_digest=content_digest,
        revision_id=revision_id,
    )


def verify_constitutional_content_integrity(isr: ISR, expected_digest: str) -> DigestEnvelope:
    if not ContentHasher.verify_integrity(isr, expected_digest):
        raise DigestPolicyViolation("constitutional-content-digest-mismatch")
    return build_constitutional_digest_envelope(isr)


def constitutional_canonical_bytes(isr: ISR) -> bytes:
    return ISRSerializer.to_canonical_json(isr).encode("utf-8")
