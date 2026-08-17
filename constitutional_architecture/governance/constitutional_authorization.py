"""R2.10.3-J — ConstitutionalAuthorization: governance-owned, evolution-external.

The CONSTITUTIONAL protection level allows a region to evolve only through an
explicitly authorized constitutional change. This module is the seam that
makes that authorization REAL: the authorization is created only here, in the
governance package, OUTSIDE the evolution loop. Evolution operators can never
import or construct it (enforced by a module-boundary test), and the
protection evaluator receives it as an opaque validated value.

The process being constrained must not control the constraint: if the
ordinary evolution loop could grant its own constitutional authorizations,
CONSTITUTIONAL would be no stronger than PRESERVATION. An authorization is a
REFERENCE to authority, not authority itself — ``anchor_ref`` identifies the
governance evidence (Phase-28 EvidenceSigner style) rather than duplicating
its contents.

``ConstitutionalAuthorizationRegistry`` anchors issued authorizations so the
evaluator can verify an anchor without trusting the caller: an authorization
that was never issued through the governance seam does not verify, and
without a registry no CONSTITUTIONAL change can ever be authorized.
"""
from __future__ import annotations

from dataclasses import dataclass


class ConstitutionalAuthorizationError(ValueError):
    """An authorization violates its governance contract."""


@dataclass(frozen=True)
class ConstitutionalAuthorization:
    """A reference to governance authority for a CONSTITUTIONAL-region change.

    Created only through the governance seam (``ConstitutionalAuthorizationRegistry``),
    anchored to governance evidence. A reference to authority, not authority
    itself — ``anchor_ref`` points at the evidence rather than duplicating it.
    """

    authorization_id: str
    region_ref: str
    subject_refs: tuple[str, ...]
    rationale: str
    authorizer: str
    anchor_ref: str

    def __post_init__(self) -> None:
        if not self.authorization_id:
            raise ConstitutionalAuthorizationError("authorization_id is required")
        if not self.region_ref:
            raise ConstitutionalAuthorizationError("region_ref is required")
        if not self.subject_refs:
            raise ConstitutionalAuthorizationError(
                "subject_refs required: an authorization must authorize something explicit"
            )
        if not self.authorizer:
            raise ConstitutionalAuthorizationError("authorizer is required")
        if not self.anchor_ref:
            raise ConstitutionalAuthorizationError(
                "anchor_ref required: an authorization must reference governance evidence"
            )

    def covers(self, region_ref: str, affected: frozenset[str]) -> bool:
        """Does this authorization cover a specific affected subject set within a region?"""
        return self.region_ref == region_ref and affected <= frozenset(self.subject_refs)


class ConstitutionalAuthorizationRegistry:
    """The governance seam that issues and anchors constitutional authorizations.

    Issue anchors the authorization's anchor_ref in the registry; verification
    is membership-based and chain-anchored (each issued authorization is
    recorded against the previous one's anchor, so the issuance history is
    tamper-evident within the governance package). The evolution package never
    imports this — the evaluator receives the registry (or its verification
    behavior) as an opaque authority.
    """

    def __init__(self) -> None:
        self._authorizations: dict[str, ConstitutionalAuthorization] = {}
        self._chain: list[str] = []

    def issue(
        self,
        *,
        authorization_id: str,
        region_ref: str,
        subject_refs: tuple[str, ...],
        rationale: str,
        authorizer: str,
    ) -> ConstitutionalAuthorization:
        if authorization_id in self._authorizations:
            raise ConstitutionalAuthorizationError(
                f"authorization '{authorization_id}' already issued"
            )
        anchor = self._next_anchor(authorization_id)
        authorization = ConstitutionalAuthorization(
            authorization_id=authorization_id,
            region_ref=region_ref,
            subject_refs=subject_refs,
            rationale=rationale,
            authorizer=authorizer,
            anchor_ref=anchor,
        )
        self._authorizations[authorization_id] = authorization
        self._chain.append(anchor)
        return authorization

    def _next_anchor(self, authorization_id: str) -> str:
        import hashlib

        previous = self._chain[-1] if self._chain else "genesis"
        return hashlib.sha256(
            f"{previous}:{authorization_id}".encode("utf-8")
        ).hexdigest()

    def verifies(self, anchor_ref: str) -> bool:
        """Is this anchor a governance-issued, chain-anchored authorization?"""
        return anchor_ref in self._chain

    def authorization(self, authorization_id: str) -> ConstitutionalAuthorization:
        try:
            return self._authorizations[authorization_id]
        except KeyError:
            raise ConstitutionalAuthorizationError(
                f"authorization '{authorization_id}' not issued"
            ) from None

    @property
    def issued(self) -> tuple[str, ...]:
        return tuple(self._authorizations)

    @property
    def chain_verifies(self) -> bool:
        """Tamper-evidence: every issued authorization is anchored exactly once
        (the issuance chain is a monotone, collision-free sequence)."""
        return len(self._chain) == len(self._authorizations) == len(set(self._chain))