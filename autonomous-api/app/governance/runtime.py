"""Live governance composition seam.

The domain subsystem is storage-agnostic; this module provides the
application-level dependency injection point used by routes and promotion
checks. It deliberately fails closed when the composition root has not
configured governance.
"""
from __future__ import annotations

_governance = None


def configure_governance(governance) -> None:
    global _governance
    _governance = governance


def get_governance():
    if _governance is None:
        raise RuntimeError("governance subsystem is not configured")
    return _governance
