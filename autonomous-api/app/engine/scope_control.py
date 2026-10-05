"""Bucket 3.11 — governed scope control and anti-hallucination work admission.

Scope classification is deliberately separate from execution. It determines
whether proposed work is required, necessary support, or advisory, and rejects
untraced work unless explicitly authorized by the governing authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Literal

ScopeClass = Literal["required", "necessary_support", "advisory", "rejected"]
Authority = Literal["authoritative", "derived", "advisory"]

_VALID_CLASSES = {"required", "necessary_support", "advisory", "rejected"}
_VALID_AUTHORITIES = {"authoritative", "derived", "advisory"}


@dataclass(frozen=True)
class WorkProposal:
    proposal_id: str
    description: str
    obligation_ids: tuple[str, ...] = ()
    dependency_ids: tuple[str, ...] = ()
    authority: Authority = "derived"
    explicitly_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.proposal_id.strip() or not self.description.strip():
            raise ValueError("proposal-id-and-description-required")
        if self.authority not in _VALID_AUTHORITIES:
            raise ValueError("invalid-authority")


@dataclass(frozen=True)
class ScopeDecision:
    proposal_id: str
    classification: ScopeClass
    reasons: tuple[str, ...]
    executable: bool
    digest: str


class ScopeControlEngine:
    """Classify proposed work without performing or certifying the work."""

    def __init__(
        self,
        *,
        project_id: str,
        authoritative_obligation_ids: set[str] | frozenset[str],
        known_obligation_ids: set[str] | frozenset[str] = frozenset(),
    ) -> None:
        if not project_id.strip():
            raise ValueError("project-id-required")
        self.project_id = project_id
        self.authoritative = frozenset(authoritative_obligation_ids)
        self.known = frozenset(known_obligation_ids) | self.authoritative

    def decide(self, proposal: WorkProposal) -> ScopeDecision:
        reasons: list[str] = []

        unknown = sorted(set(proposal.obligation_ids) - self.known)
        if unknown:
            reasons.append("unknown-obligation-reference")

        if proposal.authority == "authoritative":
            if proposal.obligation_ids and set(proposal.obligation_ids) & self.authoritative:
                classification: ScopeClass = "required"
                reasons.append("traced-to-authoritative-obligation")
            elif proposal.explicitly_authorized:
                classification = "required"
                reasons.append("explicit-human-authorization")
            else:
                classification = "rejected"
                reasons.append("authoritative-claim-without-governed-trace")
        elif proposal.obligation_ids and set(proposal.obligation_ids) & self.authoritative:
            classification = "necessary_support"
            reasons.append("supports-authoritative-obligation")
        elif proposal.dependency_ids:
            classification = "necessary_support"
            reasons.append("declared-support-dependency")
        elif proposal.authority == "advisory":
            classification = "advisory"
            reasons.append("advisory-only")
        else:
            classification = "rejected"
            reasons.append("no-governed-scope")

        if unknown:
            classification = "rejected"
            reasons.append("fail-closed-on-unknown-scope")

        executable = classification in {"required", "necessary_support"}

        payload = {
            "schema_version": "esap.scope-control.v1",
            "project_id": self.project_id,
            "proposal_id": proposal.proposal_id,
            "classification": classification,
            "reasons": tuple(reasons),
            "executable": executable,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return ScopeDecision(
            proposal_id=proposal.proposal_id,
            classification=classification,
            reasons=tuple(reasons),
            executable=executable,
            digest=digest,
        )
