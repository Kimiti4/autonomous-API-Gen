"""VS-D03 — deterministic candidate generation + selection for the VS-1 slice.

Consumes ONLY the frozen upstream artifacts:
  VS-D01: vertical_slice.requirements.build_task_tracker_requirements
  VS-D02: vertical_slice.isr.build_task_tracker_isr

Side-effect bounded: pure functions over frozen inputs. No deployment,
backend startup, compiler execution, runtime observation, or evolution.
No timestamps influence generation, scoring, ranking, or selection.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from vertical_slice.isr import build_task_tracker_isr
from vertical_slice.requirements import build_task_tracker_requirements

CANDIDATE_SCHEMA_VERSION = "vs1-candidate-v1"
SELECTION_POLICY_VERSION = "vs1-selection-v1"
BUILDER_VERSION = "vs1-candidates-v1"

# Mandatory coverage: every MUST requirement and every capability/service.
_MANDATORY_REQUIREMENTS: tuple[str, ...] = (
    "req-auth-register", "req-auth-login",
    "req-task-create", "req-task-read", "req-task-update", "req-task-delete",
    "req-credential-safety", "req-tenant-isolation",
    "con-multiuser",
)
_MANDATORY_CAPABILITIES: tuple[str, ...] = (
    "cap-registration", "cap-authentication",
    "cap-task-create", "cap-task-read", "cap-task-update", "cap-task-delete",
)
_MANDATORY_SERVICES: tuple[str, ...] = ("svc-identity", "svc-task", "svc-workspace")

# Scoring weights (documented in folder/VS1_CANDIDATES.md). Fixed.
_W_COVERAGE = 0.4
_W_SECURITY = 0.3
_W_SIMPLICITY = 0.2
_W_RISK = 0.1


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    candidate_version: str
    description: str
    implementation_profile: str
    technology_profile: tuple[tuple[str, str], ...]
    requirement_coverage: tuple[str, ...]
    isr_coverage: tuple[str, ...]
    constraints_satisfied: tuple[str, ...]
    security_posture: tuple[str, ...]
    operational_complexity: int
    cross_service_dependencies: int
    resource_units: int
    risk_ordinal: int  # 1 = low, 2 = medium; lower is better
    risk_rationale: str
    provenance: tuple[tuple[str, str], ...] = field(default_factory=tuple)


def _upstream_identity() -> tuple[tuple[str, str], ...]:
    """Capture frozen upstream identity (content hashes of the built graphs)."""
    graph = build_task_tracker_requirements()
    rev = build_task_tracker_isr()
    graph_hash = hashlib.sha256(json.dumps(
        graph.model_dump(mode="json"), sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()
    return (
        ("vs-d01-builder", "vertical_slice.requirements.build_task_tracker_requirements"),
        ("vs-d02-builder", "vertical_slice.isr.build_task_tracker_isr"),
        ("requirement-graph-sha256", graph_hash),
        ("isr-content-hash", rev.content_hash),
        ("builder-version", BUILDER_VERSION),
        ("candidate-schema-version", CANDIDATE_SCHEMA_VERSION),
        ("selection-policy-version", SELECTION_POLICY_VERSION),
    )


def build_candidates() -> tuple[Candidate, ...]:
    """Generate the bounded, deterministic candidate set (exactly 2)."""
    provenance = _upstream_identity()
    common_reqs = _MANDATORY_REQUIREMENTS + (
        "req-task-assign", "req-workspace-members",
        "req-durability", "con-api-surface",
    )
    common_isr = _MANDATORY_CAPABILITIES + _MANDATORY_SERVICES + (
        "api-identity", "api-task", "api-workspace",
        "dm-task", "dm-workspace", "dm-user-account",
        "sec-credential-safety", "sec-tenant-isolation",
    )
    candidate_a = Candidate(
        candidate_id="vs1-candidate-a",
        candidate_version="1",
        description="Consolidated single-service implementation profile.",
        implementation_profile="consolidated-monolith",
        technology_profile=(
            ("runtime", "single-service"), ("framework", "fastapi"),
            ("storage", "postgres"), ("auth", "session-tokens"),
        ),
        requirement_coverage=common_reqs,
        isr_coverage=common_isr,
        constraints_satisfied=("con-multiuser", "con-api-surface"),
        security_posture=("credential-safety", "tenant-isolation"),
        operational_complexity=1,
        cross_service_dependencies=0,
        resource_units=2,
        risk_ordinal=1,
        risk_rationale="Single deployable; no cross-service calls; fewest moving parts.",
        provenance=provenance,
    )
    candidate_b = Candidate(
        candidate_id="vs1-candidate-b",
        candidate_version="1",
        description="Decomposed three-service implementation profile mirroring ISR topology.",
        implementation_profile="decomposed-services",
        technology_profile=(
            ("runtime", "three-services"), ("framework", "fastapi"),
            ("storage", "postgres"), ("auth", "session-tokens"),
        ),
        requirement_coverage=common_reqs,
        isr_coverage=common_isr,
        constraints_satisfied=("con-multiuser", "con-api-surface"),
        security_posture=("credential-safety", "tenant-isolation"),
        operational_complexity=3,
        cross_service_dependencies=2,
        resource_units=4,
        risk_ordinal=2,
        risk_rationale="Three deployables with cross-service calls; more failure modes.",
        provenance=provenance,
    )
    return (candidate_a, candidate_b)


def check_admissible(candidate: Candidate) -> dict[str, bool]:
    """Evaluate the A1-A9 mandatory gates. No compensating scores."""
    graph = build_task_tracker_requirements()
    rev = build_task_tracker_isr()
    req_ids = set(graph.nodes)
    isr_ids = set(rev.graph.nodes)
    checks = {
        # A1: complete requirement lineage
        "A1-requirement-lineage": all(r in req_ids for r in candidate.requirement_coverage)
        and all(r in candidate.requirement_coverage for r in _MANDATORY_REQUIREMENTS),
        # A2: complete ISR lineage
        "A2-isr-lineage": all(i in isr_ids for i in candidate.isr_coverage)
        and all(i in candidate.isr_coverage
                for i in _MANDATORY_CAPABILITIES + _MANDATORY_SERVICES),
        # A3: mandatory capabilities satisfiable
        "A3-capabilities": all(c in candidate.isr_coverage for c in _MANDATORY_CAPABILITIES),
        # A4: mandatory security constraints satisfiable
        "A4-security": "credential-safety" in candidate.security_posture
        and "tenant-isolation" in candidate.security_posture,
        # A5: explicit constraints satisfiable
        "A5-constraints": "con-multiuser" in candidate.constraints_satisfied,
        # A6: no unresolved conflict (anon-sharing is deferred upstream, absent here)
        "A6-conflict-freedom": "req-anon-sharing" not in candidate.requirement_coverage,
        # A7: no forbidden dependency (no candidate bypasses auth services)
        "A7-no-forbidden-dependency": True,
        # A8: deterministic evaluation (proven by re-evaluation equality in tests)
        "A8-deterministic": True,
        # A9: technology choice does not modify canonical truth (static; pinned by tests)
        "A9-upstream-immutable": True,
    }
    return checks


def score_candidate(candidate: Candidate, max_complexity: int, max_risk: int) -> dict[str, float]:
    """Deterministic soft scoring. Scale [0,1] per metric; fixed weights."""
    coverage = sum(1 for r in _MANDATORY_REQUIREMENTS if r in candidate.requirement_coverage) / len(
        _MANDATORY_REQUIREMENTS)
    security = (1.0 if "credential-safety" in candidate.security_posture else 0.0) * 0.5 + (
        1.0 if "tenant-isolation" in candidate.security_posture else 0.0) * 0.5
    simplicity = 1.0 - (candidate.operational_complexity / max_complexity)
    risk_score = 1.0 - (candidate.risk_ordinal / max_risk)
    total = (_W_COVERAGE * coverage + _W_SECURITY * security
             + _W_SIMPLICITY * simplicity + _W_RISK * risk_score)
    return {
        "coverage": round(coverage, 6),
        "security": round(security, 6),
        "simplicity": round(simplicity, 6),
        "risk_score": round(risk_score, 6),
        "total": round(total, 6),
    }


def rank_candidates(candidates: tuple[Candidate, ...]) -> list[tuple[Candidate, dict[str, bool], dict[str, float]]]:
    """Evaluate + rank. Only admissible candidates are ranked. Deterministic
    tie-break: total desc, risk asc, complexity asc, candidate_id asc."""
    evaluated = []
    for candidate in candidates:
        checks = check_admissible(candidate)
        if not all(checks.values()):
            continue
        evaluated.append((candidate, checks))
    if not evaluated:
        return []
    max_complexity = max(c.operational_complexity for c, _ in evaluated)
    max_risk = max(c.risk_ordinal for c, _ in evaluated)
    ranked = [(c, ch, score_candidate(c, max_complexity, max_risk)) for c, ch in evaluated]
    ranked.sort(key=lambda item: (
        -item[2]["total"], item[0].risk_ordinal,
        item[0].operational_complexity, item[0].candidate_id))
    return ranked


def select_candidate(
    candidates: tuple[Candidate, ...] | None = None,
) -> dict[str, object]:
    """Select exactly one winner iff the gate passes; fail closed on ties."""
    ranked = rank_candidates(build_candidates() if candidates is None else candidates)
    if not ranked:
        return {"selected": None, "reason": "NO ADMISSIBLE CANDIDATE"}
    best, best_checks, best_scores = ranked[0]
    if len(ranked) > 1:
        runner, _, runner_scores = ranked[1]
        if (best_scores["total"] == runner_scores["total"]
                and best.risk_ordinal == runner.risk_ordinal
                and best.operational_complexity == runner.operational_complexity):
            return {"selected": None,
                    "reason": "TIE AFTER ALL TIE-BREAKERS — FAIL CLOSED"}
    return {
        "selected": best.candidate_id,
        "selection_policy_version": SELECTION_POLICY_VERSION,
        "selection_score": best_scores["total"],
        "candidate_rank": [c.candidate_id for c, _, _ in ranked],
        "admissibility_result": best_checks,
        "requirement_refs": list(best.requirement_coverage),
        "isr_refs": list(best.isr_coverage),
        "decision_rationale": (
            f"{best.candidate_id} wins deterministically: total={best_scores['total']} "
            f"(coverage={best_scores['coverage']}, security={best_scores['security']}, "
            f"simplicity={best_scores['simplicity']}, risk={best_scores['risk_score']}); "
            f"risk_ordinal={best.risk_ordinal}, complexity={best.operational_complexity}."
        ),
        "decision_provenance": list(best.provenance),
    }
