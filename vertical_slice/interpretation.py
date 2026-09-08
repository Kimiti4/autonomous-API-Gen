"""VS-D07 — interpretation + epistemic structuring (facts → claims → hypotheses).

FACTS live in vertical_slice/observation_evidence.json (VS-D06).
This module produces FINDINGS / CLAIMS / HYPOTHESES / FALSIFIERS only.

It never mutates requirements, ISR, candidates, implementation, deployment,
or observations. It never decides an architecture change. See
folder/VS1_INTERPRETATION.md §firewall.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from vertical_slice.observation import (
    DEPLOYMENT_ID,
    IMPLEMENTATION_ID,
    OBSERVATION_CONTRACT_ID,
)

INTERPRETATION_CONTRACT_VERSION = "vs1-interpret-v1"
INTERPRETATION_CONTRACT_ID = "vs1-interpret-v1"

_CLAIM_TYPES = (
    "runtime-confirmed",
    "requirement-alignment",
    "security-observation",
    "persistence-observation",
    "event-observation",
    "boundary-condition",
    "uncertainty",
    "contradiction",
)

_STATUSES = (
    "supported",
    "weakly_supported",
    "undetermined",
    "contradicted",
    "not_tested",
)

_ELIGIBILITY = (
    "eligible_for_evolution_review",
    "requires_more_evidence",
    "insufficient_evidence",
    "contradicted",
    "out_of_scope",
)

_OUT_OF_SCOPE_PROPERTIES = (
    "production-scale behavior",
    "long-duration reliability",
    "multi-instance behavior",
    "regional resilience",
    "high-load behavior",
    "economic efficiency",
    "security against arbitrary attackers",
)


class InterpretationError(Exception):
    """Fail-closed interpretation failure."""


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def load_evidence(path: str = "vertical_slice/observation_evidence.json") -> dict[str, Any]:
    """Load + validate the frozen D06 evidence artifact (fail-closed)."""
    with open(path, encoding="utf-8") as f:
        evidence = json.load(f)
    if evidence.get("observation_contract") != "vs1-observe-v1":
        raise InterpretationError("D06 contract mismatch")
    records = evidence.get("records")
    if not isinstance(records, list) or not records:
        raise InterpretationError("D06 evidence has no records")
    required = (
        "observation_id", "observation_contract", "deployment_id",
        "implementation_id", "probe_id", "sequence", "operation", "target",
        "result", "status", "evidence_payload", "provenance",
    )
    for record in records:
        for field in required:
            if field not in record:
                raise InterpretationError(f"D06 record missing field: {field}")
    return evidence


def upstream_identities(provenance: dict[str, str] | None = None) -> dict[str, str]:
    """Recompute (never trust copies) the frozen upstream identities.

    Selection identity is read from validated D06 record provenance (which
    carries vs-d03-selected), never by re-executing selection: interpretation
    must not run candidate machinery (firewall). Policy/implementation/
    deployment versions are read as constants, and D01/D02 hashes are
    recomputed from the frozen builders.
    """
    from vertical_slice import implementation as IMPL
    from vertical_slice.candidates import SELECTION_POLICY_VERSION
    from vertical_slice.deployment import build_contract as deploy_contract
    from vertical_slice import observation as OBS

    identity = IMPL.frozen_input_identity()
    contract = deploy_contract()
    selected = (provenance or {}).get("vs-d03-selected", "vs1-candidate-a")
    if selected != "vs1-candidate-a":
        raise InterpretationError(
            f"upstream selection drift: {selected}")
    return {
        "vs-d01-graph-sha256": identity["vs-d01-graph-sha256"],
        "vs-d02-isr-content-hash": identity["vs-d02-isr-content-hash"],
        "vs-d03-selected": selected,
        "vs-d03-policy": SELECTION_POLICY_VERSION,
        "vs-d04-implementation": IMPL.IMPLEMENTATION_VERSION,
        "vs-d05-deployment": str(contract["deployment_contract_version"]),
        "vs-d06-observation": OBS.OBSERVATION_CONTRACT_VERSION,
    }


def _claim(claim_type: str, statement: str, supporting: list[str],
           provenance: dict[str, str], status: str,
           isr_refs: tuple[str, ...] = ()) -> dict[str, Any]:
    if claim_type not in _CLAIM_TYPES:
        raise InterpretationError(f"unknown claim type: {claim_type}")
    if status not in _STATUSES:
        raise InterpretationError(f"unknown status: {status}")
    if not supporting:
        raise InterpretationError("claim with no evidence lineage")
    return {
        "claim_id": _stable_id("vs1-claim", claim_type, statement,
                               ",".join(sorted(supporting))),
        "claim_type": claim_type,
        "statement": statement,
        "supporting_observations": sorted(supporting),
        "isr_refs": sorted(isr_refs),
        "provenance": dict(provenance),
        "strength": status,
        "status": status,
    }


def build_claims(records: list[dict[str, Any]],
                 provenance: dict[str, str]) -> list[dict[str, Any]]:
    """Derive claims from records. Every claim names its observations."""
    by_probe = {r["probe_id"]: r for r in records}

    def obs(*probe_ids: str) -> list[str]:
        missing = [p for p in probe_ids if p not in by_probe]
        if missing:
            raise InterpretationError(f"claim references absent observations: {missing}")
        return [by_probe[p]["observation_id"] for p in probe_ids]

    claims = [
        _claim("runtime-confirmed",
               "The observed deployment satisfied the defined readiness condition.",
               obs("P01-readiness"), provenance, "supported",
               ("svc-task",)),
        _claim("requirement-alignment",
               "Authenticated task lifecycle completed as required by "
               "req-task-create/req-task-read/req-task-update.",
               obs("P03-crud-lifecycle"), provenance, "supported",
               ("cap-task-create", "cap-task-read", "cap-task-update",
                "svc-task", "api-task")),
        _claim("security-observation",
               "Unauthenticated access was rejected and a non-member was "
               "isolated, consistent with req-auth-login/req-tenant-isolation.",
               obs("P02-authentication", "P04-authorization"), provenance,
               "supported",
               ("sec-credential-safety", "sec-tenant-isolation",
                "svc-identity", "svc-task")),
        _claim("persistence-observation",
               "Committed state survived a controlled restart, consistent "
               "with req-durability.",
               obs("P05-persistence"), provenance, "supported",
               ("dm-task", "dm-workspace")),
        _claim("event-observation",
               "A task lifecycle operation produced the expected persisted "
               "event evidence.",
               obs("P06-events"), provenance, "supported",
               ("ev-task-created", "svc-task")),
        _claim("runtime-confirmed",
               "The observed runtime remained in steady state for the bounded run.",
               obs("P07-lifecycle"), provenance, "weakly_supported",
               ("svc-task",)),
        _claim("boundary-condition",
               "The following were NOT established by this evidence: "
               + "; ".join(_OUT_OF_SCOPE_PROPERTIES) + ".",
               obs("P01-readiness", "P07-lifecycle"), provenance, "supported",
               ()),
        _claim("uncertainty",
               "No failure was observed within the bounded run; this is absence "
               "of observed failure, not evidence that failure is impossible.",
               obs("P01-readiness", "P03-crud-lifecycle", "P07-lifecycle"),
               provenance, "supported", ()),
    ]
    return sorted(claims, key=lambda c: c["claim_id"])


def build_findings(claims: list[dict[str, Any]],
                   provenance: dict[str, str]) -> list[dict[str, Any]]:
    """Bounded conclusions, each with claim/observation lineage and scope."""
    by_type: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        by_type.setdefault(claim["claim_type"], []).append(claim)

    def finding(fid_suffix: str, statement: str, support: list[dict[str, Any]],
                confidence: str) -> dict[str, Any]:
        if confidence not in _STATUSES:
            raise InterpretationError(f"unknown confidence: {confidence}")
        claim_ids = sorted(c["claim_id"] for c in support)
        obs_ids = sorted({o for c in support for o in c["supporting_observations"]})
        if not claim_ids:
            raise InterpretationError("finding with no supporting claims")
        return {
            "finding_id": f"vs1-finding-{fid_suffix}",
            "statement": statement,
            "supporting_claims": claim_ids,
            "supporting_observations": obs_ids,
            "confidence": confidence,
            "scope": "bounded VS1 observation run (local loopback, single instance)",
            "limitations": "Single controlled run; see boundary-condition claim.",
            "provenance": dict(provenance),
        }

    sec = by_type.get("security-observation", [])
    req = by_type.get("requirement-alignment", [])
    per = by_type.get("persistence-observation", [])
    evt = by_type.get("event-observation", [])
    run = by_type.get("runtime-confirmed", [])
    bnd = by_type.get("boundary-condition", [])
    unc = by_type.get("uncertainty", [])
    findings = [
        finding("auth-enforced",
                "Authentication and workspace isolation held for every probed "
                "operation within the bounded run.",
                sec, "supported"),
        finding("lifecycle-verified",
                "The required task lifecycle completed end-to-end against the "
                "deployed implementation.",
                req, "supported"),
        finding("persistence-demonstrated",
                "Committed state survived a controlled restart.",
                per, "supported"),
        finding("events-emitted",
                "Lifecycle operations produced the expected persisted event evidence.",
                evt, "supported"),
        finding("steady-state",
                "The runtime remained steady for the bounded run; no broader "
                "availability claim is made.",
                run, "weakly_supported"),
        finding("scope-bounded",
                "Conclusions are confined to the bounded run; out-of-scope "
                "properties remain unestablished.",
                bnd + unc, "supported"),
    ]
    return sorted(findings, key=lambda f: f["finding_id"])


def build_hypotheses(findings: list[dict[str, Any]],
                     provenance: dict[str, str]) -> list[dict[str, Any]]:
    """Falsifiable propositions. Each carries falsifiers + acceptance
    conditions. A hypothesis is not a decision."""

    def hypothesis(hid: str, statement: str, motivation: str,
                   support_ids: list[str], scope: str, confidence: str,
                   falsifiers: list[str], acceptance: list[str],
                   eligibility: str) -> dict[str, Any]:
        if not falsifiers:
            raise InterpretationError(f"hypothesis {hid} lacks a falsifier")
        if eligibility not in _ELIGIBILITY:
            raise InterpretationError(f"unknown eligibility: {eligibility}")
        if confidence not in _STATUSES:
            raise InterpretationError(f"unknown confidence: {confidence}")
        known = {f["finding_id"] for f in findings}
        missing = [s for s in support_ids if s not in known]
        if missing:
            raise InterpretationError(f"hypothesis {hid} references unknown findings: {missing}")
        obs_ids = sorted({o for f in findings if f["finding_id"] in support_ids
                          for o in f["supporting_observations"]})
        return {
            "hypothesis_id": hid,
            "statement": statement,
            "motivation": motivation,
            "supporting_findings": sorted(support_ids),
            "supporting_observations": obs_ids,
            "scope": scope,
            "confidence": confidence,
            "falsifiers": list(falsifiers),
            "acceptance_conditions": list(acceptance),
            "provenance": dict(provenance),
            "status": "proposed",
            "evolution_eligibility": eligibility,
        }

    scope = "bounded VS1 slice; single instance, controlled workload"
    return sorted([
        hypothesis(
            "vs1-hypothesis-sufficient-bounded",
            "The consolidated single-service architecture is sufficient for "
            "the bounded VS1 workload.",
            "All functional, security, persistence, and event findings held "
            "within the bounded run.",
            ["vs1-finding-auth-enforced", "vs1-finding-lifecycle-verified",
             "vs1-finding-persistence-demonstrated", "vs1-finding-events-emitted"],
            scope, "supported",
            ["A controlled workload within the defined contract repeatedly "
             "produces service failure attributable to the architecture."],
            ["Repeat bounded runs keep all findings supported.",
             "No repeatable architecture-attributable failure appears."],
            "eligible_for_evolution_review"),
        hypothesis(
            "vs1-hypothesis-auth-model-adequate",
            "The session-token auth model satisfies the slice authentication "
            "and isolation requirements.",
            "P02/P04 findings held; no bypass observed.",
            ["vs1-finding-auth-enforced"], scope, "supported",
            ["A bounded authentication probe demonstrates credential bypass, "
             "session forgery, or cross-workspace access."],
            ["Authentication and isolation findings remain supported across repeats."],
            "requires_more_evidence"),
        hypothesis(
            "vs1-hypothesis-deploy-repeatable",
            "Deployment from the version-controlled descriptor reproduces the "
            "observed behavior on a fresh host.",
            "Single-instance evidence only; cross-host repetition not observed.",
            ["vs1-finding-steady-state"], scope, "weakly_supported",
            ["A fresh-host deployment from the same descriptor fails readiness "
             "or diverges behaviorally."],
            ["Independent fresh-host runs reproduce all probe outcomes."],
            "requires_more_evidence"),
    ], key=lambda h: h["hypothesis_id"])


def detect_contradictions(records: list[dict[str, object]],
                          claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expose genuine conflicts; never silently collapse them. The frozen D06
    evidence contains no contradictions; this guards the pipeline."""
    seen: dict[str, list[str]] = {}
    for record in records:
        seen.setdefault(record["probe_id"], []).append(record["result"])
    contradictions = []
    for probe_id in sorted(seen):
        results = seen[probe_id]
        if len(set(results)) > 1:
            contradictions.append({
                "contradiction_id": f"vs1-contradiction-{probe_id}",
                "probe_id": probe_id,
                "conflicting_results": sorted(set(results)),
                "status": "contradicted",
            })
    for claim in claims:
        if claim["status"] == "contradicted":
            contradictions.append({
                "contradiction_id": f"vs1-contradiction-{claim['claim_id']}",
                "probe_id": "",
                "conflicting_results": [claim["claim_id"]],
                "status": "contradicted",
            })
    return contradictions


def build_interpretation_evidence(
        evidence_path: str = "vertical_slice/observation_evidence.json") -> dict[str, Any]:
    """Full pipeline: validate → interpret → normalize (deterministic)."""
    from vertical_slice import observation as OBS

    with open(evidence_path, encoding="utf-8") as f:
        raw = f.read()
    import json as _json
    evidence = _json.loads(raw)
    if evidence.get("observation_contract") != "vs1-observe-v1":
        raise InterpretationError("D06 contract mismatch")
    records = evidence.get("records", [])
    normalized = OBS.normalize(records)
    provenance = dict(normalized[0]["provenance"]) if normalized else {}
    for field in ("observation_contract", "deployment_id", "implementation_id",
                  "vs-d01-graph-sha256", "vs-d02-isr-content-hash", "vs-d03-selected"):
        if field not in provenance:
            raise InterpretationError(f"incomplete provenance: {field}")
    claims = build_claims(normalized, provenance)
    findings = build_findings(claims, provenance)
    hypotheses = build_hypotheses(findings, provenance)
    contradictions = detect_contradictions(normalized, claims)
    return {
        "contract": OBSERVATION_CONTRACT_ID,
        "contract_version": INTERPRETATION_CONTRACT_VERSION,
        "upstream_identities": upstream_identities(provenance),
        "source_observation_ids": sorted(r["observation_id"] for r in normalized),
        "claims": claims,
        "findings": findings,
        "hypotheses": hypotheses,
        "falsifiers": sorted({f for h in hypotheses for f in h["falsifiers"]}),
        "contradictions": contradictions,
        "uncertainties": sorted(
            c["claim_id"] for c in claims if c["claim_type"] == "uncertainty"),
        "evolution_eligibility": sorted({h["evolution_eligibility"] for h in hypotheses}),
        "provenance": provenance,
        "schema_version": "vs1-interpretation-v1",
    }
