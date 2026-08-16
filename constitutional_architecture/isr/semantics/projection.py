"""Semantic architectural projection — single source of truth for ISR identity.

Computes a canonical, deterministic projection of the ISR's architectural
payload (the ``system`` field), EXCLUDING lineage (version, provenance) and the
private hash cache. Deliberately has NO default=str fallback: unhandled types
raise, so representation differences are canonicalized explicitly, never hidden
(the anti-pattern present in ``ISRSerializer._json_default``).

Lives in constitutional_architecture; imports nothing from tiannara.
``identity.FSMSemanticProjector`` (tiannara) delegates here.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any

# ISR field classification: architectural payload vs lineage/runtime.
ISR_ARCHITECTURAL_FIELDS = ("system",)
ISR_EXCLUDED_FIELDS = ("version", "provenance", "_content_hash")


class CanonicalizationError(TypeError):
    """No canonical form for a value. Deliberate: no default=str fallback."""


def _is_empty(value: Any) -> bool:
    """R2.10.2 (Option A): empty carriers are identity-neutral.

    None, the empty string, and empty containers carry no architecture, so
    they are omitted from the canonical projection. This makes adding an
    *optional* primitive to the ISR schema hash-stable: an ISR whose new
    primitive is empty hashes identically to an ISR without the field.
    Booleans, zero, and non-empty strings remain meaningful and are kept.
    """
    if value is None or value == "":
        return True
    if isinstance(value, (list, tuple, dict, set, frozenset)):
        return not value
    return False


def canonical_form(value: Any) -> Any:
    """Recursively convert a value to a canonical, JSON-serializable form.

    Empty carriers (None, "", [], (), {}, empty sets) are omitted inside
    containers (R2.10.2 Option A) so optional schema extensions are
    hash-neutral. Raises CanonicalizationError on unhandled types instead of
    str()-ing them, so hidden representation differences surface as failures,
    not silent drift.
    """
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, Enum):
        return {"__enum__": value.value}
    if isinstance(value, datetime):
        return {"__datetime__": value.isoformat()}
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            canonical = canonical_form(v)
            if not _is_empty(canonical):
                out[str(k)] = canonical
        return out
    if isinstance(value, (list, tuple)):
        out = []
        for v in value:
            canonical = canonical_form(v)
            if not _is_empty(canonical):
                out.append(canonical)
        return out
    if isinstance(value, (set, frozenset)):
        return [json.loads(f) for f in sorted(canonicalize(v) for v in value)]
    if is_dataclass(value) and not isinstance(value, type):
        return canonical_form(asdict(value))
    raise CanonicalizationError(f"no canonical form for {type(value).__name__}")


def canonicalize(value: Any) -> str:
    return json.dumps(canonical_form(value), sort_keys=True, separators=(",", ":"))


def project_semantic_architecture(isr: Any) -> Any:
    """Project the ISR to its architectural payload only.

    Excludes version, provenance, and the hash cache by projecting only
    ``system``. The full System/Module tree (entities, services, workflows,
    policies, interfaces, events, deployment, metadata, constraints) is
    canonicalized recursively, so the result is sensitive to every
    architectural change — preserving governance change-detection.
    """
    system = getattr(isr, "system", None)
    return canonical_form(system)


def semantic_content_hash(isr: Any) -> str:
    """H(canonical(architectural payload)).

    Stable across runs (volatile provenance/version excluded) AND sensitive to
    all architectural changes (full projection). This is the post-migration
    ``ISR.content_hash``.
    """
    return hashlib.sha256(
        canonicalize(project_semantic_architecture(isr)).encode("utf-8")
    ).hexdigest()
