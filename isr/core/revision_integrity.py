"""R1-W03 — revision integrity helpers (create-path enforcement at trust boundaries)."""

from __future__ import annotations

from isr.core.digest_verification import (
    DigestVerificationError,
    verify_revision_content_integrity,
)
from isr.core.revision import ISRRevision


def assert_revision_immutability_envelope(revision: ISRRevision) -> None:
    """W03 — frozen envelope + content-addressed digest from create-path."""
    cfg = ISRRevision.model_config
    frozen = cfg.get("frozen") if isinstance(cfg, dict) else getattr(cfg, "frozen", False)
    if not frozen:
        raise DigestVerificationError("revision-envelope-not-frozen")
    if len(revision.content_hash) != ISRRevision._EXPECTED_CONTENT_HASH:
        raise DigestVerificationError("revision-content-hash-length-invalid")


def assert_revision_integrity_at_boundary(revision: ISRRevision) -> None:
    """Fail closed if stored digest does not match canonical recomputation."""
    assert_revision_immutability_envelope(revision)
    try:
        verify_revision_content_integrity(revision)
    except DigestVerificationError as exc:
        raise DigestVerificationError(
            "revision-integrity-boundary-failed"
        ) from exc
