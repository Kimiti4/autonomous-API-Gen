"""
Content Hashing.

Provides deterministic content hashing for ISR versions.
Used for caching, lineage tracking, and reproducibility.
"""

from __future__ import annotations

import hashlib

from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.serialization.serializer import ISRSerializer


class ContentHasher:
    """Deterministic content hashing for ISR artifacts."""

    @staticmethod
    def hash_isr(isr: ISR) -> str:
        canonical = ISRSerializer.to_canonical_json(isr)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def hash_string(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def hash_bytes(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def short_hash(isr: ISR, length: int = 12) -> str:
        return ContentHasher.hash_isr(isr)[:length]

    @staticmethod
    def verify_integrity(isr: ISR, expected_hash: str) -> bool:
        return ContentHasher.hash_isr(isr) == expected_hash
