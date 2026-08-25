"""GAP-06/GAP-09 acceptance: taxonomy totality + envelope validity."""
from __future__ import annotations

import typing

from app.core.contracts.errors import (
    ERROR_TAXONOMY,
    ErrorCode,
    RecoveryGuidance,
    build_error_envelope,
)


def test_every_code_has_exactly_one_category_and_severity():
    for code, (cat, sev) in ERROR_TAXONOMY.items():
        assert cat in {
            "client", "platform", "contract",
            "synchronization", "security", "resource",
        }
        assert sev in {"info", "warning", "error", "fatal"}


def test_taxonomy_is_total():
    """New codes cannot slip in unclassified."""
    allowed = set(typing.get_args(ErrorCode))
    assert set(ERROR_TAXONOMY) == allowed


def test_build_error_envelope_produces_valid_envelope_for_every_code():
    for code in ERROR_TAXONOMY:
        envelope = build_error_envelope(
            code=code,
            message="test message",
            source_revision="test-rev",
            source_subsystem="test",
            recovery=RecoveryGuidance(action="none", message="no recovery"),
        )
        category, severity = ERROR_TAXONOMY[code]
        assert envelope.error.category == category
        assert envelope.error.severity == severity
        assert len(envelope.provenance.contentHash) == 64
        # traceId is correlation-only; absent here and never carries internals.
        assert envelope.error.traceId is None


def test_unknown_code_is_rejected():
    import pytest

    with pytest.raises(ValueError):
        build_error_envelope(
            code="NOT_A_REAL_CODE",
            message="x",
            source_revision="r",
            source_subsystem="s",
            recovery=RecoveryGuidance(action="none", message="m"),
        )