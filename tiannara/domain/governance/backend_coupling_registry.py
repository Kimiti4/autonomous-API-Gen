"""Backend-coupling registry — frozen boundary for meta-compiler debt.

Cap-A's pattern applied to the second coupling disease: meta-compilers
selecting behavior by COMPILER BACKEND ID instead of by capability.

Bidirectionally enforced by tests/test_backend_coupling_guard.py:
  * unregistered coupling fails the build (debt cannot grow);
  * stale entries fail the build (removals are recorded).

The registry is the Phase-15 remediation checklist. It can only shrink.
"""

from __future__ import annotations

import enum

from pydantic import BaseModel


class BackendCouplingCategory(str, enum.Enum):
    BACKEND_ID_STRING = "backend_id_string"


class BackendCouplingEntry(BaseModel):
    file_path: str        # repo-relative path of the offending module
    matched_token: str    # exact backend identifier found
    reason: str
    remediation: str


#: Wire these to the actual meta-compiler locations BEFORE first run.
#: The guard FAILS on missing roots — silently passing is forbidden.
META_COMPILER_ROOTS: tuple[str, ...] = (
    "tiannara/application/cicd",
)

#: Known compiler backend identifiers — the denylist for meta-compiler sources.
#: Cap-C formalizes backend registration; until then this tuple is the single
#: source of truth for ids that must not leak into meta-compiler selection
#: logic.
KNOWN_BACKEND_IDS: tuple[str, ...] = (
    "fastapi_hexagonal",
    "minimal-container",
)

LEGACY_BACKEND_COUPLING_REGISTRY: tuple[BackendCouplingEntry, ...] = (
    # First guard run enumerates existing debt deterministically; paste the
    # reported (file_path, matched_token) entries here with remediation
    # notes — the same one-iteration procedure Cap-A used.
)
