"""Adversarial review of proposed architectural corrections."""
from __future__ import annotations
from dataclasses import dataclass
from .correction_synthesis import CorrectionCandidate


@dataclass(frozen=True)
class AdversarialFinding:
    finding_id: str
    correction_id: str
    category: str
    severity: str
    claim: str
    verification_obligation: str


@dataclass(frozen=True)
class CorrectionReview:
    correction_id: str
    findings: tuple[AdversarialFinding, ...]
    obligations: tuple[str, ...]
    disposition: str  # candidate-only, challenged, bounded


def review_correction(candidate: CorrectionCandidate) -> CorrectionReview:
    findings: list[AdversarialFinding] = []
    cid = candidate.correction_id

    if candidate.strategy == "strengthen-transition-guards":
        findings.append(AdversarialFinding(
            f"{cid}:liveness", cid, "reliability", "medium",
            "stronger guards may reject valid progress",
            "test valid and retryable paths remain reachable",
        ))
        findings.append(AdversarialFinding(
            f"{cid}:complexity", cid, "maintainability", "low",
            "guard complexity may obscure authorization logic",
            "verify guard semantics are explicit and traceable",
        ))

    elif candidate.strategy == "serialize-conflicting-effects":
        findings.append(AdversarialFinding(
            f"{cid}:throughput", cid, "performance", "medium",
            "serialization may reduce concurrency",
            "measure throughput and contention under representative load",
        ))
        findings.append(AdversarialFinding(
            f"{cid}:deadlock", cid, "reliability", "high",
            "new ordering constraints may introduce deadlock risk",
            "run lock-order and timeout/failure scenarios",
        ))

    elif candidate.strategy == "add-compensation-or-recovery":
        findings.append(AdversarialFinding(
            f"{cid}:compensation", cid, "correctness", "high",
            "compensation may itself create a second effect",
            "verify compensation is authorized, idempotent, and auditable",
        ))
        findings.append(AdversarialFinding(
            f"{cid}:partial", cid, "distributed-systems", "medium",
            "partial compensation may leave inconsistent state",
            "inject failures at each recovery boundary",
        ))

    obligations = tuple(sorted({f.verification_obligation for f in findings}))
    disposition = "challenged" if findings else "candidate-only"
    return CorrectionReview(cid, tuple(findings), obligations, disposition)


def review_candidates(
    candidates: tuple[CorrectionCandidate, ...],
) -> tuple[CorrectionReview, ...]:
    return tuple(review_correction(c) for c in candidates)
