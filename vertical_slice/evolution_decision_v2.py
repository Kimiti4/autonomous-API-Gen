"""VS-D12 — evolution decision / authorization gate (authority only).

Consumes the frozen D11 v2 interpretation and emits ONE deterministic
decision: AUTHORIZE_EVOLUTION | NO_CHANGE | REJECT_EVOLUTION (+ BLOCKED on
integrity failure). Grants authority only; never generates candidates,
mutates architecture, implements, deploys, or acquires evidence. See
folder/VS1_EVOLUTION_DECISION_V2.md.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

DECISION_CONTRACT_VERSION = "vs1-decision-v2"
DECISION_CONTRACT_ID = "vs1-decision-v2"
DECISION_POLICY_VERSION = "vs1-evolution-decision-v2"

_DECISIONS = (
    "AUTHORIZE_EVOLUTION",
    "NO_CHANGE",
    "REJECT_EVOLUTION",
    "BLOCKED",
)

_MAGNITUDES = (
    "LOCAL_OPTIMIZATION",
    "BEHAVIORAL_CHANGE",
    "ARCHITECTURAL_CHANGE",
)


class DecisionError(Exception):
    """Fail-closed decision failure (never guess a decision class)."""


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def load_d11(path: str = "vertical_slice/interpretation_v2_evidence.json",
             ) -> dict[str, Any]:
    """Load + validate the frozen D11 artifact (fail-closed, read-only)."""
    try:
        with open(path, encoding="utf-8") as f:
            evidence = json.load(f)
    except (OSError, ValueError) as exc:
        raise DecisionError(f"D11 evidence unavailable: {exc}")
    if not isinstance(evidence, dict):
        raise DecisionError("D11 evidence malformed")
    for field in ("contract", "claims", "findings", "hypotheses",
                  "contradictions", "provenance", "upstream_identities"):
        if field not in evidence:
            raise DecisionError(f"D11 evidence missing field: {field}")
    if evidence.get("contract") != "vs1-interpretation-v2":
        raise DecisionError("D11 contract mismatch")
    for hypothesis in evidence["hypotheses"]:
        for field in ("hypothesis_id", "updated_status", "falsifier_status",
                      "evolution_relevance", "supporting_findings", "falsifier"):
            if field not in hypothesis:
                raise DecisionError(
                    f"D11 hypothesis missing field: {field}")
    return evidence


def upstream_identities(d11: dict[str, Any]) -> dict[str, str]:
    """Recompute frozen upstream identities D01–D11 (fail-closed)."""
    from vertical_slice import implementation as IMPL
    from vertical_slice import candidates as C
    from vertical_slice.deployment import build_contract as deploy_contract
    from vertical_slice import observation as OBS
    from vertical_slice import evolution_decision as DEC
    from vertical_slice import evidence_acquisition as ACQ
    from vertical_slice import evidence_runner as RUN

    identity = IMPL.frozen_input_identity()
    contract = deploy_contract()
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
        "vs-d08-policy": DEC.decide()["policy_id"],
        "vs-d09-policy": ACQ.run_gate()["policy"],
        "vs-d09-outcome": ACQ.run_gate()["outcome"],
        "vs-d10-contract": "vs1-evidence-run-v1",
        "vs-d11-contract": "vs1-interpretation-v2",
    }
    if expected["vs-d08-decision"] != "NO_CHANGE":
        raise DecisionError("D08 historical decision drift")
    _ = RUN.RUN_CONTRACT_VERSION  # D10 runner present; not executed here
    return expected


def _problem_in(hypothesis: dict[str, Any]) -> dict[str, Any] | None:
    """Return the evidence-backed problem block if the hypothesis carries
    one, else None. A sufficiency statement without a problem is not one."""
    problem = hypothesis.get("problem")
    if not problem:
        return None
    for field in ("statement", "evidence_basis", "scope", "desired_outcome",
                  "success_measure"):
        if field not in problem:
            raise DecisionError(
                f"problem block missing field: {field}")
    return problem


def _classify_magnitude(problem: dict[str, Any]) -> str:
    blob = json.dumps(problem).lower()
    if any(marker in blob for marker in (
            "requirement change", "new requirement", "isr semantic",
            "rewrite requirement", "change the isr")):
        raise DecisionError("REQUIRES_ISR_EVOLUTION: out of VS1 slice scope")
    if any(marker in blob for marker in (
            "service boundary", "architecture", "topology", "decompos")):
        return "ARCHITECTURAL_CHANGE"
    if any(marker in blob for marker in (
            "behavior", "endpoint", "validation", "error handling")):
        return "BEHAVIORAL_CHANGE"
    return "LOCAL_OPTIMIZATION"


def _validate_structure(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    """Fail-closed structural validation of the D11 evidence mapping."""
    hypotheses = evidence.get("hypotheses")
    if not isinstance(hypotheses, list) or not hypotheses:
        raise DecisionError("D11 evidence has no hypotheses")
    for hypothesis in hypotheses:
        for field in ("hypothesis_id", "updated_status", "falsifier_status",
                      "evolution_relevance", "supporting_findings", "falsifier"):
            if field not in hypothesis:
                raise DecisionError(
                    f"D11 hypothesis missing field: {field}")
        if status_of(hypothesis) not in ("SUFFICIENTLY_SUPPORTED",
                                         "REMAINS_WEAKLY_SUPPORTED",
                                         "REQUIRES_MORE_EVIDENCE",
                                         "CONTRADICTED"):
            raise DecisionError("D11 hypothesis has invalid state")
        if not hypothesis["falsifier"]:
            raise DecisionError(
                f"D11 hypothesis {hypothesis.get('hypothesis_id')} lacks a falsifier")
    return hypotheses


def status_of(hypothesis: dict[str, Any]) -> str:
    return str(hypothesis.get("updated_status"))


def _blocked_record(reason: str, evidence: dict[str, Any],
                    identities: dict[str, str]) -> dict[str, Any]:
    record = {
        "decision_id": _stable_id("vs1-decision", DECISION_POLICY_VERSION,
                                  "blocked", reason),
        "contract_id": DECISION_CONTRACT_ID,
        "policy_id": DECISION_POLICY_VERSION,
        "upstream": identities,
        "reviewed_hypotheses": sorted(
            h.get("hypothesis_id", "?") for h in evidence.get("hypotheses", [])
            if isinstance(h, dict)),
        "evaluations": [],
        "decision": "BLOCKED",
        "decision_rationale": reason,
        "authorized_objective": None,
        "change_magnitude": "NONE",
        "constraints": sorted([
            "D01 requirements preserved",
            "D02 ISR semantics preserved",
        ]),
        "required_next_stage": "NONE — resolve the blocker first",
        "uncertainties": ["blocked: see rationale"],
        "provenance": dict(evidence.get("provenance", {})),
    }
    record["content_hash"] = hashlib.sha256(json.dumps(
        {k: v for k, v in record.items() if k != "content_hash"},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return record


def evaluate_hypothesis(hypothesis: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one D11 hypothesis to a decision contribution."""
    hid = hypothesis.get("hypothesis_id", "?")
    for field in ("updated_status", "falsifier_status", "evolution_relevance",
                  "supporting_findings", "falsifier"):
        if field not in hypothesis:
            raise DecisionError(f"D11 hypothesis missing field: {field}")
    if not hypothesis["falsifier"]:
        raise DecisionError(f"hypothesis {hid} lacks a falsifier")
    status = hypothesis.get("updated_status")
    relevance = hypothesis.get("evolution_relevance")
    falsifier_state = hypothesis.get("falsifier_status")
    if status not in ("SUFFICIENTLY_SUPPORTED", "REMAINS_WEAKLY_SUPPORTED",
                      "REQUIRES_MORE_EVIDENCE", "CONTRADICTED"):
        raise DecisionError(f"hypothesis {hid} has invalid state: {status}")
    if falsifier_state not in ("NOT_TRIGGERED", "TRIGGERED", "UNDETERMINED"):
        raise DecisionError(f"hypothesis {hid} has invalid falsifier state")
    if status == "CONTRADICTED" or falsifier_state == "TRIGGERED":
        return {"hypothesis_id": hid, "disposition": "REJECT",
                "rationale": "contradicted or falsifier triggered"}
    if relevance != "ELIGIBLE_FOR_EVOLUTION_REVIEW":
        return {"hypothesis_id": hid, "disposition": "DEFER",
                "rationale": f"relevance is {relevance}"}
    problem = _problem_in(hypothesis)
    if problem is None:
        return {"hypothesis_id": hid, "disposition": "NO_ACTION",
                "rationale": ("eligible and supported, but no evidence-backed "
                              "engineering problem to fix")}
    magnitude = _classify_magnitude(problem)
    return {"hypothesis_id": hid, "disposition": "AUTHORIZE",
            "rationale": "eligible with evidence-backed problem",
            "problem": dict(problem), "magnitude": magnitude}


def _build_objective(evaluation: dict[str, Any],
                     hypothesis: dict[str, Any]) -> dict[str, Any]:
    problem = evaluation["problem"]
    return {
        "objective_id": _stable_id("vs1-objective", evaluation["hypothesis_id"],
                                   problem["statement"]),
        "magnitude": _classify_magnitude(problem),
        "problem_statement": problem["statement"],
        "evidence_basis": problem["evidence_basis"],
        "affected_scope": problem.get("scope", ""),
        "desired_outcome": problem["desired_outcome"],
        "success_measure": problem["success_measure"],
        "constraints": [
            "D01 requirements preserved",
            "D02 ISR semantics preserved",
            "security policies preserved",
            "verification gates preserved",
            "rollback capability required",
        ],
        "risk": problem.get("risk", "bounded loopback evaluation"),
        "rollback_requirement": "previous known-good state restorable",
        "verification_requirement": "reverification before acceptance",
        "deployment_requirement": "controlled deployment before production",
        "observation_requirement": "post-deployment observation",
    }


def _build_authorization(objective: dict[str, Any], decision_id: str,
                         evidence: dict[str, Any]) -> dict[str, Any]:
    refs = {
        "hypothesis_refs": [objective["source_hypothesis_id"]],
    }
    return {
        "authorization_id": _stable_id("vs1-authorization", decision_id),
        "source_decision": decision_id,
        "objective_id": objective["objective_id"],
        "evidence_refs": sorted(objective["evidence_basis"]),
        "finding_refs": sorted(objective.get("finding_refs", [])),
        "hypothesis_refs": refs["hypothesis_refs"],
        "scope": objective.get("affected_scope", ""),
        "invariants": [
            "requirements immutable",
            "ISR immutable",
            "verification mandatory",
            "deployment provenance mandatory",
        ],
        "allowed_change_surface": ["architecture within stated scope"],
        "forbidden_change_surface": [
            "requirements mutation",
            "unrelated subsystem changes",
            "security weakening",
            "ISR corruption",
            "unverified deployment",
            "evidence deletion",
            "verification bypass",
        ],
        "rollback_strategy": objective["rollback_requirement"],
        "verification_gates": [objective["verification_requirement"]],
        "deployment_gate": objective["deployment_requirement"],
        "observation_gate": objective["observation_requirement"],
        "success_criteria": [objective["success_measure"]],
    }


def decide(evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    """Produce the single deterministic evolution decision."""
    if evidence is None:
        evidence = load_d11()
    try:
        hypotheses = _validate_structure(evidence)
        identities = upstream_identities(evidence)
    except DecisionError as exc:
        # Structural failure of the evidence mapping itself: fail closed
        # with a BLOCKED record, never a guessed decision.
        try:
            partial = upstream_identities(evidence)
        except DecisionError:
            partial = {}
        return _blocked_record(str(exc), evidence, partial)
    evaluations = []
    for hypothesis in sorted(hypotheses, key=lambda h: h["hypothesis_id"]):
        evaluations.append(evaluate_hypothesis(hypothesis))

    by_disposition: dict[str, list[dict[str, Any]]] = {}
    for evaluation in evaluations:
        by_disposition.setdefault(evaluation["disposition"], []).append(evaluation)

    hypotheses_by_id = {h["hypothesis_id"]: h for h in hypotheses}
    authorized = by_disposition.get("AUTHORIZE", [])
    rejected = by_disposition.get("REJECT", [])

    if rejected and not authorized:
        decision, rationale = "REJECT_EVOLUTION", (
            f"{len(rejected)} hypothesi(s) contradicted or falsified")
        objective = None
        authorization = None
    elif authorized:
        first = authorized[0]
        hypothesis = hypotheses_by_id[first["hypothesis_id"]]
        objective = _build_objective(
            {**first, "problem": _problem_in(hypothesis)}, hypothesis)
        objective["source_hypothesis_id"] = first["hypothesis_id"]
        objective["finding_refs"] = sorted(hypothesis.get("supporting_findings", []))
        objective["evidence_basis"] = sorted(hypothesis.get("supporting_observations", []))
        decision_id = _stable_id(
            "vs1-decision", DECISION_POLICY_VERSION,
            ",".join(sorted(h["hypothesis_id"] for h in hypotheses)), "AUTHORIZE")
        authorization = _build_authorization(objective, decision_id, evidence)
        decision, rationale = "AUTHORIZE_EVOLUTION", (
            f"{len(authorized)} hypothesi(s) authorize bounded evolution")
    elif any(e["disposition"] == "NO_ACTION" for e in evaluations):
        decision, rationale = "NO_CHANGE", (
            "current system is acceptable under current evidence; "
            "no evidence-backed problem to fix")
        objective = None
        authorization = None
    else:
        decision, rationale = "NO_CHANGE", (
            "no actionable finding; system remains unchanged")
        objective = None
        authorization = None

    if decision not in ("AUTHORIZE_EVOLUTION", "NO_CHANGE", "REJECT_EVOLUTION"):
        raise DecisionError(f"ambiguous decision class: {decision}")
    record = {
        "decision_id": _stable_id(
            "vs1-decision", DECISION_POLICY_VERSION,
            ",".join(sorted(h["hypothesis_id"] for h in hypotheses)), decision),
        "contract_id": DECISION_CONTRACT_ID,
        "policy_id": DECISION_POLICY_VERSION,
        "upstream": identities,
        "reviewed_hypotheses": sorted(h["hypothesis_id"] for h in hypotheses),
        "evaluations": sorted(evaluations, key=lambda e: e["hypothesis_id"]),
        "decision": decision,
        "decision_rationale": rationale,
        "authorized_objective": objective,
        "change_magnitude": (objective.get("magnitude") if objective else "NONE"),
        "constraints": sorted([
            "D01 requirements preserved",
            "D02 ISR semantics preserved",
            "security policies preserved",
            "data ownership preserved",
            "API contracts preserved unless explicitly evolved",
            "verification gates preserved",
            "deployment provenance preserved",
            "observation provenance preserved",
            "rollback capability required for any future evolution",
        ]),
        "required_next_stage": ("NONE — decision is terminal for D12"
                                if objective is None
                                else "VS-D13 candidate evolution"),
        "uncertainties": sorted({u for h in hypotheses
                                 for u in h.get("remaining_uncertainties", [])}),
        "provenance": dict(evidence.get("provenance", {})),
    }
    if objective is not None:
        record["authorized_objective"] = objective
        record["authorization"] = authorization
        record["change_magnitude"] = objective["magnitude"]
    record["content_hash"] = hashlib.sha256(json.dumps(
        {k: v for k, v in record.items() if k != "content_hash"},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return record
