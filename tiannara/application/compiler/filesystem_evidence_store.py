"""Filesystem adapter for trusted, auditable compiler evidence retrieval.

The evidence root and audit callback are trusted startup dependencies. Each
reference resolves to a binary evidence object and a signed attestation JSON
sidecar under that root. OS permissions must restrict writes to trusted runners.
"""
from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
from typing import Callable
from urllib.parse import urlsplit

from tiannara.application.compiler.trusted_obligation_evidence import (
    RetrievedTrustedEvidence,
    TrustedEvidenceAttestation,
)


class FileSystemTrustedEvidenceStore:
    """Read evidence/attestation pairs beneath a configured root, fail closed."""

    def __init__(
        self,
        root: str | Path,
        *,
        audit_read: Callable[[str, str, str, str], None],
    ) -> None:
        self._root = Path(root).resolve()
        self._audit_read = audit_read
        if not self._root.is_dir():
            raise ValueError("trusted evidence root must be an existing directory")

    def read(self, evidence_ref: str) -> RetrievedTrustedEvidence | None:
        """Read one evidence://namespace/path object and audit the attempt.

        The audit callback receives (reference, outcome, payload SHA-256,
        attestation ID). If auditing fails, retrieval fails closed.
        """
        payload_hash = ""
        attestation_id = ""
        outcome = "INVALID_REFERENCE"
        try:
            base = self._resolve_reference(evidence_ref)
            payload_path = base.with_suffix(".bin")
            attestation_path = base.with_suffix(".attestation.json")
            if not payload_path.is_file() or not attestation_path.is_file():
                outcome = "NOT_FOUND"
                return None

            payload = payload_path.read_bytes()
            attestation = TrustedEvidenceAttestation.model_validate_json(
                attestation_path.read_bytes()
            )
            payload_hash = hashlib.sha256(payload).hexdigest()
            attestation_id = attestation.attestation_id
            outcome = "READ"
            return RetrievedTrustedEvidence(payload=payload, attestation=attestation)
        finally:
            # Even invalid/missing reads are audited. Failure to append audit
            # evidence propagates and prevents a usable retrieval result.
            self._audit_read(
                evidence_ref, outcome, payload_hash, attestation_id
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
