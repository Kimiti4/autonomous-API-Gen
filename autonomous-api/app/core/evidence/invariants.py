"""Evidence invariant enforcement (§4.3, E-1..E-3)."""
from __future__ import annotations

from app.core.ids import content_hash


class EvidenceInvariantError(Exception):
    """Raised when a command would violate an evidence invariant (E-x)."""


def check_e1_content_hash(artifact) -> str:
    """E-1: contentHash is SHA-256 of the artifact, computed at write time."""
    if isinstance(artifact, bytes):
        payload = artifact.decode("utf-8", errors="replace")
    else:
        payload = artifact
    return content_hash(payload)


def check_e2_immutability(existing: bool) -> None:
    """E-2: evidence is immutable once stored."""
    if existing:
        raise EvidenceInvariantError(
            "E-2 violated: evidence is immutable once stored"
        )