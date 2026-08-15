"""
Phase 28 — Cryptographic signing of AuditEvidenceISR.

Hash-chaining already gives *tamper evidence* (reordering/splicing is detectable
via ``verify_chain``). This module adds *authenticity* and *integrity*: each
evidence record is signed over its immutable, chain-linked content so that a
specific actor is bound to a specific record and its position in the chain.

Security precision
------------------
``HmacEvidenceSigner`` is HMAC-SHA256 (symmetric). It provides authenticity and
integrity and protects against *tampering*, but is **not** non-repudiation: any
holder of the symmetric key could have produced the MAC. For single-authority
attestation within this platform that is sufficient; for third-party
non-repudiation an asymmetric signer (e.g. Ed25519) satisfying the
``EvidenceSigner`` protocol can be dropped in via ``new_evidence_recorder``
without changing any caller.

Design notes
------------
* No signing key is ever hard-coded. Keys are injected (constructor or
  ``AUDIT_EVIDENCE_SIGNING_KEY`` env var); in production this comes from a
  secrets manager / KMS.
* The signed domain deliberately excludes ``signature`` and ``signer_id``
  themselves (otherwise the computation would be circular) and *includes*
  ``chain_link``. Signature verification therefore catches chain splicing /
   link removal independently of the hash-chain check.
* Config-gated and additive: with no key configured, ``new_evidence_recorder``
  returns the plain ``AuditEvidenceRecorder`` (unsigned) and emits an
  observable warning; existing unsigned records remain valid (``signature=None``).
"""

from __future__ import annotations

import hashlib
import hmac
import os
import warnings
from datetime import datetime
from typing import Protocol, runtime_checkable

from constitutional_architecture.governance.schemas import AuditEvidenceISR, canonical_json
from constitutional_architecture.governance.audit import (
    AuditEvidenceRecorder,
    EvidenceLedger,
)

AUDIT_EVIDENCE_SIGNING_KEY_ENV = "AUDIT_EVIDENCE_SIGNING_KEY"


@runtime_checkable
class EvidenceSigner(Protocol):
    """A cryptographic signer for audit evidence.

    Implementations must be deterministic: for a given payload, ``sign`` must
    return a stable signature and ``verify`` must accept it. Keys are injected
    by the caller, never embedded in source.
    """

    def sign(self, payload: dict) -> str: ...

    def verify(self, payload: dict, signature: str) -> bool: ...


class HmacEvidenceSigner(EvidenceSigner):
    """HMAC-SHA256 signer (RFC 2104). Symmetric attestation of authenticity."""

    def __init__(self, key: bytes | str, *, encoding: str = "utf-8") -> None:
        if isinstance(key, str):
            key = key.encode(encoding)
        self._key = key

    @staticmethod
    def _canonical(payload: dict) -> bytes:
        # Reuses the platform canonicalization (schemas.canonical_json) so the
        # signature domain is byte-identical to content_hash() / IS-R hashing.
        return canonical_json(payload).encode("utf-8")

    def sign(self, payload: dict) -> str:
        return hmac.new(self._key, self._canonical(payload), hashlib.sha256).hexdigest()

    def verify(self, payload: dict, signature: str) -> bool:
        expected = self.sign(payload)
        return hmac.compare_digest(expected, signature)


def _signing_domain(evidence: AuditEvidenceISR) -> dict:
    """Immutable content covered by the signature (excludes signature/signer_id)."""
    return {
        "evidence_id": evidence.evidence_id,
        "recorded_at": evidence.recorded_at,
        "actor": evidence.actor,
        "event_kind": evidence.event_kind,
        "subject_ref": evidence.subject_ref,
        "payload_hash": evidence.payload_hash,
        "chain_link": evidence.chain_link,
    }


def sign_evidence(
    evidence: AuditEvidenceISR, signer: EvidenceSigner, signer_id: str
) -> AuditEvidenceISR:
    """Return a copy of ``evidence`` carrying a signature from ``signer``.

    The returned copy is otherwise identical; ``payload_hash`` and
    ``chain_link`` are unchanged so the existing hash-chain stays intact.
    """
    signature = signer.sign(_signing_domain(evidence))
    return evidence.model_copy(update={"signature": signature, "signer_id": signer_id})


def verify_evidence_signature(
    evidence: AuditEvidenceISR, signer: EvidenceSigner
) -> bool:
    """Verify an evidence record. ``None`` => unsigned => returns ``True``
    (backward-compatible pass for pre-existing records). Signed records are
    verified against the signer's key; any tamper with the chained content
    (including the chain link itself) fails verification.
    """
    if evidence.signature is None:
        return True
    if evidence.signer_id is None:
        return False
    return signer.verify(_signing_domain(evidence), evidence.signature)


class SignedAuditEvidenceRecorder:
    """Opt-in signing wrapper around :class:`AuditEvidenceRecorder`.

    Satisfies :class:`EvidenceLedger`. Records created through ``record`` are
    automatically signed over their full chain-linked content. ``verify_chain``
    delegates to the underlying ledger; ``verify_signatures`` checks every
    signature and that no signed record has been tampered.
    """

    def __init__(
        self,
        signer: EvidenceSigner,
        signer_id: str,
        *,
        delegate: AuditEvidenceRecorder | None = None,
    ) -> None:
        self._signer = signer
        self._signer_id = signer_id
        self._delegate = delegate if delegate is not None else AuditEvidenceRecorder()
        self._signed: list[AuditEvidenceISR] = []

    def record(
        self,
        *,
        actor: str,
        event_kind: str,
        subject_ref: str,
        payload: dict,
        recorded_at: datetime,
    ) -> AuditEvidenceISR:
        evidence = self._delegate.record(
            actor=actor,
            event_kind=event_kind,
            subject_ref=subject_ref,
            payload=payload,
            recorded_at=recorded_at,
        )
        signed = sign_evidence(evidence, self._signer, self._signer_id)
        self._signed.append(signed)
        return signed

    @property
    def entries(self) -> tuple[AuditEvidenceISR, ...]:
        return tuple(self._signed)

    def verify_chain(self) -> bool:
        return self._delegate.verify_chain()

    def verify_signatures(self) -> bool:
        if not all(verify_evidence_signature(ev, self._signer) for ev in self._signed):
            return False
        return len(self._signed) == len(self._delegate.entries)


def new_evidence_recorder(
    *,
    key: str | bytes | None = None,
    key_env: str = AUDIT_EVIDENCE_SIGNING_KEY_ENV,
    signer_id: str = "governance_kernel",
) -> EvidenceLedger:
    """Composition-root factory: choose the evidence ledger by configuration.

    * If a key is supplied (or present via ``key_env``), returns a
      :class:`SignedAuditEvidenceRecorder` (HMAC-SHA256) so the kernel evidence
      path produces signed, authenticity-attested records.
    * If no key is configured, returns the plain :class:`AuditEvidenceRecorder`
      (unsigned) **and emits a warning** — "unsigned" must never be silent, per
      the platform's Observability-by-Design principle.

    This is the single seam where signing is wired into the live path; the
    kernel and dashboard never choose implementations directly.
    """
    if key is None:
        key = os.getenv(key_env)
    if key:
        return SignedAuditEvidenceRecorder(HmacEvidenceSigner(key), signer_id)
    warnings.warn(
        f"{key_env} is not set; audit evidence will be recorded without a "
        f"cryptographic signature (no authenticity attestation). Supply a "
        f"secrets-manager-provisioned key in production.",
        stacklevel=2,
    )
    return AuditEvidenceRecorder()
