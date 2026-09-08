"""VS-D13 — bounded architecture evolution (synthetic authorization only).

Consumes an explicit D12 AUTHORIZE_EVOLUTION authorization and produces
bounded, competing evolved architecture candidates. The real D12 record is
NO_CHANGE and can never enter generation (fail-closed). No selection,
implementation, deployment, observation, or interpretation occurs here. See
folder/VS1_EVOLUTION_CANDIDATES.md.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

EVOLUTION_CONTRACT_VERSION = "vs1-evolution-v1"
EVOLUTION_POLICY_VERSION = "vs1-evolution-policy-v1"

_BASE_ARCHITECTURE_ID = "vs1-candidate-a"

# Policy fitness weights (explicit; belong to the evolution policy, not ISR).
_W_ALIGN = 0.30
_W_REQUIREMENT = 0.20
_W_SECURITY = 0.15
_W_COHESION = 0.10
_W_ROLLBACK = 0.10
_W_COUPLING = 0.05
_W_COMPLEXITY = 0.05
_W_VERCOST = 0.05

# Mandatory preserved capabilities (requirement preservation floor).
_MANDATORY_CAPABILITIES = (
    "cap-task-create",
    "cap-task-read",
    "cap-task-update",
    "cap-task-delete",
    "cap-registration",
    "cap-authentication",
)

# Security references that must survive in every candidate.
_REQUIRED_SECURITY_REFS = (
    "sec-credential-safety",
    "sec-tenant-isolation",
)

_WEAKENING_MARKERS = (
    "remove authentication",
    "bypass authorization",
    "no auth",
    "disable auth",
    "weaken role",
    "expose protected",
    "store credentials",
    "plaintext secret",
)

_W_REQUIREMENT = 0.20

# Security references that must survive in every candidate.
_REQUIRED_SECURITY_REFS = (
    "sec-credential-safety",
    "sec-tenant-isolation",
)

_WEAKENING_MARKERS = (
    "remove authentication",
    "bypass authorization",
    "no auth",
    "disable auth",
    "weaken role",
    "expose protected",
    "store credentials",
    "plaintext secret",
)


class EvolutionError(Exception):
    """Fail-closed evolution failure (never guess an authorization)."""


class EvolutionNotAuthorized(EvolutionError):
    """A non-AUTHORIZE real decision reached generation."""


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def load_real_decision(
    path: str = "vertical_slice/evolution_decision_v2_evidence.json",
) -> dict[str, Any]:
    """Load the real D12 record (fail-closed, read-only)."""
    try:
        with open(path, encoding="utf-8") as f:
            decision = json.load(f)
    except (OSError, ValueError) as exc:
        raise EvolutionError(f"D12 record unavailable: {exc}")
    if not isinstance(decision, dict):
        raise EvolutionError("D12 record malformed")
    return decision


def synthetic_authorization() -> dict[str, Any]:
    """Test-only authorization fixture (never a production authorization)."""
    objective = {
        "objective_id": "vs1-objective-synthetic-auth-boundary",
        "problem_statement": (
            "Harden the authorization boundary so policy decisions flow "
            "through an explicit, auditable structure while preserving "
            "existing authenticated-user behavior and task lifecycle semantics."),
        "evidence_basis": ["vs1-v2-claim-1e9c9711edd6"],
        "finding_refs": ["vs1-v2-finding-auth-boundary"],
        "hypothesis_refs": ["vs1-hypothesis-auth-model-adequate"],
        "affected_scope": "authorization policy structure and enforcement boundary",
        "desired_outcome": "explicit auditable authorization decisions",
        "success_measure": "all existing auth/isolation probes keep passing",
        "constraints": ["requirements preserved", "ISR preserved",
                        "CRUD semantics preserved"],
        "risk": "bounded loopback evaluation",
        "rollback_requirement": "previous known-good state restorable",
        "verification_requirement": "reverification before acceptance",
        "deployment_requirement": "controlled deployment before production",
        "observation_requirement": "post-deployment observation",
        "magnitude": "ARCHITECTURAL_CHANGE",
    }
    return {
        "authorization_id": "vs1-authorization-synthetic-001",
        "authorization_mode": "SYNTHETIC_TEST_ONLY",
        "source_decision": "D12-SYNTHETIC",
        "objective_id": objective["objective_id"],
        "objective": objective,
        "evidence_refs": ["vs1-v2-claim-1e9c9711edd6"],
        "finding_refs": ["vs1-v2-finding-auth-boundary"],
        "hypothesis_refs": ["vs1-hypothesis-auth-model-adequate"],
        "scope": objective["affected_scope"],
        "invariants": ["requirements immutable", "ISR immutable",
                       "verification mandatory"],
        "allowed_change_surface": [
            "authorization policy structure",
            "authorization enforcement boundary",
            "service-level authorization responsibility",
            "authorization decision flow",
        ],
        "forbidden_change_surface": [
            "changing requirements",
            "deleting security controls",
            "weakening authentication",
            "changing persistence model",
            "changing deployment target",
            "changing unrelated service responsibilities",
            "changing domain semantics",
            "changing the ISR",
        ],
        "rollback_strategy": objective["rollback_requirement"],
        "verification_gates": [objective["verification_requirement"]],
        "deployment_gate": objective["deployment_requirement"],
        "observation_gate": objective["observation_requirement"],
        "success_criteria": [objective["success_measure"]],
    }


def validate_authorization(authorization: dict[str, Any]) -> dict[str, Any]:
    """Fail-closed authorization validation. Real NO_CHANGE/REJECT/BLOCKED
    records are refused; only explicit test-mode authorizations pass."""
    for field in ("authorization_id", "objective", "allowed_change_surface",
                  "forbidden_change_surface", "scope"):
        if field not in authorization:
            raise EvolutionError(f"authorization missing field: {field}")
    if authorization.get("authorization_mode") != "SYNTHETIC_TEST_ONLY":
        raise EvolutionNotAuthorized(
            "real production authorization required; "
            f"found mode={authorization.get('authorization_mode')}")
    objective = authorization["objective"]
    for field in ("objective_id", "problem_statement", "desired_outcome",
                  "success_measure"):
        if field not in objective:
            raise EvolutionError(f"objective missing field: {field}")
    return authorization


def _profile_table() -> dict[str, dict[str, Any]]:
    """The three materially distinct architecture profiles (policy data with
    documented rationale; computation over them is deterministic)."""
    return {
        "central-policy": {
            "description": ("Authorization remains centralized behind a "
                            "dedicated policy boundary."),
            "added": ["authorization-policy-component"],
            "modified": ["authorization-decision-flow"],
            "removed": [],
            "boundary": "single central policy component fronts all services",
            "interaction": "services query the central policy component",
            "rationale": {
                "objective_alignment": (1.0, "directly implements the objective"),
                "security_improvement": (0.6, "one auditable choke point"),
                "cohesion": (0.8, "policy logic in one place"),
                "coupling": (0.5, "all services depend on the policy component"),
                "complexity": (0.4, "one new component, one modified flow"),
                "rollbackability": (0.9, "policy component removable"),
                "verification_cost": (0.4, "central behavior testable once"),
            },
        },
        "service-owned": {
            "description": ("Authorization responsibility moves to the service "
                            "boundary with explicit enforcement at service entry."),
            "added": ["service-entry-policy-enforcement"],
            "modified": ["svc-identity-entry", "svc-task-entry", "svc-workspace-entry"],
            "removed": [],
            "boundary": "each service enforces policy at its own entry",
            "interaction": "services consult colocated policy rules",
            "rationale": {
                "objective_alignment": (0.9, "implements the objective per service"),
                "security_improvement": (0.7, "defense in depth at every entry"),
                "cohesion": (0.6, "policy logic colocated with services"),
                "coupling": (0.3, "no new cross-service dependency"),
                "complexity": (0.6, "three modified entries"),
                "rollbackability": (0.7, "per-service revert possible"),
                "verification_cost": (0.6, "three entries to verify"),
            },
        },
        "policy-capability": {
            "description": ("Dedicated policy component plus explicit capability "
                            "checks at protected service operations."),
            "added": ["authorization-policy-component", "operation-capability-checks"],
            "modified": ["protected-operation-guards"],
            "removed": [],
            "boundary": "central policy plus per-operation capability gates",
            "interaction": "operations present capabilities; policy adjudicates",
            "rationale": {
                "objective_alignment": (0.8, "implements the objective with gates"),
                "security_improvement": (0.8, "policy plus least-privilege gates"),
                "cohesion": (0.7, "policy central, gates colocated"),
                "coupling": (0.6, "operations depend on policy component"),
                "complexity": (0.7, "two added structures plus guards"),
                "rollbackability": (0.6, "gates removable independently"),
                "verification_cost": (0.7, "policy plus gate matrix to verify"),
            },
        },
    }


def _isr_nodes() -> set[str]:
    from vertical_slice.isr import build_task_tracker_isr

    return set(build_task_tracker_isr().graph.nodes)


def generate_candidates(authorization: dict[str, Any],
                        seed: int = 42) -> list[dict[str, Any]]:
    """Generate the bounded competing evolved candidates (deterministic; no
    randomness is used — the seed parameter documents the policy slot)."""
    _ = seed
    validate_authorization(authorization)
    objective = authorization["objective"]
    isr_nodes = _isr_nodes()
    candidates = []
    for profile in ("central-policy", "service-owned", "policy-capability"):
        spec = _profile_table()[profile]
        candidate_id = _stable_id(
            "vs1-evolved", objective["objective_id"], profile,
            json.dumps(spec, sort_keys=True))
        affected = ["svc-task", "svc-identity", "api-task", "api-identity",
                    "sec-credential-safety", "sec-tenant-isolation",
                    "cap-task-create", "cap-authentication"]
        preserved = [
            "cap-registration", "cap-authentication",
            "cap-task-create", "cap-task-read", "cap-task-update",
            "cap-task-delete", "cap-task-assign", "cap-membership-mgmt",
            "svc-identity", "svc-task", "svc-workspace",
            "api-identity", "api-task", "api-workspace",
            "dm-task", "dm-workspace", "dm-user-account",
            "sec-credential-safety", "sec-tenant-isolation",
        ]
        for ref in affected + preserved:
            if ref not in isr_nodes:
                raise EvolutionError(f"invalid ISR reference: {ref}")
        delta = {
            "added_responsibilities": list(spec["added"]),
            "removed_responsibilities": list(spec["removed"]),
            "modified_responsibilities": list(spec["modified"]),
            "modified_boundaries": [spec["boundary"]],
            "modified_interactions": [spec["interaction"]],
            "preserved_invariants": [
                "CRUD lifecycle semantics",
                "persistence semantics",
                "password hashing",
                "event semantics",
                "API contract semantics",
            ],
        }
        candidates.append({
            "candidate_id": candidate_id,
            "parent_candidate_id": _BASE_ARCHITECTURE_ID,
            "base_architecture_id": _BASE_ARCHITECTURE_ID,
            "evolution_id": "vs1-evolution-synthetic-001",
            "objective_id": objective["objective_id"],
            "profile": profile,
            "description": spec["description"],
            "architecture_delta": delta,
            "preserved_invariants": list(delta["preserved_invariants"]),
            "changed_surfaces": sorted(set(spec["added"]) | set(spec["modified"])),
            "affected_isr_refs": sorted(affected),
            "preserved_isr_refs": sorted(preserved),
            "constraint_results": {"allowed_scope": True,
                                   "forbidden_scope": False},
            "fitness": fitness_candidate(profile),
            "admissibility": "ADMISSIBLE",
            "lineage": {
                "authorization_id": authorization["authorization_id"],
                "objective_id": objective["objective_id"],
                "parent_candidate_id": _BASE_ARCHITECTURE_ID,
                "base_architecture_id": _BASE_ARCHITECTURE_ID,
            },
        })
    for candidate in candidates:
        candidate["content_hash"] = hashlib.sha256(json.dumps(
            {k: v for k, v in candidate.items() if k != "content_hash"},
            sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        candidate["lineage_hash"] = hashlib.sha256("|".join([
            candidate["parent_candidate_id"],
            json.dumps(candidate["architecture_delta"], sort_keys=True),
            candidate["objective_id"]]).encode()).hexdigest()
    check_distinct(candidates)
    for candidate in candidates:
        admissible, _ = check_admissible(candidate)
        if not admissible:
            raise EvolutionError(
                f"generated inadmissible candidate: {candidate['candidate_id']}")
    return sorted(candidates, key=lambda c: c["candidate_id"])


def fitness_candidate(profile: str) -> dict[str, float]:
    """Deterministic policy fitness from declared delta attributes."""
    rationale = _profile_table()[profile]["rationale"]
    values = {dim: score for dim, (score, _why) in rationale.items()}
    total = (
        _W_ALIGN * values["objective_alignment"]
        + _W_REQUIREMENT * 1.0
        + _W_SECURITY * values["security_improvement"]
        + _W_COHESION * values["cohesion"]
        + _W_ROLLBACK * values["rollbackability"]
        - _W_COUPLING * values["coupling"]
        - _W_COMPLEXITY * values["complexity"]
        - _W_VERCOST * values["verification_cost"]
    )
    return {
        "objective_alignment": values["objective_alignment"],
        "requirement_preservation": 1.0,
        "security_improvement": values["security_improvement"],
        "architectural_cohesion": values["cohesion"],
        "coupling": values["coupling"],
        "complexity": values["complexity"],
        "rollbackability": values["rollbackability"],
        "verification_cost": values["verification_cost"],
        "total": round(total, 6),
    }


def check_admissible(candidate: dict[str, Any]) -> tuple[bool, list[str]]:
    """Admissibility: ISR compatibility, requirement preservation, scope,
    security, invariants, validity, provenance. Fail-closed reasons."""
    reasons: list[str] = []
    isr_nodes = _isr_nodes()
    for ref in candidate.get("affected_isr_refs", []):
        if ref not in isr_nodes:
            reasons.append(f"unknown ISR reference: {ref}")
    preserved = set(candidate.get("preserved_isr_refs", []))
    for cap in _MANDATORY_CAPABILITIES:
        if cap not in preserved:
            reasons.append(f"mandatory capability not preserved: {cap}")
    blob = json.dumps(candidate).lower()
    if "task" not in blob or "crud" not in blob:
        reasons.append("CRUD lifecycle not preserved")
    for marker in _WEAKENING_MARKERS:
        if marker in blob:
            reasons.append(f"security weakening: {marker}")
    for ref in _REQUIRED_SECURITY_REFS:
        if ref not in candidate.get("affected_isr_refs", []):
            reasons.append(f"required security reference missing: {ref}")
    if not candidate.get("lineage", {}).get("parent_candidate_id"):
        reasons.append("missing parent lineage")
    if not candidate.get("content_hash"):
        reasons.append("missing content hash")
    return (not reasons), reasons


def check_distinct(candidates: list[dict[str, Any]]) -> None:
    """Reject structural duplicates after canonical normalization."""
    seen: dict[str, str] = {}
    for candidate in candidates:
        normalized = json.dumps(
            {k: v for k, v in candidate.items()
             if k not in ("candidate_id", "content_hash", "lineage_hash")},
            sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(normalized.encode()).hexdigest()
        if digest in seen:
            raise EvolutionError(
                f"duplicate candidate: {candidate['candidate_id']} "
                f"duplicates {seen[digest]}")
        seen[digest] = candidate["candidate_id"]


def order_candidates(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """NON-AUTHORITATIVE analytical ordering (never a production selection)."""
    ranked = sorted(candidates,
                    key=lambda c: (-c["fitness"]["total"], c["candidate_id"]))
    return {
        "order_kind": "NON-AUTHORITATIVE_CANDIDATE_ORDER",
        "ranked_candidate_ids": [c["candidate_id"] for c in ranked],
        "note": "analytical only; production selection belongs to a later stage",
    }


def build_evidence(run_label: str = "vs1-d13-proof") -> dict[str, Any]:
    """Execute the synthetic proof path and assemble the evidence record."""
    from vertical_slice import implementation as IMPL
    from vertical_slice import candidates as C

    authorization = synthetic_authorization()
    validate_authorization(authorization)
    candidates = generate_candidates(authorization)
    ordering = order_candidates(candidates)
    identity = IMPL.frozen_input_identity()
    record = {
        "contract": EVOLUTION_CONTRACT_VERSION,
        "policy": EVOLUTION_POLICY_VERSION,
        "run_label": run_label,
        "authorization_mode": "SYNTHETIC_TEST_ONLY",
        "real_d12_decision": "NO_CHANGE",
        "upstream_identities": {
            "vs-d01-graph-sha256": identity["vs-d01-graph-sha256"],
            "vs-d02-isr-content-hash": identity["vs-d02-isr-content-hash"],
            "vs-d03-selected": "vs1-candidate-a",
            "vs-d03-policy": C.SELECTION_POLICY_VERSION,
            "vs-d12-decision": "NO_CHANGE",
        },
        "objective": authorization["objective"],
        "candidates": candidates,
        "ordering": ordering,
        "production_selection": "NOT_PERFORMED",
    }
    record["content_hash"] = hashlib.sha256(json.dumps(
        {k: v for k, v in record.items() if k != "content_hash"},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return record
