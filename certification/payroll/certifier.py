"""Fail-closed payroll certification gate.

This module does not calculate payroll or supply statutory values. It decides
whether a particular generated candidate has the required source coverage,
behavioral contracts, backend support, statutory source evidence, independent
oracles, frontend execution evidence, and runtime evidence to be considered
certified.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
import re
from typing import Mapping, Sequence

from compiler.core.capabilities import (
    BackendCapabilities,
    SemanticFeature,
    UnsupportedSemanticsError,
    assert_plan_supported,
    required_features,
)
from compiler.core.plan import CompilationPlan
from isr.core.graph import ISRGraph, NodeType
from isr.core.revision import ISRRevision
from reqgraph.core.graph import Priority, RequirementGraph


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
PAYROLL_BEHAVIORAL_FEATURES = frozenset({
    SemanticFeature.TYPED_FIELDS,
    SemanticFeature.FIELD_CONSTRAINTS,
    SemanticFeature.EXPRESSIONS,
    SemanticFeature.BUSINESS_RULES,
    SemanticFeature.STATE_TRANSITIONS,
    SemanticFeature.API_CONTRACTS,
    SemanticFeature.AUTHORIZATION_POLICIES,
    SemanticFeature.EFFECT_SEMANTICS,
    SemanticFeature.INVARIANTS,
    SemanticFeature.TYPED_EVENTS,
})


@dataclass(frozen=True)
class StatutoryEvidence:
    scheme: str
    source_ref: str
    source_sha256: str
    effective_from: str
    effective_to: str | None
    verified_by: str
    candidate_sha256: str
    test_cases: int
    passed_cases: int
    failed_cases: int


@dataclass(frozen=True)
class IndependentOracleEvidence:
    category: str
    source_requirement_id: str
    source_ref: str
    source_sha256: str
    candidate_sha256: str
    independently_authored_by: str
    test_cases: int
    passed_cases: int
    failed_cases: int


@dataclass(frozen=True)
class FrontendRunEvidence:
    candidate_sha256: str
    artifact_sha256: str
    build_log_sha256: str
    unit_log_sha256: str
    e2e_log_sha256: str
    workflow_run_id: str
    source_commit: str
    build_passed: bool
    unit_tests_passed: bool
    e2e_passed: bool


@dataclass(frozen=True)
class BackendRuntimeEvidence:
    backend_id: str
    candidate_sha256: str
    workflow_run_id: str
    source_commit: str
    trial_count: int
    pass_count: int
    build_passed: bool
    tests_passed: bool
    independent_verification_passed: bool
    health_passed: bool
    cleanup_passed: bool
    ledger_chain_valid: bool


@dataclass(frozen=True)
class PayrollCertificationReport:
    verdict: str
    candidate_sha256: str
    checks: tuple[str, ...]
    findings: tuple[str, ...]

    @property
    def certified(self) -> bool:
        return self.verdict == "CERTIFIED"

    def to_dict(self) -> dict[str, object]:
        return {
            "verdict": self.verdict,
            "certified": self.certified,
            "candidate_sha256": self.candidate_sha256,
            "checks": list(self.checks),
            "findings": list(self.findings),
        }


def _valid_hash(value: str) -> bool:
    return bool(_SHA256.fullmatch(value))


def _iso_date(value: str, label: str, findings: list[str]) -> date | None:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        findings.append(f"{label} is not a valid ISO date")
        return None


def _require_behavioral_completeness(plan: CompilationPlan, findings: list[str]) -> None:
    if not any(model.behavior and model.behavior.fields for model in plan.data_models):
        findings.append("ISR-to-plan has no typed data-model fields")
    if not any(service.behavior and service.behavior.rules for service in plan.services):
        findings.append("ISR-to-plan has no executable business rules")
    if not any(service.behavior and service.behavior.transitions for service in plan.services):
        findings.append("ISR-to-plan has no state-transition contracts")
    if not any(api.behavior for api in plan.apis):
        findings.append("ISR-to-plan has no API operation contracts")
    if not any(policy.behavior and policy.behavior.rules for policy in plan.security):
        findings.append("ISR-to-plan has no explicit authorization rules")
    if not any(effect.behavior for effect in plan.effects):
        findings.append("ISR-to-plan has no declared effect contract")
    if not any(invariant.behavior for invariant in plan.invariants):
        findings.append("ISR-to-plan has no explicit invariants")
    if not any(event.behavior and event.behavior.fields for event in plan.events):
        findings.append("ISR-to-plan has no typed event contract")
    missing = sorted(feature.value for feature in PAYROLL_BEHAVIORAL_FEATURES - required_features(plan))
    if missing:
        findings.append("payroll behavioral plan is missing required features: " + ", ".join(missing))


def derive_required_statutory_schemes(requirement_graph: RequirementGraph) -> frozenset[str]:
    """Derive statutory schemes from reviewed TOR requirement text, not caller defaults."""
    schemes: set[str] = set()
    for node in requirement_graph.nodes.values():
        text = node.statement.lower()
        if "income tax" in text or "paye" in text:
            schemes.add("income_tax")
        if "social security" in text or "nssf" in text:
            schemes.add("social_security")
        if "pension" in text:
            schemes.add("pension")
        if "health insurance" in text or "medical insurance" in text or "shif" in text:
            schemes.add("health_insurance")
        if "other statutory deduction" in text or "other statutory deductions" in text:
            schemes.add("other_statutory")
    return frozenset(schemes)


def derive_required_oracle_categories(requirement_graph: RequirementGraph) -> frozenset[str]:
    """Derive independent oracle categories from approved payroll requirements."""
    categories: set[str] = set()
    for node in requirement_graph.nodes.values():
        text = node.statement.lower()
        if any(term in text for term in ("gross pay", "gross-to-net", "salary calculation", "calculate salary", "payroll calculation")):
            categories.add("gross_to_net")
            categories.update({"rounding_boundaries", "negative_and_boundary_cases"})
        if any(term in text for term in ("income tax", "social security", "health insurance", "pension", "statutory deduction")):
            categories.add("statutory_deductions")
        if "arrears" in text or "back-pay" in text or "back pay" in text:
            categories.add("arrears_backpay")
        if "leave deduction" in text:
            categories.add("leave_deductions")
        if "cost allocation" in text or "cost center" in text or "cost centre" in text:
            categories.add("cost_allocation")
        if "overtime" in text:
            categories.add("overtime")
        if "pay frequency" in text or "weekly" in text or "bi-weekly" in text or "biweekly" in text:
            categories.add("pay_frequency")
        if "loan" in text or "advance" in text:
            categories.add("loans_advances")
        if "allowance" in text or "benefit" in text:
            categories.add("allowances_benefits")
        if "bonus" in text or "incentive" in text:
            categories.add("bonus_incentives")
        if "bank transfer" in text or "bank details" in text:
            categories.add("bank_transfers")
        if "leave balance" in text or "apply for leave" in text:
            categories.add("leave_balances")
    return frozenset(categories)


def compute_payroll_candidate_hash(
    *,
    requirement_graph: RequirementGraph,
    revision: ISRRevision,
    plan: CompilationPlan,
    tor_source_id: str,
    tor_source_sha256: str,
    tor_candidate_count: int,
    reviewed_tor_candidate_count: int,
    backend_artifact_hashes: Mapping[str, str],
    frontend_artifact_sha256: str,
) -> str:
    """Hash the ISR, lowered plan, exact emitted backend/frontend artifacts, and TOR review state."""
    manifest = {
        "isr_content_hash": revision.content_hash,
        "reviewed_requirements": [
            {
                "id": node.id,
                "kind": node.kind.value,
                "statement": node.statement,
                "priority": node.priority.value,
                "acceptance_criteria": list(node.acceptance_criteria),
                "source_refs": list(node.source_refs),
            }
            for node in sorted(requirement_graph.nodes.values(), key=lambda item: item.id)
        ],
        "derived_statutory_schemes": sorted(derive_required_statutory_schemes(requirement_graph)),
        "derived_oracle_categories": sorted(derive_required_oracle_categories(requirement_graph)),
        "system_id": revision.system_id,
        "plan": plan.model_dump(mode="json"),
        "backend_artifact_hashes": dict(sorted(backend_artifact_hashes.items())),
        "frontend_artifact_sha256": frontend_artifact_sha256,
        "tor_source_id": tor_source_id,
        "tor_source_sha256": tor_source_sha256,
        "tor_candidate_count": tor_candidate_count,
        "reviewed_tor_candidate_count": reviewed_tor_candidate_count,
    }
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def certify_payroll_candidate(
    *,
    requirement_graph: RequirementGraph,
    revision: ISRRevision,
    plan: CompilationPlan,
    candidate_sha256: str,
    tor_source_id: str,
    tor_source_sha256: str,
    tor_candidate_count: int,
    reviewed_tor_candidate_count: int,
    backend_artifact_hashes: Mapping[str, str],
    frontend_artifact_sha256: str,
    payroll_period_start: str,
    payroll_period_end: str,
    required_statutory_schemes: Sequence[str],
    required_oracle_categories: Sequence[str],
    backend_capabilities: Mapping[str, BackendCapabilities],
    required_backends: Sequence[str],
    statutory_evidence: Sequence[StatutoryEvidence] = (),
    oracle_evidence: Sequence[IndependentOracleEvidence] = (),
    frontend_evidence: FrontendRunEvidence | None = None,
    runtime_evidence: Sequence[BackendRuntimeEvidence] = (),
) -> PayrollCertificationReport:
    """Certify only when every required evidence class binds to one candidate."""
    findings: list[str] = []
    checks = (
        "candidate-hash-valid",
        "mandatory-requirement-coverage",
        "behavioral-isr-completeness",
        "backend-capability-compatibility",
        "statutory-source-and-effective-date",
        "independent-requirement-derived-oracles",
        "frontend-build-unit-and-browser-e2e",
        "backend-runtime-independent-verification",
        "evidence-ledger-integrity",
    )

    if not _valid_hash(candidate_sha256):
        findings.append("candidate SHA-256 is missing or malformed")
    if not tor_source_id.strip() or not _valid_hash(tor_source_sha256):
        findings.append("TOR source identity or SHA-256 is missing or malformed")
    if tor_candidate_count <= 0:
        findings.append("TOR extraction contains no reviewable candidates")
    if reviewed_tor_candidate_count != tor_candidate_count:
        findings.append(
            f"TOR review incomplete: {reviewed_tor_candidate_count}/{tor_candidate_count} candidates reviewed"
        )
    if plan.isr_id != revision.system_id:
        findings.append("compilation plan is bound to a different ISR system ID")
    if plan.plan_id != f"plan:{revision.content_hash[:16]}":
        findings.append("compilation plan ID is not bound to the supplied ISR revision")
    if set(backend_artifact_hashes) != set(required_backends):
        findings.append("backend artifact manifest does not exactly match required backends")
    for backend_id in required_backends:
        if not _valid_hash(backend_artifact_hashes.get(backend_id, "")):
            findings.append(f"missing or invalid emitted artifact hash for backend: {backend_id}")
    if not _valid_hash(frontend_artifact_sha256):
        findings.append("frontend artifact SHA-256 is missing or malformed")
    expected_candidate_hash = compute_payroll_candidate_hash(
        requirement_graph=requirement_graph,
        revision=revision,
        plan=plan,
        tor_source_id=tor_source_id,
        tor_source_sha256=tor_source_sha256,
        tor_candidate_count=tor_candidate_count,
        reviewed_tor_candidate_count=reviewed_tor_candidate_count,
        backend_artifact_hashes=backend_artifact_hashes,
        frontend_artifact_sha256=frontend_artifact_sha256,
    )
    if candidate_sha256 != expected_candidate_hash:
        findings.append("candidate SHA-256 does not match the ISR/plan/backend/frontend/TOR artifact manifest")

    period_start = _iso_date(payroll_period_start, "payroll period start", findings)
    period_end = _iso_date(payroll_period_end, "payroll period end", findings)
    if period_start and period_end and period_end < period_start:
        findings.append("payroll period end precedes payroll period start")

    mandatory_ids = {
        node.id for node in requirement_graph.nodes.values()
        if node.priority is Priority.MUST
    }
    mapped_ids = {
        str(node.properties.get("requirement_id", node.properties.get("ref_id", "")))
        for node in revision.graph.nodes.values()
        if node.type is NodeType.REQUIREMENT_REF
    }
    missing_requirements = sorted(mandatory_ids - mapped_ids)
    if missing_requirements:
        findings.append("mandatory TOR requirements are missing from ISR: " + ", ".join(missing_requirements))

    _require_behavioral_completeness(plan, findings)

    for backend_id in required_backends:
        capabilities = backend_capabilities.get(backend_id)
        if capabilities is None:
            findings.append(f"missing capability declaration for backend: {backend_id}")
            continue
        try:
            assert_plan_supported(plan, capabilities)
        except UnsupportedSemanticsError as exc:
            findings.append(f"backend {backend_id} cannot implement this payroll plan: {exc}")

    effective_statutory_schemes = set(required_statutory_schemes) | set(derive_required_statutory_schemes(requirement_graph))
    effective_oracle_categories = set(required_oracle_categories) | set(derive_required_oracle_categories(requirement_graph))
    schemes: dict[str, list[StatutoryEvidence]] = {}
    for evidence in statutory_evidence:
        schemes.setdefault(evidence.scheme, []).append(evidence)
    for scheme in sorted(effective_statutory_schemes):
        evidence_items = schemes.get(scheme, [])
        if not evidence_items:
            findings.append(f"missing statutory evidence for scheme: {scheme}")
            continue
        intervals: list[tuple[date, date | None, StatutoryEvidence]] = []
        for evidence in evidence_items:
            if not evidence.source_ref.strip() or not _valid_hash(evidence.source_sha256):
                findings.append(f"statutory source provenance is invalid for scheme: {scheme}")
            if evidence.candidate_sha256 != candidate_sha256:
                findings.append(f"statutory test evidence is bound to a different candidate: {scheme}")
            if not evidence.verified_by.strip():
                findings.append(f"statutory source lacks reviewer approval: {scheme}")
            effective_from = _iso_date(evidence.effective_from, f"{scheme} effective_from", findings)
            effective_to = _iso_date(evidence.effective_to, f"{scheme} effective_to", findings) if evidence.effective_to else None
            if effective_from and effective_to and effective_to < effective_from:
                findings.append(f"{scheme} statutory effective interval is inverted")
            if evidence.test_cases <= 0 or evidence.passed_cases != evidence.test_cases or evidence.failed_cases != 0:
                findings.append(f"{scheme} statutory test vectors are incomplete or failing")
            if effective_from and (effective_to is None or effective_to >= effective_from):
                intervals.append((effective_from, effective_to, evidence))

        if period_start and period_end:
            relevant = sorted(
                (
                    (start_date, end_date, evidence)
                    for start_date, end_date, evidence in intervals
                    if start_date <= period_end and (end_date is None or end_date >= period_start)
                ),
                key=lambda item: item[0],
            )
            cursor = period_start
            covered = False
            previous_end: date | None = None
            for start_date, end_date, evidence in relevant:
                clipped_start = max(start_date, period_start)
                clipped_end = min(end_date or period_end, period_end)
                if previous_end is not None and clipped_start <= previous_end:
                    findings.append(f"{scheme} has overlapping statutory source intervals")
                    continue
                if clipped_start > cursor:
                    findings.append(f"{scheme} statutory source coverage has a gap starting {cursor.isoformat()}")
                    cursor = clipped_start
                if clipped_start > cursor:
                    continue
                previous_end = clipped_end
                cursor = clipped_end.fromordinal(clipped_end.toordinal() + 1)
                if clipped_end >= period_end:
                    covered = True
                    break
            if not covered:
                findings.append(f"{scheme} statutory evidence does not cover the full payroll period")

    requirement_ids = set(requirement_graph.nodes)
    oracles = {item.category: item for item in oracle_evidence}
    for category in sorted(effective_oracle_categories):
        evidence = oracles.get(category)
        if evidence is None:
            findings.append(f"missing independent payroll oracle category: {category}")
            continue
        if evidence.source_requirement_id not in requirement_ids:
            findings.append(f"oracle {category} references an unknown source requirement")
        if not evidence.source_ref.strip() or not _valid_hash(evidence.source_sha256):
            findings.append(f"oracle {category} lacks source provenance")
        if evidence.candidate_sha256 != candidate_sha256:
            findings.append(f"oracle {category} is bound to a different candidate")
        if not evidence.independently_authored_by.strip():
            findings.append(f"oracle {category} lacks independent authorship")
        if evidence.test_cases <= 0 or evidence.passed_cases != evidence.test_cases or evidence.failed_cases != 0:
            findings.append(f"oracle {category} has incomplete or failing test cases")

    if frontend_evidence is None:
        findings.append("missing real frontend build/unit/E2E evidence")
    else:
        if frontend_evidence.candidate_sha256 != candidate_sha256:
            findings.append("frontend evidence is bound to a different candidate")
        if not _valid_hash(frontend_evidence.artifact_sha256):
            findings.append("frontend artifact hash is invalid")
        if frontend_evidence.artifact_sha256 != frontend_artifact_sha256:
            findings.append("frontend execution evidence does not match the declared frontend artifact hash")
        for label, passed in (
            ("frontend build", frontend_evidence.build_passed),
            ("frontend unit tests", frontend_evidence.unit_tests_passed),
            ("frontend browser E2E", frontend_evidence.e2e_passed),
        ):
            if passed is not True:
                findings.append(f"{label} did not pass")
        for label, digest in (
            ("frontend build log", frontend_evidence.build_log_sha256),
            ("frontend unit log", frontend_evidence.unit_log_sha256),
            ("frontend E2E log", frontend_evidence.e2e_log_sha256),
        ):
            if not _valid_hash(digest):
                findings.append(f"{label} hash is invalid")
        if not frontend_evidence.workflow_run_id or not frontend_evidence.source_commit:
            findings.append("frontend evidence lacks workflow/commit identity")

    runtime_by_backend = {item.backend_id: item for item in runtime_evidence}
    for backend_id in required_backends:
        evidence = runtime_by_backend.get(backend_id)
        if evidence is None:
            findings.append(f"missing backend runtime evidence: {backend_id}")
            continue
        if evidence.candidate_sha256 != candidate_sha256:
            findings.append(f"runtime evidence for {backend_id} is bound to a different candidate")
        if not evidence.workflow_run_id or not evidence.source_commit:
            findings.append(f"runtime evidence for {backend_id} lacks workflow/commit identity")
        if evidence.trial_count <= 0 or evidence.pass_count != evidence.trial_count:
            findings.append(f"runtime trials for {backend_id} are incomplete or failing")
        for label, passed in (
            ("build", evidence.build_passed),
            ("tests", evidence.tests_passed),
            ("independent verification", evidence.independent_verification_passed),
            ("health", evidence.health_passed),
            ("cleanup", evidence.cleanup_passed),
            ("ledger chain", evidence.ledger_chain_valid),
        ):
            if passed is not True:
                findings.append(f"{backend_id} runtime {label} evidence did not pass")

    findings = list(dict.fromkeys(findings))
    return PayrollCertificationReport(
        verdict="CERTIFIED" if not findings else "NOT_CERTIFIED",
        candidate_sha256=candidate_sha256,
        checks=checks,
        findings=tuple(findings),
    )
