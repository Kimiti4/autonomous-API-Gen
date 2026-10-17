"""Filesystem adapter for trusted, auditable compiler evidence retrieval.

The evidence root and audit callback are trusted startup dependencies. Each
reference resolves to a binary evidence object and a signed attestation JSON
sidecar under that root. OS permissions must restrict writes to trusted runners.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable
from urllib.parse import urlsplit

from tiannara.application.compiler.trusted_obligation_evidence import (
    RetrievedTrustedEvidence,
    TrustedEvidenceAttestation,
)


@dataclass(frozen=True)
class EvidenceReadAuditReceipt:
    """Store-side receipt returned only after the access audit is persisted."""

    audit_event_id: str
    authorized_principal: str
    retrieved_at: str

    def __post_init__(self) -> None:
        for field_name in ("audit_event_id", "authorized_principal", "retrieved_at"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"audit receipt {field_name} must be non-empty")


class FileSystemTrustedEvidenceStore:
    """Read evidence/attestation pairs beneath a configured root, fail closed."""

    def __init__(
        self,
        root: str | Path,
        *,
        audit_read: Callable[[str, str, str, str], EvidenceReadAuditReceipt],
    ) -> None:
        self._root = Path(root).resolve()
        self._audit_read = audit_read
        if not self._root.is_dir():
            raise ValueError("trusted evidence root must be an existing directory")

    def read(self, evidence_ref: str) -> RetrievedTrustedEvidence | None:
        """Read one evidence object and require a complete store-side receipt.

        The audit callback receives (reference, outcome, payload SHA-256,
        attestation ID) and must return an EvidenceReadAuditReceipt only
        after its audit event is durably recorded. Invalid and missing reads
        are audited too. Audit failure prevents a usable retrieval result.
        """
        payload_hash = ""
        attestation_id = ""
        outcome = "INVALID_REFERENCE"
        payload: bytes | None = None
        attestation: TrustedEvidenceAttestation | None = None
        read_error: Exception | None = None

        try:
            base = self._resolve_reference(evidence_ref)
        except Exception as exc:
            read_error = exc
        else:
            try:
                payload_path = base.with_suffix(".bin")
                attestation_path = base.with_suffix(".attestation.json")
                if not payload_path.is_file() or not attestation_path.is_file():
                    outcome = "NOT_FOUND"
                else:
                    payload = payload_path.read_bytes()
                    attestation = TrustedEvidenceAttestation.model_validate_json(
                        attestation_path.read_bytes()
                    )
                    payload_hash = hashlib.sha256(payload).hexdigest()
                    attestation_id = attestation.attestation_id
                    outcome = "READ"
            except Exception as exc:
                outcome = "READ_ERROR"
                read_error = exc

        # Audit every attempt before returning evidence or surfacing a read
        # error. The receipt is the authoritative source of retrieval metadata;
        # the store must not invent event IDs, principals, or timestamps.
        receipt = self._audit_read(
            evidence_ref, outcome, payload_hash, attestation_id
        )
        if not isinstance(receipt, EvidenceReadAuditReceipt):
            raise ValueError(
                "audit callback must return a complete EvidenceReadAuditReceipt"
            )
        if read_error is not None:
            raise read_error
        if outcome != "READ":
            return None
        if payload is None or attestation is None:
            raise RuntimeError("trusted evidence read reached an invalid internal state")

        return RetrievedTrustedEvidence(
            payload=payload,
            attestation=attestation,
            audit_event_id=receipt.audit_event_id,
            authorized_principal=receipt.authorized_principal,
            retrieved_at=receipt.retrieved_at,
        )

    def _resolve_reference(self, evidence_ref: str) -> Path:
        parsed = urlsplit(evidence_ref)
        if parsed.scheme != "evidence" or not parsed.netloc:
            raise ValueError("evidence reference must use evidence://namespace/path")
        raw_path = parsed.path.lstrip("/")
        relative = PurePosixPath(parsed.netloc, raw_path)
        if not relative.parts or any(
            part in ("", ".", "..") for part in relative.parts
        ):
            raise ValueError("evidence reference contains an invalid path")
        if parsed.query or parsed.fragment or "\\" in evidence_ref:
            raise ValueError("evidence reference contains unsupported path syntax")
        base = (self._root / Path(*relative.parts)).resolve()
        if not base.is_relative_to(self._root):
            raise ValueError("evidence reference escapes the trusted evidence root")
        return base
