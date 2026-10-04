"""Bounded, evidence-backed root-cause hypotheses and repair candidates."""

from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

from .repository_code_scan import CodeFinding
from .repository_impact_analysis import ImpactAnalysis

@dataclass(frozen=True)
class RootCauseHypothesis:
    hypothesis_id: str
    finding_id: str
    category: str
    explanation: str
    evidence: tuple[str, ...]
    confidence: float

@dataclass(frozen=True)
class RepairCandidate:
    candidate_id: str
    hypothesis_id: str
    strategy: str
    rationale: str
    affected_paths: tuple[str, ...]
    required_verification_paths: tuple[str, ...]
    confidence: float

def derive_root_causes(
    finding: CodeFinding,
    impact: ImpactAnalysis,
) -> tuple[RootCauseHypothesis, ...]:
    evidence=tuple(sorted(set(finding.evidence + (impact.digest,))))
    hypotheses=[]
    if finding.rule=="bare-except":
        hypotheses.append(_hyp(finding,"exception-handling","bare exception may hide unexpected failures",evidence,.70))
    elif finding.rule=="broad-exception":
        hypotheses.append(_hyp(finding,"exception-handling","broad exception handling may mask unrelated failures",evidence,.65))
    elif finding.rule in {"unfinished-marker","stub-pass"}:
        hypotheses.append(_hyp(finding,"incomplete-implementation","unfinished implementation may leave required behavior absent",evidence,.75))
    else:
        hypotheses.append(_hyp(finding,"code-quality","observed structural risk requires targeted investigation",evidence,.40))
    return tuple(hypotheses)

def generate_repair_candidates(
    finding: CodeFinding,
    impact: ImpactAnalysis,
    hypotheses: Iterable[RootCauseHypothesis],
) -> tuple[RepairCandidate, ...]:
    paths=tuple(sorted({impact.source_path, *(n.path for n in impact.affected)}))
    candidates=[]
    for h in hypotheses:
        if h.category=="exception-handling":
            strategies=("narrow-exception-handling","preserve-existing-fallback-with-explicit-errors")
        elif h.category=="incomplete-implementation":
            strategies=("implement-required-behavior","replace-stub-with-verified-path")
        else:
            strategies=("targeted-structural-repair","defer-until-additional-evidence")
        for strategy in strategies:
            cid=sha256(f"{h.hypothesis_id}|{strategy}|{'|'.join(paths)}".encode()).hexdigest()[:20]
            candidates.append(RepairCandidate(cid,h.hypothesis_id,strategy,
                f"Candidate for {h.explanation}",paths,paths,h.confidence))
    return tuple(candidates)

def _hyp(finding,category,explanation,evidence,confidence):
    hid=sha256(f"{finding.finding_id}|{category}|{explanation}".encode()).hexdigest()[:20]
    return RootCauseHypothesis(hid,finding.finding_id,category,explanation,evidence,confidence)
