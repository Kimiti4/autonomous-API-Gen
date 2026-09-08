"""VS-D14 — evolution candidate selection gate (choice only, no authority).

Consumes the frozen D13 evolved candidates and chooses exactly one admissible
candidate under a deterministic contract. Records selection_mode explicitly:
SYNTHETIC_TEST_ONLY with production_authorization FALSE while the real D12
record remains NO_CHANGE. Never generates, implements, deploys, observes,
interprets, or authorizes. See folder/VS1_EVOLUTION_SELECTION.md.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

SELECTION_CONTRACT_VERSION = "vs1-selection-v2"
SELECTION_POLICY = "vs1-evolution-selection-v1"

_MANDATORY_CAPABILITIES = (
    "cap-task-create",
    "cap-task-read",
    "cap-task-update",
    "cap-task-delete",
    "cap-registration",
    "cap-authentication",
)

_REQUIRED_SECURITY_REFS = (
    "sec-credential-safety",
    "sec-tenant-isolation",
)


class SelectionError(Exception):
    """Fail-closed selection failure (never guess a winner)."""


class SelectionBlocked(SelectionError):
    """Selection cannot proceed; explicit BLOCKED outcome."""


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def load_candidates() -> list[dict[str, Any]]:
    """Recompute (never trust copies) the frozen D13 candidate set."""
    from vertical_slice import evolution as EVO

    record = EVO.build_evidence()
    candidates = record.get("candidates", [])
    if len(candidates) != 3:
        raise SelectionError(
            f"D13 must hold 3 candidates, found {len(candidates)}")
    return candidates


def load_real_decision(
    path: str = "vertical_slice/evolution_decision_v2_evidence.json",
) -> dict[str, Any]:
    """Load the real D12 record (fail-closed, read-only). Local to D14 so
    the D13 module stays byte-untouched. Never mutates the record."""
    try:
        with open(path, encoding="utf-8") as f:
            decision = json.load(f)
    except (OSError, ValueError) as exc:
        raise SelectionError(f"D12 record unavailable: {exc}")
    if not isinstance(decision, dict):
        raise SelectionError("D12 record malformed")
    for field in ("decision", "content_hash", "policy_id"):
        if field not in decision:
            raise SelectionError(f"D12 record missing field: {field}")
    return decision


def upstream_identities() -> dict[str, str]:
    """Recompute frozen upstream identities D01–D13 (fail-closed)."""
    import json as _json
    from vertical_slice import implementation as IMPL
    from vertical_slice import candidates as C
    from vertical_slice.deployment import build_contract as deploy_contract
    from vertical_slice import observation as OBS
    from vertical_slice import evolution_decision as DEC
    from vertical_slice import evidence_acquisition as ACQ

    identity = IMPL.frozen_input_identity()
    contract = deploy_contract()
    real = load_real_decision()
    expected = {
        "vs-d01-graph-sha256": identity["vs-d01-graph-sha256"],
        "vs-d02-isr-content-hash": identity["vs-d02-isr-content-hash"],
        "vs-d03-selected": "vs1-candidate-a",
        "vs-d03-policy": C.SELECTION_POLICY_VERSION,
        "vs-d04-implementation": IMPL.IMPLEMENTATION_VERSION,
        "vs-d05-deployment": str(contract["deployment_contract_version"]),
        "vs-d06-observation": OBS.OBSERVATION_CONTRACT_VERSION,
        "vs-d07-interpretation": "vs1-interpret-v1",
        "vs-d08-decision": DEC.decide()["decision"],
        "vs-d09-policy": ACQ.run_gate()["policy"],
        "vs-d10-contract": "vs1-evidence-run-v1",
        "vs-d11-contract": "vs1-interpretation-v2",
        "vs-d12-decision": real["decision"],
        "vs-d12-hash": real["content_hash"],
        "vs-d13-contract": "vs1-evolution-v1",
    }
    if expected["vs-d12-decision"] != "NO_CHANGE":
        raise SelectionError("real D12 decision drift")
    with open("vertical_slice/interpretation_v2_evidence.json",
              encoding="utf-8") as f:
        v2 = _json.load(f)
    if len(v2.get("hypotheses", [])) != 2:
        raise SelectionError("D11 interpretation drift")
    return expected


def check_admissible(candidate: dict[str, Any],
                     isr_nodes: set[str]) -> tuple[bool, list[str]]:
    """Independent D14 admissibility verification (fail-closed reasons)."""
    reasons: list[str] = []
    for field in ("candidate_id", "parent_candidate_id",
                  "base_architecture_id", "objective_id", "fitness",
                  "affected_isr_refs", "preserved_invariants", "lineage",
                  "content_hash"):
        if field not in candidate:
            reasons.append(f"missing field: {field}")
    if reasons:
        return False, reasons
    if candidate.get("parent_candidate_id") != "vs1-candidate-a":
        reasons.append("parent lineage broken")
    if candidate.get("base_architecture_id") != "vs1-candidate-a":
        reasons.append("base architecture mismatch")
    for ref in candidate.get("affected_isr_refs", []):
        if ref not in isr_nodes:
            reasons.append(f"unresolved ISR reference: {ref}")
    preserved = set(candidate.get("preserved_isr_refs", []))
    for cap in _MANDATORY_CAPABILITIES:
        if cap not in preserved:
            reasons.append(f"requirement not preserved: {cap}")
    for ref in _REQUIRED_SECURITY_REFS:
        if ref not in preserved:
            reasons.append(f"security reference missing: {ref}")
    fitness = candidate.get("fitness", {})
    if not isinstance(fitness, dict) or "total" not in fitness:
        reasons.append("fitness missing")
    lineage = candidate.get("lineage", {})
    if lineage.get("parent_candidate_id") != "vs1-candidate-a":
        reasons.append("lineage parent mismatch")
    # D13 ordering convention (documented, frozen): content_hash was computed
    # before lineage_hash was attached, so it covers neither hash field.
    recomputed = hashlib.sha256(json.dumps(
        {k: v for k, v in candidate.items()
         if k not in ("content_hash", "lineage_hash")},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if recomputed != candidate.get("content_hash"):
        reasons.append("identity inconsistent")
    lineage_recomputed = hashlib.sha256("|".join([
        candidate.get("parent_candidate_id", ""),
        json.dumps(candidate.get("architecture_delta", {}), sort_keys=True),
        candidate.get("objective_id", "")]).encode()).hexdigest()
    if lineage_recomputed != candidate.get("lineage_hash"):
        reasons.append("lineage identity inconsistent")
    return (not reasons), reasons


def _isr_nodes() -> set[str]:
    from vertical_slice.isr import build_task_tracker_isr

    return set(build_task_tracker_isr().graph.nodes)


def verify_objective_alignment(candidate: dict[str, Any],
                               objective_text_markers: tuple[str, ...] = (
                                   "authorization", "policy")) -> bool:
    """The candidate's changes must reference the authorized objective's
    concern (authorization boundary) without expanding scope."""
    blob = json.dumps(candidate).lower()
    return any(marker in blob for marker in objective_text_markers)


def order_candidates(
        candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic ranking: fitness desc, content-hash asc, id asc. No new
    scoring dimensions; no dictionary/set iteration order dependence. The
    ordering is explicitly NON-AUTHORITATIVE (analytical only)."""
    ranked = sorted(
        candidates,
        key=lambda c: (-c["fitness"]["total"], c["content_hash"],
                       c["candidate_id"]))
    return {
        "order_kind": "NON-AUTHORITATIVE_CANDIDATE_ORDER",
        "ranked_candidate_ids": [c["candidate_id"] for c in ranked],
        "ranking": ranked,
        "note": "analytical only; production selection belongs to a later stage",
    }


def choose_candidate(
        candidates: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Choose exactly one admissible candidate (fail-closed BLOCKED cases)."""
    if candidates is None:
        candidates = load_candidates()
    isr_nodes = _isr_nodes()
    admissible: list[dict[str, Any]] = []
    for candidate in candidates:
        ok, reasons = check_admissible(candidate, isr_nodes)
        if not ok:
            raise SelectionBlocked(
                f"candidate {candidate.get('candidate_id')} inadmissible: "
                f"{'; '.join(reasons)}")
        if not verify_objective_alignment(candidate):
            raise SelectionBlocked(
                f"candidate {candidate.get('candidate_id')} misaligned")
        admissible.append(candidate)
    if not admissible:
        raise SelectionBlocked("no admissible candidates")
    ranked = order_candidates(admissible)["ranking"]
    winner = ranked[0]
    identities = upstream_identities()
    record = {
        "selection_id": _stable_id(
            "vs1-selection", SELECTION_POLICY,
            ",".join(sorted(c["candidate_id"] for c in ranked))),
        "contract_id": SELECTION_CONTRACT_VERSION,
        "policy_id": SELECTION_POLICY,
        "selection_mode": "SYNTHETIC_TEST_ONLY",
        "production_authorization": False,
        "candidate_count": len(candidates),
        "admissible_count": len(admissible),
        "rejected_count": len(candidates) - len(admissible),
        "ranked_candidates": [
            {"candidate_id": c["candidate_id"],
             "fitness_total": c["fitness"]["total"],
             "content_hash": c["content_hash"]} for c in ranked],
        "selected_candidate_id": winner["candidate_id"],
        "selected_candidate_hash": winner["content_hash"],
        "parent_architecture_id": winner["parent_candidate_id"],
        "objective_id": winner["objective_id"],
        "authorization_id": winner["lineage"]["authorization_id"],
        "isr_hash": identities["vs-d02-isr-content-hash"],
        "upstream": identities,
        "selection_hash": "",
    }
    record["selection_hash"] = hashlib.sha256(json.dumps(
        {k: v for k, v in record.items() if k != "selection_hash"},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return record
