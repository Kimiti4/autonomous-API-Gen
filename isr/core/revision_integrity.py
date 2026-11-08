"""R1-W03 — revision integrity helpers (create-path enforcement at trust boundaries)."""

from __future__ import annotations

from isr.core.digest_verification import (
    DigestVerificationError,
    verify_revision_content_integrity,
)
from isr.core.revision import ISRRevision


def assert_revision_integrity_at_boundary(revision: ISRRevision) -> None:
    """Fail closed if stored digest does not match canonical recomputation."""
    try:
        verify_revision_content_integrity(revision)
    except DigestVerificationError as exc:
        raise DigestVerificationError(
            "revision-integrity-boundary-failed"
        ) from exc
