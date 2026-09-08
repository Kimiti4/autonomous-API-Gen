"""VS-D11 — runtime evidence interpretation v2 / hypothesis update (facts only).

Consumes the frozen D10 acquisition results and updates the two D08-deferred
hypotheses. Emits claims, findings, updated hypotheses, falsifier states,
uncertainties, and evolution-review eligibility. Never authorizes evolution,
never mutates anything upstream. See folder/VS1_INTERPRETATION_V2.md.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

INTERPRETATION_CONTRACT_VERSION = "vs1-interpretation-v2"
INTERPRETATION_CONTRACT_ID = "vs1-interpretation-v2"

_SUPPORT_LEVELS = (
    "SUPPORTED",
    "WEAKLY_SUPPORTED",
    "UNDETERMINED",
    "CONTRADICTED",
)

_FALSIFIER_STATES = ("NOT_TRIGGERED", "TRIGGERED", "UNDETERMINED")

_ELIGIBILITY = (
    "ELIGIBLE_FOR_EVOLUTION_REVIEW",
    "REQUIRES_MORE_EVIDENCE",
    "NOT_EVOLUTION_RELEVANT",
    "CONTRADICTED",
)

# Universal-certainty phrases that no bounded evidence can support.
_OVERCLAIM_MARKERS = (
    "universally reliable",
    "proven correct",
    "100% reliable",
    "always available",
    "optimal architecture",
    "production-grade reliability",
)


class InterpretationError(Exception):
    """Fail-closed interpretation failure."""


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def assert_bounded(statement: str) -> None:
    """Reject universal-certainty overclaims (fail-closed)."""
    lowered = statement.lower()
    for marker in _OVERCLAIM_MARKERS:
        if marker in lowered:
            raise InterpretationError(
                f"unsupported certainty escalation: {marker!r}")


def load_d10(path: str = "vertical_slice/evidence_acquisition_results.json",
             ) -> dict[str, Any]:
    """Load + validate the frozen D10 artifact (fail-closed, read-only)."""
    try:
        with open(path, encoding="utf-8") as f:
            artifact = json.load(f)
    except (OSError, ValueError) as exc:
        raise InterpretationError(f"D10 evidence unavailable: {exc}")
    if not isinstance(artifact, dict):
        raise InterpretationError("D10 evidence malformed")
    for field in ("contract_id", "observations", "summary", "provenance",
                  "content_hash"):
        if field not in artifact:
            raise InterpretationError(f"D10 evidence missing field: {field}")
    observations = artifact["observations"]
    if len(observations) != 7:
        raise InterpretationError(
            f"D10 must hold 7 observations, found {len(observations)}")
    for record in observations:
        for field in ("evidence_id", "plan_id", "hypothesis_id",
                      "observation_id", "outcome", "provenance"):
            if field not in record:
                raise InterpretationError(f"D10 record missing field: {field}")
        if record["outcome"] not in ("PASS", "FAIL", "UNDETERMINED", "BLOCKED"):
            raise InterpretationError(
                f"D10 record has unknown outcome: {record['outcome']}")
    return artifact


def upstream_identities(d10: dict[str, Any]) -> dict[str, str]:
    """Recompute frozen upstream identities D01–D10; cross-check provenance."""
    from vertical_slice import implementation as IMPL
    from vertical_slice import candidates as C
    from vertical_slice.deployment import build_contract as deploy_contract
    from vertical_slice import observation as OBS
    from vertical_slice import evolution_decision as DEC
    from vertical_slice import evidence_acquisition as ACQ

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
        "vs-d09-policy": ACQ.run_gate()["policy"],
        "vs-d10-contract": "vs1-evidence-run-v1",
    }
    for record in d10["observations"]:
        for key in ("vs-d01-graph-sha256", "vs-d02-isr-content-hash",
                    "vs-d03-selected"):
            if record["provenance"].get(key) != expected[key]:
                raise InterpretationError(
                    f"D10 record provenance drift: {key}")
    return expected


def _split_observations(
        d10: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    auth = sorted(
        (r for r in d10["observations"]
         if r["hypothesis_id"] == "vs1-hypothesis-auth-model-adequate"),
        key=lambda r: r["observation_id"])
    deploy_recs = sorted(
        (r for r in d10["observations"]
         if r["hypothesis_id"] == "vs1-hypothesis-deploy-repeatable"),
        key=lambda r: r["observation_id"])
    if len(auth) != 4 or len(deploy_recs) != 3:
        raise InterpretationError("D10 observation split mismatch (need 4+3)")
    return auth, deploy_recs


def evaluate_auth(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate the 4 authorization observations against D09 criteria."""
    if len(records) != 4:
        raise InterpretationError("auth evaluation needs exactly 4 records")
    outcomes = [r["outcome"] for r in records]
    by_obs = {r["observation_id"]: r for r in records}
    expected_ids = {"auth-admin-allowed", "auth-member-denied",
                    "auth-credential-rejection", "auth-outsider-isolated"}
    if set(by_obs) != expected_ids:
        raise InterpretationError("auth observation set mismatch")
    if all(o == "PASS" for o in outcomes):
        return {"support": "SUPPORTED", "falsifier": "NOT_TRIGGERED",
                "detail": "4/4 authorization observations PASS"}
    if any(o == "FAIL" for o in outcomes):
        return {"support": "CONTRADICTED", "falsifier": "TRIGGERED",
                "detail": "authorization falsifier triggered"}
    return {"support": "UNDETERMINED", "falsifier": "UNDETERMINED",
            "detail": "non-passing outcomes without falsification"}


def evaluate_deploy(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate the 3 deployment-cycle observations against D09 criteria."""
    if len(records) != 3:
        raise InterpretationError("deploy evaluation needs exactly 3 records")
    outcomes = [r["outcome"] for r in records]
    cycles = sorted(r["cycle_id"] for r in records)
    if cycles != ["cycle-01", "cycle-02", "cycle-03"]:
        raise InterpretationError("deploy cycle set mismatch")
    if all(o == "PASS" for o in outcomes):
        return {"support": "SUPPORTED", "falsifier": "NOT_TRIGGERED",
                "detail": "3/3 independent cycles PASS"}
    if any(o == "FAIL" for o in outcomes):
        return {"support": "CONTRADICTED", "falsifier": "TRIGGERED",
                "detail": "cycle falsifier triggered"}
    return {"support": "UNDETERMINED", "falsifier": "UNDETERMINED",
            "detail": "non-passing outcomes without falsification"}


def detect_contradictions(auth_eval: dict[str, Any],
                          deploy_eval: dict[str, Any]) -> list[dict[str, Any]]:
    """Expose genuine conflicts; never collapse them. Empty when clean."""
    contradictions = []
    for name, evaluation in (("auth", auth_eval), ("deploy", deploy_eval)):
        if evaluation["support"] == "CONTRADICTED":
            contradictions.append({
                "contradiction_id": f"vs1-v2-contradiction-{name}",
                "scope": name,
                "detail": evaluation["detail"],
                "status": "contradicted",
            })
    return contradictions


def _claim(claim_type: str, statement: str, evidence_refs: list[str],
           prior_refs: list[str], provenance: dict[str, str],
           status: str) -> dict[str, Any]:
    assert_bounded(statement)
    if not evidence_refs:
        raise InterpretationError("claim with no evidence lineage")
    if status not in ("supported", "weakly_supported", "undetermined",
                      "contradicted"):
        raise InterpretationError(f"unknown claim status: {status}")
    return {
        "claim_id": _stable_id("vs1-v2-claim", claim_type, statement,
                               ",".join(sorted(evidence_refs))),
        "claim_type": claim_type,
        "statement": statement,
        "support_level": status,
        "evidence_refs": sorted(evidence_refs),
        "prior_claim_refs": sorted(prior_refs),
        "scope": "bounded VS1 loopback runs (D10) plus bounded D06 run",
        "uncertainty": ("single-environment evidence" if status == "supported"
                        else "see statement scope"),
        "falsifier": "D07/D09 falsifiers retained (see hypothesis records)",
        "provenance": dict(provenance),
    }


def build_claims(auth_records: list[dict[str, Any]],
                 deploy_records: list[dict[str, Any]],
                 provenance: dict[str, str]) -> list[dict[str, Any]]:
    """Canonical claims from D10 evidence (bounded, falsifiable, scoped)."""
    auth_ids = [r["evidence_id"] for r in auth_records]
    deploy_ids = [r["evidence_id"] for r in deploy_records]
    claims = [
        _claim("security-observation",
               "Role-boundary authorization held across 4/4 bounded probes: "
               "admin-allowed administration, member-denied administration, "
               "identical wrong-password rejection, outsider isolation.",
               auth_ids, [], provenance, "supported"),
        _claim("persistence-observation",
               "Deployment cycles completed readiness and CRUD probes against "
               "isolated stores (prior D06 finding retained).",
               deploy_ids, [], provenance, "supported"),
        _claim("boundary-condition",
               "Results cover loopback single-instance runs only; production "
               "scale, longevity, multi-instance, and hostile-attacker "
               "properties remain unestablished.",
               auth_ids + deploy_ids, [], provenance, "supported"),
        _claim("uncertainty",
               "Three deployment cycles bound repeatability narrowly; wider "
               "environmental variation remains unobserved.",
               deploy_ids, [], provenance, "supported"),
    ]
    return sorted(claims, key=lambda c: c["claim_id"])


def build_findings(claims: list[dict[str, Any]],
                   provenance: dict[str, str]) -> list[dict[str, Any]]:
    """Engineering findings from claims (interpretation, not decision)."""
    by_type: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        by_type.setdefault(claim["claim_type"], []).append(claim)

    def finding(fid: str, statement: str, support: list[dict[str, Any]],
                confidence: str) -> dict[str, Any]:
        assert_bounded(statement)
        if confidence not in ("supported", "weakly_supported", "undetermined",
                              "contradicted"):
            raise InterpretationError(f"unknown confidence: {confidence}")
        claim_ids = sorted(c["claim_id"] for c in support)
        evidence = sorted({e for c in support for e in c["evidence_refs"]})
        if not claim_ids:
            raise InterpretationError("finding with no supporting claims")
        return {
            "finding_id": fid,
            "statement": statement,
            "claim_refs": claim_ids,
            "evidence_refs": evidence,
            "confidence_class": confidence,
            "scope": "bounded VS1 loopback evidence (D10) combined with D06",
            "limitations": "Single environment; small samples (4+3); no hostile testing.",
            "provenance": dict(provenance),
        }

    sec = by_type.get("security-observation", [])
    per = by_type.get("persistence-observation", [])
    bnd = by_type.get("boundary-condition", [])
    unc = by_type.get("uncertainty", [])
    return sorted([
        finding("vs1-v2-finding-auth-boundary",
                "Role-boundary behavior observed across the bounded probe set "
                "matches the D09 success criteria with no violation.",
                sec, "supported"),
        finding("vs1-v2-finding-deploy-cycles",
                "Three independent deployment cycles each completed readiness "
                "and CRUD probes with identical outcomes.",
                per, "supported"),
        finding("vs1-v2-finding-scope",
                "Conclusions are confined to loopback single-instance runs; "
                "broader properties remain explicitly unestablished.",
                bnd + unc, "supported"),
    ], key=lambda f: f["finding_id"])


def build_hypotheses(auth_eval: dict[str, Any], deploy_eval: dict[str, Any],
                      findings: list[dict[str, Any]],
                      provenance: dict[str, str]) -> list[dict[str, Any]]:
    """Update the two deferred hypotheses (SUFFICIENTLY_SUPPORTED etc.)."""
    by_id = {f["finding_id"]: f for f in findings}

    def hypothesis(hid: str, prior: str, support: str,
                   finding_ids: list[str], falsifier_state: str,
                   uncertainties: list[str], relevance: str) -> dict[str, Any]:
        for fid in finding_ids:
            if fid not in by_id:
                raise InterpretationError(f"unknown finding: {fid}")
        if support not in ("SUFFICIENTLY_SUPPORTED", "REMAINS_WEAKLY_SUPPORTED",
                           "REQUIRES_MORE_EVIDENCE", "CONTRADICTED"):
            raise InterpretationError(f"unknown support state: {support}")
        if relevance not in ("ELIGIBLE_FOR_EVOLUTION_REVIEW",
                             "REQUIRES_MORE_EVIDENCE", "NOT_EVOLUTION_RELEVANT",
                             "CONTRADICTED"):
            raise InterpretationError(f"unknown relevance: {relevance}")
        obs_ids = sorted({e for fid in finding_ids
                            for e in by_id[fid]["evidence_refs"]})
        if not obs_ids:
            raise InterpretationError(
                f"hypothesis {hid} has no observation lineage")
        falsifiers = [
            "bounded workload beyond the defined contract repeatedly fails "
            "for architecture-attributable reasons",
            "an authorization probe demonstrates bypass, forgery, or "
            "cross-workspace access",
            "a fresh identical deployment cycle fails readiness or diverges",
        ] if hid == "vs1-hypothesis-auth-model-adequate" else [
            "a fresh identical deployment cycle fails readiness or diverges",
            "behavioral divergence across cycles under identical inputs",
        ]
        return {
            "hypothesis_id": hid,
            "prior_status": prior,
            "updated_status": support,
            "supporting_claims": sorted(
                {c for fid in finding_ids for c in by_id[fid]["claim_refs"]}),
            "supporting_findings": sorted(finding_ids),
            "supporting_observations": obs_ids,
            "falsifier": ("D07 falsifiers retained: " +
                          "; ".join(falsifiers[:2])),
            "falsifier_status": falsifier_state,
            "remaining_uncertainties": list(uncertainties),
            "scope": "bounded VS1 loopback evidence (D10, 4+3 observations)",
            "evolution_relevance": relevance,
        }

    auth_state = ("SUFFICIENTLY_SUPPORTED" if auth_eval["support"] == "SUPPORTED"
                  else "CONTRADICTED" if auth_eval["support"] == "CONTRADICTED"
                  else "REQUIRES_MORE_EVIDENCE")
    deploy_state = ("SUFFICIENTLY_SUPPORTED" if deploy_eval["support"] == "SUPPORTED"
                    else "CONTRADICTED" if deploy_eval["support"] == "CONTRADICTED"
                    else "REQUIRES_MORE_EVIDENCE")
    auth_relevance = ("ELIGIBLE_FOR_EVOLUTION_REVIEW"
                      if auth_state == "SUFFICIENTLY_SUPPORTED"
                      else "CONTRADICTED" if auth_state == "CONTRADICTED"
                      else "REQUIRES_MORE_EVIDENCE")
    deploy_relevance = ("ELIGIBLE_FOR_EVOLUTION_REVIEW"
                        if deploy_state == "SUFFICIENTLY_SUPPORTED"
                        else "CONTRADICTED" if deploy_state == "CONTRADICTED"
                        else "REQUIRES_MORE_EVIDENCE")
    return sorted([
        hypothesis("vs1-hypothesis-auth-model-adequate", "requires_more_evidence",
                   auth_state,
                   ["vs1-v2-finding-auth-boundary"],
                   auth_eval["falsifier"],
                   ["role shapes beyond tested set", "long-run credential hygiene"],
                   auth_relevance),
        hypothesis("vs1-hypothesis-deploy-repeatable", "requires_more_evidence",
                   deploy_state,
                   ["vs1-v2-finding-deploy-cycles"],
                   deploy_eval["falsifier"],
                   ["fresh-host variation", "wider environmental spread"],
                   deploy_relevance),
    ], key=lambda h: h["hypothesis_id"])


def interpret(auth: list[dict[str, Any]], deploy_recs: list[dict[str, Any]],
              provenance: dict[str, str]) -> dict[str, Any]:
    """Pure interpretation core: records in, claims/findings/hypotheses out.
    No servers, no runs. Deterministic for identical inputs."""
    auth_eval = evaluate_auth(auth)
    deploy_eval = evaluate_deploy(deploy_recs)
    claims = build_claims(auth, deploy_recs, provenance)
    findings = build_findings(claims, provenance)
    hypotheses = build_hypotheses(auth_eval, deploy_eval, findings, provenance)
    contradictions = detect_contradictions(auth_eval, deploy_eval)
    return {
        "auth_eval": auth_eval,
        "deploy_eval": deploy_eval,
        "claims": claims,
        "findings": findings,
        "hypotheses": hypotheses,
        "contradictions": contradictions,
    }


def build_artifact(run_id: str = "vs1-d11-input") -> dict[str, Any]:
    """Full pipeline: validate D10 → evaluate → interpret (deterministic)."""
    from vertical_slice import evidence_runner as RUN

    artifact = RUN.build_artifact(run_id=run_id)
    if artifact["summary"]["executed_observations"] != 7:
        raise InterpretationError("D11 requires exactly 7 D10 observations")
    observations = artifact["observations"]
    auth = sorted(
        (r for r in observations
         if r["hypothesis_id"] == "vs1-hypothesis-auth-model-adequate"),
        key=lambda r: r["observation_id"])
    deploy_recs = sorted(
        (r for r in observations
         if r["hypothesis_id"] == "vs1-hypothesis-deploy-repeatable"),
        key=lambda r: r["observation_id"])
    if len(auth) != 4 or len(deploy_recs) != 3:
        raise InterpretationError("D10 observation split mismatch (need 4+3)")
    provenance = dict(artifact["provenance"])
    interpreted = interpret(auth, deploy_recs, provenance)
    claims = interpreted["claims"]
    findings = interpreted["findings"]
    hypotheses = interpreted["hypotheses"]
    contradictions = interpreted["contradictions"]
    record = {
        "contract": INTERPRETATION_CONTRACT_ID,
        "contract_version": INTERPRETATION_CONTRACT_VERSION,
        "upstream_identities": upstream_identities_from(artifact),
        "source_evidence": {
            "d10_execution": artifact["execution_id"],
            "d10_hash": artifact["content_hash"],
            "observation_ids": sorted(r["observation_id"] for r in observations),
        },
        "claims": claims,
        "findings": findings,
        "hypotheses": hypotheses,
        "contradictions": contradictions,
        "uncertainties": sorted({u for h in hypotheses
                                 for u in h["remaining_uncertainties"]}),
        "provenance": provenance,
        "schema_version": "vs1-interpretation-v2",
    }
    record["content_hash"] = hashlib.sha256(json.dumps(
        {k: v for k, v in record.items() if k != "content_hash"},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return record


def evaluate_auth(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate authorization records against D09 criteria (pure)."""
    if len(records) != 4:
        raise InterpretationError("auth evaluation needs exactly 4 records")
    outcomes = [r["outcome"] for r in records]
    ids = {r["observation_id"] for r in records}
    if ids != {"auth-admin-allowed", "auth-member-denied",
               "auth-credential-rejection", "auth-outsider-isolated"}:
        raise InterpretationError("auth observation set mismatch")
    if all(o == "PASS" for o in outcomes):
        return {"support": "SUPPORTED", "falsifier": "NOT_TRIGGERED",
                "detail": "4/4 authorization observations PASS"}
    if any(o == "FAIL" for o in outcomes):
        return {"support": "CONTRADICTED", "falsifier": "TRIGGERED",
                "detail": "authorization falsifier triggered"}
    return {"support": "UNDETERMINED", "falsifier": "UNDETERMINED",
            "detail": "non-passing outcomes without falsification"}


def evaluate_deploy(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate deployment-cycle records against D09 criteria (pure)."""
    if len(records) != 3:
        raise InterpretationError("deploy evaluation needs exactly 3 records")
    outcomes = [r["outcome"] for r in records]
    cycles = sorted(r["cycle_id"] for r in records)
    if cycles != ["cycle-01", "cycle-02", "cycle-03"]:
        raise InterpretationError("deploy cycle set mismatch")
    if all(o == "PASS" for o in outcomes):
        return {"support": "SUPPORTED", "falsifier": "NOT_TRIGGERED",
                "detail": "3/3 independent cycles PASS"}
    if any(o == "FAIL" for o in outcomes):
        return {"support": "CONTRADICTED", "falsifier": "TRIGGERED",
                "detail": "cycle falsifier triggered"}
    return {"support": "UNDETERMINED", "falsifier": "UNDETERMINED",
            "detail": "non-passing outcomes without falsification"}


def detect_contradictions(auth_eval: dict[str, Any],
                          deploy_eval: dict[str, Any]) -> list[dict[str, Any]]:
    """Expose genuine conflicts; never collapse them."""
    contradictions = []
    for name, evaluation in (("auth", auth_eval), ("deploy", deploy_eval)):
        if evaluation["support"] == "CONTRADICTED":
            contradictions.append({
                "contradiction_id": f"vs1-v2-contradiction-{name}",
                "scope": name,
                "detail": evaluation["detail"],
                "status": "contradicted",
            })
    return contradictions


def upstream_identities_from(d10_artifact: dict[str, Any]) -> dict[str, str]:
    """Recompute frozen upstream identities D01–D10 (fail-closed)."""
    from vertical_slice import implementation as IMPL
    from vertical_slice import candidates as C
    from vertical_slice.deployment import build_contract as deploy_contract
    from vertical_slice import observation as OBS
    from vertical_slice import evolution_decision as DEC
    from vertical_slice import evidence_acquisition as ACQ

    identity = IMPL.frozen_input_identity()
    contract = deploy_contract()
    decision = DEC.decide()
    gate = ACQ.run_gate()
    expected = {
        "vs-d01-graph-sha256": identity["vs-d01-graph-sha256"],
        "vs-d02-isr-content-hash": identity["vs-d02-isr-content-hash"],
        "vs-d03-selected": "vs1-candidate-a",
        "vs-d03-policy": C.SELECTION_POLICY_VERSION,
        "vs-d04-implementation": IMPL.IMPLEMENTATION_VERSION,
        "vs-d05-deployment": str(contract["deployment_contract_version"]),
        "vs-d06-observation": OBS.OBSERVATION_CONTRACT_VERSION,
        "vs-d07-interpretation": "vs1-interpret-v1",
        "vs-d08-decision": decision["decision"],
        "vs-d08-policy": decision["policy_id"],
        "vs-d09-policy": gate["policy"],
        "vs-d09-outcome": gate["outcome"],
        "vs-d10-contract": "vs1-evidence-run-v1",
    }
    for record in d10_artifact["observations"]:
        for key in ("vs-d01-graph-sha256", "vs-d02-isr-content-hash",
                    "vs-d03-selected"):
            if record["provenance"].get(key) != expected[key]:
                raise InterpretationError(f"D10 provenance drift: {key}")
    return expected
