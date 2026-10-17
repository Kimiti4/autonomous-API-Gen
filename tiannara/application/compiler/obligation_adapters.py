"""Lossless adapters from both compiler pipelines into the shared obligation contract.

These adapters deliberately do not promote structural success to semantic PASS.
Legacy gate evidence is prose, not a verified evidence artifact; the newer
compiler's success/BundleVerifier result is likewise not behavioral proof.
"""
from __future__ import annotations

from typing import Any

from tiannara.domain.models.compiler_obligation import (
    Applicability,
    CompilerObligationRecord,
    Disposition,
    EnforcementPoint,
    Strength,
)


def _source_hash(source_graph_hash: str) -> str:
    """Validate source identity before using it as an obligation binding."""
    if len(source_graph_hash) != 64:
        raise ValueError("source_graph_hash must be a lowercase SHA-256 digest")
    try:
        bytes.fromhex(source_graph_hash)
    except ValueError as exc:
        raise ValueError("source_graph_hash must be a lowercase SHA-256 digest") from exc
    if source_graph_hash.lower() != source_graph_hash:
        raise ValueError("source_graph_hash must be lowercase")
    return source_graph_hash


def adapt_legacy_gate(
    gate: Any,
    *,
    source_graph_id: str,
    source_graph_hash: str,
    consumer_binding: str | None = None,
) -> CompilerObligationRecord:
    """Map a legacy integrity gate without inventing evidence artifacts.

    A failed gate maps to FAIL. A held gate maps only to UNKNOWN until its
    evidence text is independently materialized, hashed, and bound to a run.
    Missing consumer identity is surfaced as BLOCKED_NO_CONSUMER.
    """
    gate_id = str(gate.gate_id)
    has_consumer = bool(consumer_binding and consumer_binding.strip())
    if not has_consumer:
        disposition = Disposition.BLOCKED_NO_CONSUMER
    elif not gate.held:
        disposition = Disposition.FAIL
    else:
        disposition = Disposition.UNKNOWN

    return CompilerObligationRecord(
        schema_version="1.0",
        obligation_id=f"legacy_integrity.{gate_id}",
        source_graph_id=source_graph_id,
        source_graph_hash=_source_hash(source_graph_hash),
        domain="compiler_integrity",
        statement=f"Legacy compilation integrity gate {gate_id} must hold.",
        applicability=Applicability.REQUIRED,
        required_strength=Strength.MUST,
        consumer_binding=consumer_binding or "",
        enforcement_points=(
            (EnforcementPoint(kind="legacy_integrity_gate", locator=gate_id),)
            if has_consumer else ()
        ),
        disposition=disposition,
        limitations=(
            "Legacy GateResult.evidence is descriptive text and is not independently "
            "verified, hashed, or bound to an execution environment.",
        ),
    )


def adapt_project_outcome(
    outcome: Any,
    *,
    source_graph_id: str,
    source_graph_hash: str,
) -> CompilerObligationRecord:
    """Map the newer generation outcome conservatively into the shared contract.

    Backend exceptions and failed static verification remain FAIL. A successful
    generate() call or passing structural verifier remains UNKNOWN because this
    path does not itself prove domain behavior or runtime enforcement.
    """
    source_hash = _source_hash(source_graph_hash)
    planned = getattr(outcome, "planned", None)
    backend_id = getattr(planned, "backend_id", None)
    status = getattr(outcome, "status", "unknown")
    verification = getattr(outcome, "verification_report", None)
    verification_reason = str(getattr(outcome, "verification_reason", ""))

    if not backend_id:
        disposition = Disposition.BLOCKED_NO_CONSUMER
        consumer = ""
        enforcement_points = ()
    else:
        consumer = str(backend_id)
        enforcement_points = (
            EnforcementPoint(kind="backend_generation", locator=consumer),
        )
        if status != "success" or (verification is not None and not verification.ok):
            disposition = Disposition.FAIL
        else:
            disposition = Disposition.UNKNOWN

    limitations = [
        "Backend generation success is not semantic or behavioral certification.",
        "BundleVerifier checks structure, syntax, and dependency direction; it does "
        "not independently execute domain acceptance scenarios.",
    ]
    if verification_reason:
        limitations.append(f"verification_reason: {verification_reason[:1000]}")
    error = getattr(outcome, "error", None)
    if error:
        limitations.append(f"generation_error: {str(error)[:1000]}")

    return CompilerObligationRecord(
        schema_version="1.0",
        obligation_id=f"cap_c.backend_generation.{backend_id or 'unbound'}",
        source_graph_id=source_graph_id,
        source_graph_hash=source_hash,
        domain="compiler_generation",
        statement="The selected backend must generate an artifact that preserves the required source semantics.",
        applicability=Applicability.REQUIRED,
        required_strength=Strength.MUST,
        consumer_binding=consumer,
        enforcement_points=enforcement_points,
        disposition=disposition,
        limitations=tuple(limitations),
    )
