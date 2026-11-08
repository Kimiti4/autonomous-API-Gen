"""Versioned digest envelope (ADR-R1-01, R1-W01). Content digest excludes envelope metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass

_SHA256_HEX_RE = re.compile(r"^[a-f0-9]{64}$")


@dataclass(frozen=True, slots=True)
class DigestEnvelope:
    hash_algorithm: str
    authority_domain: str
    isr_family_id: str
    schema_version: str
    canonicalization_id: str
    canonicalization_version: str
    content_digest: str
    revision_id: str | None = None
    provenance_ref: str | None = None

    def __post_init__(self) -> None:
        if self.hash_algorithm != "sha256":
            raise ValueError(f"unsupported-hash-algorithm: {self.hash_algorithm!r}")
        if not _SHA256_HEX_RE.match(self.content_digest):
            raise ValueError("content_digest must be 64-char lowercase sha256 hex")


AUTHORITY_DOMAIN_CERTIFICATION = "isr.core.certification"
AUTHORITY_DOMAIN_CONSTITUTIONAL = "constitutional.isr"
