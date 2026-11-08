"""F-04 CompilationPlan canonical bytes (ADR-R1-02 Tier B)."""

from __future__ import annotations

import json

from compiler.core.plan import CompilationPlan


def canonical_bytes_f04(plan: CompilationPlan) -> bytes:
    """Deterministic plan serialization for digest and independent verification."""
    payload = plan.model_dump(mode="json")
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
