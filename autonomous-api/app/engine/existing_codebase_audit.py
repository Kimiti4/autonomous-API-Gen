"""Deterministic evidence bundle for an existing-codebase audit (Bucket 4.1)."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

from .repository_audit_gate import RepositoryAuditDecision, RepositoryAuditScope, assess_repository_audit
from .repository_code_scan import CodeFinding, RepositoryScan, scan_repository
from .repository_impact_analysis import ImpactAnalysis, analyze_finding_impact
from .repository_root_cause import RepairCandidate, RootCauseHypothesis, derive_root_causes, generate_repair_candidates
from .repository_structure_scan import StructuralScan, analyze_repository_structure


@dataclass(frozen=True)
class FindingAnalysis:
    finding: CodeFinding
    impact: ImpactAnalysis
    hypotheses: tuple[RootCauseHypothesis, ...]
    candidates: tuple[RepairCandidate, ...]


@dataclass(frozen=True)
class ExistingCodebaseAudit:
    scope: RepositoryAuditScope
    audit_decision: RepositoryAuditDecision
    code_scan: RepositoryScan
    structure_scan: StructuralScan
    analyses: tuple[FindingAnalysis, ...]
    digest: str


def audit_existing_codebase(
    files: Iterable[tuple[str, str]],
    *,
    root: str = ".",
    expected_files: int | None = None,
    repair_evidence_complete: bool = False,
) -> ExistingCodebaseAudit:
    ordered = tuple(sorted(files, key=lambda x: x[0]))
    code_scan = scan_repository(ordered, root=root)
    structure_scan = analyze_repository_structure(ordered)
    expected = code_scan.files_scanned if expected_files is None else expected_files
    scope = RepositoryAuditScope(
        expected_files=expected,
        scanned_files=code_scan.files_scanned,
    )
    decision = assess_repository_audit(
        scope,
        findings_count=len(code_scan.findings) + len(structure_scan.findings),
        repair_evidence_complete=repair_evidence_complete,
    )

    analyses = []
    for finding in code_scan.findings:
        impact = analyze_finding_impact(finding.finding_id, finding.path, ordered)
        hypotheses = derive_root_causes(finding, impact)
        candidates = generate_repair_candidates(finding, impact, hypotheses)
        analyses.append(FindingAnalysis(finding, impact, hypotheses, candidates))

    canonical = "|".join((
        code_scan.digest,
        structure_scan.digest,
        str(scope.expected_files),
        str(scope.scanned_files),
        str(decision.may_claim_full_audit),
        str(decision.may_certify_repair),
        "|".join(
            f"{a.finding.finding_id}:{a.impact.digest}:{','.join(c.candidate_id for c in a.candidates)}"
            for a in analyses
        ),
    ))
    return ExistingCodebaseAudit(
        scope=scope,
        audit_decision=decision,
        code_scan=code_scan,
        structure_scan=structure_scan,
        analyses=tuple(analyses),
        digest=sha256(canonical.encode()).hexdigest(),
    )
