"""Verify a reviewer-attested TaskFlow semantic ledger.

The HMAC key must be provisioned outside the repository (for example by a
protected CI secret or local secret manager). A signature authenticates the
reviewer's attestation and binds it to exact snapshot and graph hashes; it does
not replace review quality or runtime verification.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Mapping

from tiannara.domain.models.semantic_resolution import (
    SemanticResolutionRecord,
    require_taskflow_semantics,
)

ENVELOPE_SCHEMA = "tiannara.taskflow.trusted-resolution-envelope.v1"


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def signed_payload(envelope: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in envelope.items() if key != "signature_hmac_sha256"}


def verify_trusted_resolution_envelope(
    *,
    record: SemanticResolutionRecord,
    graph,
    problem_bytes: bytes,
    acceptance_bytes: bytes,
    envelope: Mapping[str, Any] | None,
    trusted_key: bytes | None,
) -> tuple[bool, tuple[str, ...]]:
    """Return whether a configured trusted attestation matches all current inputs."""
    blockers: list[str] = []
    if envelope is None:
        blockers.append("No trusted resolution envelope was supplied.")
    if not trusted_key:
        blockers.append("No out-of-repository trusted evidence key is configured.")
    if envelope is None or not trusted_key:
        return False, tuple(blockers)

    if envelope.get("schema") != ENVELOPE_SCHEMA:
        blockers.append("Trusted resolution envelope schema is missing or unsupported.")
    if not envelope.get("signer_id") or not isinstance(envelope.get("signer_id"), str):
        blockers.append("Trusted resolution envelope must identify its reviewer/signer.")
    expected = {
        "graph_id": graph.graph_id,
        "graph_hash": graph.content_hash(),
        "problem_sha256": sha256(problem_bytes),
        "acceptance_sha256": sha256(acceptance_bytes),
        "resolution_record_sha256": sha256(canonical_json(record.model_dump(mode="json"))),
    }
    for field, value in expected.items():
        if envelope.get(field) != value:
            blockers.append(f"Trusted resolution envelope {field} does not match current inputs.")

    signature = envelope.get("signature_hmac_sha256")
    if not isinstance(signature, str) or len(signature) != 64:
        blockers.append("Trusted resolution envelope has no validly shaped HMAC-SHA256 signature.")
    else:
        expected_signature = hmac.new(trusted_key, canonical_json(signed_payload(envelope)), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            blockers.append("Trusted resolution envelope signature verification failed.")

    try:
        require_taskflow_semantics(graph, record)
    except (ValueError, TypeError) as exc:
        blockers.append(f"Semantic ledger failed authoritative contract validation: {exc}")

    return not blockers, tuple(blockers)


def create_envelope_for_signing(
    *,
    record: SemanticResolutionRecord,
    graph,
    problem_bytes: bytes,
    acceptance_bytes: bytes,
    signer_id: str,
    trusted_key: bytes,
) -> dict[str, str]:
    """Create a locally signed envelope for a trusted reviewer workflow.

    Do not call this automatically during generation: doing so would let the
    generator approve its own semantic assumptions.
    """
    if not signer_id.strip():
        raise ValueError("signer_id must be non-empty")
    require_taskflow_semantics(graph, record)
    payload = {
        "schema": ENVELOPE_SCHEMA,
        "signer_id": signer_id,
        "graph_id": graph.graph_id,
        "graph_hash": graph.content_hash(),
        "problem_sha256": sha256(problem_bytes),
        "acceptance_sha256": sha256(acceptance_bytes),
        "resolution_record_sha256": sha256(canonical_json(record.model_dump(mode="json"))),
    }
    payload["signature_hmac_sha256"] = hmac.new(trusted_key, canonical_json(payload), hashlib.sha256).hexdigest()
    return payload
