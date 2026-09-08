"""VS-D08 — evolution decision / authorization gate (decision authority only).

Consumes the frozen D07 interpretation evidence and emits ONE deterministic
decision: NO_CHANGE | REQUEST_MORE_EVIDENCE | AUTHORIZE_EVOLUTION |
REJECT_EVOLUTION, plus a full-provenance decision record.

This module grants authority only. It never mutates requirements, ISR,
candidates, implementation, deployment, or observations, and it never
generates, selects, compiles, or deploys anything. See
folder/VS1_EVOLUTION_DECISION.md.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

DECISION_CONTRACT_VERSION = "vs1-decision-v1"
DECISION_CONTRACT_ID = "vs1-decision-v1"
DECISION_POLICY_VERSION = "vs1-evolution-decision-v1"

_DECISION_CLASSES = (
    "NO_CHANGE",
    "REQUEST_MORE_EVIDENCE",
    "AUTHORIZE_EVOLUTION",
    "REJECT_EVOLUTION",
)

_DISPOSITIONS = ("AUTHORIZE", "DEFER", "REJECT", "NO_ACTION")

_ELIGIBILITY = (
    "eligible_for_evolution_review",
    "requires_more_evidence",
    "insufficient_evidence",
    "contradicted",
    "out_of_scope",
)

_MAGNITUDES = (
    "LOCAL_OPTIMIZATION",
    "BEHAVIORAL_CHANGE",
    "ARCHITECTURAL_CHANGE",
    "REQUIREMENT_CHANGE",
)


class DecisionError(Exception):
    """Fail-closed decision failure (never guess a decision class)."""


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def load_interpretation(
    path: str = "vertical_slice/interpretation_evidence.json",
) -> dict[str, Any]:
    """Load + validate the frozen D07 interpretation artifact (fail-closed)."""
    with open(path, encoding="utf-8") as f:
        evidence = json.load(f)
    for field in ("contract", "claims", "findings", "hypotheses",
                  "contradictions", "provenance", "upstream_identities"):
        if field not in evidence:
            raise DecisionError(f"D07 evidence missing field: {field}")
    if evidence.get("contract") != "vs1-observe-v1":
        raise DecisionError("D07 source-observation contract mismatch")
    if evidence.get("contract_version") != "vs1-interpret-v1":
        raise DecisionError("D07 interpretation contract mismatch")
    if not evidence["hypotheses"]:
        raise DecisionError("D07 evidence has no hypotheses")
    for hypothesis in evidence["hypotheses"]:
        for field in ("hypothesis_id", "statement", "supporting_findings",
                      "falsifiers", "evolution_eligibility", "confidence"):
            if field not in hypothesis:
                raise DecisionError(
                    f"hypothesis missing field: {field}")
        if not hypothesis["falsifiers"]:
            raise DecisionError(
                f"hypothesis {hypothesis.get('hypothesis_id')} lacks a falsifier")
    return evidence


def upstream_identities(evidence: dict[str, Any]) -> dict[str, str]:
    """Recompute frozen upstream identities; cross-check the D07 record."""
    from vertical_slice import implementation as IMPL
    from vertical_slice import candidates as C
    from vertical_slice.deployment import build_contract as deploy_contract
    from vertical_slice import observation as OBS

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
    }
    record_prov = evidence.get("provenance", {})
    for key in ("vs-d01-graph-sha256", "vs-d02-isr-content-hash", "vs-d03-selected"):
        if record_prov.get(key) != expected[key]:
            raise DecisionError(f"upstream drift in D07 provenance: {key}")
    return expected


def evaluate_hypothesis(hypothesis: dict[str, Any],
                        evidence: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one hypothesis to a disposition (AUTHORIZE/DEFER/REJECT/NO_ACTION).

    Policy (vs1-evolution-decision-v1):
      - eligibility != eligible_for_evolution_review → DEFER (or REJECT if
        contradicted/out_of_scope).
      - eligible + hypothesis asserts a bounded, falsifiable sufficiency with
        no evidence-backed problem to fix → NO_ACTION (system acceptable).
      - eligible + evidence-backed problem + bounded objective within slice
        scope + falsifier + no ISR/verification/deployment bypass → AUTHORIZE.
      - contradicted/out_of_scope eligibility, or scope violation → REJECT.
    """
    hid = hypothesis.get("hypothesis_id", "?")
    if not hypothesis.get("falsifiers"):
        raise DecisionError(f"hypothesis {hid} lacks a falsifier")
    eligibility = hypothesis.get("evolution_eligibility")
    if eligibility not in _ELIGIBILITY:
        raise DecisionError(f"hypothesis {hid} has unknown eligibility")
    if eligibility in ("contradicted", "out_of_scope"):
        return {"hypothesis_id": hid, "disposition": "REJECT",
                "rationale": f"eligibility is {eligibility}"}
    if eligibility != "eligible_for_evolution_review":
        return {"hypothesis_id": hid, "disposition": "DEFER",
                "rationale": f"eligibility is {eligibility}; more evidence required"}
    # Eligible: authorize only on an evidence-backed problem with a bounded
    # objective. A sufficiency claim with no problem to fix is NO_ACTION.
    statement = str(hypothesis.get("statement", "")).lower()
    problem_markers = ("failure", "violat", "breach", "defect", "regress",
                       "bypass", "insufficient", "inadequate")
    if not any(marker in statement for marker in problem_markers):
        return {"hypothesis_id": hid, "disposition": "NO_ACTION",
                "rationale": ("eligible and supported, but states sufficiency "
                              "with no evidence-backed problem to fix")}
    return {"hypothesis_id": hid, "disposition": "AUTHORIZE",
            "rationale": "eligible with evidence-backed problem (requires objective)"}


def _check_no_isr_change(hypothesis: dict[str, Any]) -> None:
    blob = json.dumps(hypothesis).lower()
    for marker in ("mutate isr", "rewrite requirement", "change the isr",
                   "modify requirement", "requirement change",
                   "new requirement", "isr semantic"):
        if marker in blob:
            raise DecisionError("hypothesis requires ISR/requirement evolution")


def decide(evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    """Produce the single deterministic evolution decision."""
    if evidence is None:
        evidence = load_interpretation()
    identities = upstream_identities(evidence)
    hypotheses = evidence["hypotheses"]
    evaluations = []
    for hypothesis in sorted(hypotheses, key=lambda h: h["hypothesis_id"]):
        _check_no_isr_change(hypothesis)
        evaluations.append(evaluate_hypothesis(hypothesis, evidence))

    by_disposition: dict[str, list[dict[str, Any]]] = {}
    for evaluation in evaluations:
        by_disposition.setdefault(evaluation["disposition"], []).append(evaluation)

    authorized = by_disposition.get("AUTHORIZE", [])
    no_action = by_disposition.get("NO_ACTION", [])
    deferred = by_disposition.get("DEFER", [])
    rejected = by_disposition.get("REJECT", [])

    contradictions = evidence.get("contradictions", [])
    if contradictions:
        decision, rationale = "REJECT_EVOLUTION", (
            f"{len(contradictions)} unresolved contradiction(s); "
            "evolution cannot be authorized on conflicted evidence")
        objective = None
    elif authorized:
        decision, rationale = "AUTHORIZE_EVOLUTION", (
            f"{len(authorized)} hypothesi(s) authorize bounded evolution")
        objective = _build_objective(authorized[0], evidence, identities)
    elif no_action and not deferred:
        decision, rationale = "NO_CHANGE", (
            "current system is acceptable under current evidence; "
            "no evidence-backed problem to fix")
        objective = None
    elif no_action:
        # Supported sufficiency coexists with deferred items: the system is
        # acceptable on current evidence; nothing warrants change.
        decision, rationale = "NO_CHANGE", (
            "current system is acceptable under current evidence; "
            f"{len(deferred)} hypothesi(s) deferred pending more evidence")
        objective = None
    elif deferred:
        decision, rationale = "REQUEST_MORE_EVIDENCE", (
            f"{len(deferred)} hypothesi(s) require more evidence; "
            "no actionable finding")
        objective = None
    else:
        decision, rationale = "REJECT_EVOLUTION", "no evaluable hypotheses"
        objective = None

    if decision not in _DECISION_CLASSES:
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
        "change_magnitude": objective["magnitude"] if objective else "NONE",
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
        "required_next_stage": ("NONE — decision is terminal for D08"
                                if objective is None
                                else "VS-D09 candidate evolution"),
        "required_evidence": ("none" if objective is None
                              else "falsifier experiment + reverification"),
        "rollback_requirement": ("not-applicable (no change authorized)"
                                 if objective is None
                                 else "previous known-good state restorable"),
        "verification_requirement": ("not-applicable (no change authorized)"
                                     if objective is None
                                     else "reverification before acceptance"),
        "deployment_requirement": ("not-applicable (no change authorized)"
                                   if objective is None
                                   else "controlled deployment before production"),
        "observation_requirement": ("not-applicable (no change authorized)"
                                    if objective is None
                                    else "post-deployment observation"),
        "uncertainties": sorted({u for h in hypotheses
                                 for u in h.get("uncertainties", [])} or
                                ["single-run evidence; see D07 uncertainties"]),
        "provenance": dict(evidence.get("provenance", {})),
    }
    record["content_hash"] = hashlib.sha256(json.dumps(
        {k: v for k, v in record.items() if k != "content_hash"},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return record


def _classify_magnitude(hypothesis: dict[str, Any]) -> str:
    """Classify change magnitude from the hypothesis text (fail-closed).

    REQUIREMENT_CHANGE is never authorized in VS1; anything needing it raises
    REQUIRES_ISR_EVOLUTION instead of guessing a smaller magnitude.
    """
    blob = json.dumps({
        "statement": hypothesis.get("statement", ""),
        "scope": hypothesis.get("scope", ""),
        "motivation": hypothesis.get("motivation", ""),
    }).lower()
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


def _build_objective(evaluation: dict[str, Any], evidence: dict[str, Any],
                     identities: dict[str, str]) -> dict[str, Any]:
    """Construct an Evolution Objective Record (only for AUTHORIZE). Describes
    WHAT should improve, never HOW code should change."""
    hypotheses = {h["hypothesis_id"]: h for h in evidence["hypotheses"]}
    hypothesis = hypotheses[evaluation["hypothesis_id"]]
    return {
        "objective_id": _stable_id("vs1-objective", evaluation["hypothesis_id"]),
        "source_hypothesis_id": evaluation["hypothesis_id"],
        "problem_statement": hypothesis["statement"],
        "desired_property": "to be specified by the evolution phase within scope",
        "current_known_state": "incumbent vs1-candidate-a behavior per D06 evidence",
        "target_property": "bounded improvement with falsifier intact",
        "success_criteria": hypothesis.get("acceptance_conditions", []),
        "falsification_criteria": hypothesis.get("falsifiers", []),
        "scope": hypothesis.get("scope", ""),
        "out_of_scope": ["requirement changes", "ISR semantic changes"],
        "constraints": ["no ISR bypass", "no verification bypass"],
        "required_evidence": ["falsifier experiment", "reverification"],
        "rollback_requirement": "previous known-good state restorable",
        "verification_requirement": "reverification before acceptance",
        "deployment_requirement": "controlled deployment before production",
        "observation_requirement": "post-deployment observation",
        "magnitude": _classify_magnitude(hypothesis),
    }
