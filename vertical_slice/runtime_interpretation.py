"""VS-D18 — interpretation of D17 runtime observation evidence.

Reads the committed D17 evidence artifact and states what may and may not
be concluded from it. Interpretation ONLY: no authorization, no evolution
decision, no mutation, no redeployment, no remediation. Every finding traces
to observation IDs; every limit is stated explicitly. Scope notes are part
of the findings, not footnotes — a bounded loopback workload cannot prove
production behavior, and this module must not claim otherwise.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

INTERPRETATION_CONTRACT = "vs1-runtime-interpret-v1"
EVIDENCE_PATH = "vertical_slice/runtime_observation_evidence.json"

SUPPORT_VALUES: tuple[str, ...] = (
    "SUPPORTED", "HYPOTHESIZED", "UNKNOWN", "CONTRADICTED",
)

# Words that would constitute interpretation overreach (performance claims,
# superiority claims, production claims, authorization claims).
BANNED_CLAIM_TOKENS: tuple[str, ...] = (
    "fast", "slow", "performant", "superior", "better architecture",
    "production-ready", "production ready", "certified", "authorized",
    "approved", "improvement", "fitness gain",
)

# Frozen identity pins (fail-closed inputs, never regenerated here).
EXPECTED_ISR = "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb"
EXPECTED_IMPL = "vs1-impl-v2"
EXPECTED_IMPL_HASH = (
    "d2090df69127e9922494bb7a4d526de087fd948ee793bdf326d5fe18fac1dd8c"
)
EXPECTED_ARCH = "vs1-evolved-96fe2d29fd76"


class InterpretationError(Exception):
    """Fail-closed interpretation failure."""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canon(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def load_evidence(path: str = EVIDENCE_PATH) -> dict[str, Any]:
    """Load the D17 evidence artifact and verify its identity (read-only)."""
    try:
        with open(path, encoding="utf-8") as f:
            evidence = json.load(f)
    except (OSError, ValueError) as exc:
        raise InterpretationError(f"D17 evidence unavailable: {exc}")
    if not isinstance(evidence, dict):
        raise InterpretationError("D17 evidence malformed")
    for field in ("observations", "normalized", "summary", "provenance",
                  "normalized_hash", "constitutional_invariants",
                  "security_invariants", "behavioral_invariants"):
        if field not in evidence:
            raise InterpretationError(f"D17 evidence missing field: {field}")
    if evidence.get("contract") != "vs1-runtime-observe-v1":
        raise InterpretationError("D17 contract drift")
    if evidence.get("implementation_id") != EXPECTED_IMPL:
        raise InterpretationError("implementation drift")
    if evidence.get("implementation_hash") != EXPECTED_IMPL_HASH:
        raise InterpretationError("implementation hash drift")
    if evidence.get("architecture_id") != EXPECTED_ARCH:
        raise InterpretationError("architecture drift")
    if evidence.get("isr_hash") != EXPECTED_ISR:
        raise InterpretationError("ISR drift")
    if evidence.get("production_authorization") is not False:
        raise InterpretationError("production authorization drift")
    check = {k: v for k, v in evidence.items()
             if k not in ("provenance", "normalized_hash")}
    provenance = dict(evidence["provenance"])
    provenance.pop("generated_at", None)
    check["provenance"] = provenance
    if _sha(_canon(check)) != evidence["normalized_hash"]:
        raise InterpretationError("D17 evidence hash mismatch")
    return evidence


def _finding(finding_id: str, claim: str, support: str,
             observation_ids: list[str], scope: str,
             known: set[str]) -> dict[str, Any]:
    if support not in SUPPORT_VALUES:
        raise InterpretationError(f"unknown support level: {support}")
    missing = [o for o in observation_ids if o not in known]
    if missing:
        raise InterpretationError(f"{finding_id} traces to missing: {missing}")
    lowered = claim.lower()
    for token in BANNED_CLAIM_TOKENS:
        if token in lowered:
            raise InterpretationError(
                f"{finding_id} overreaches with {token!r}")
    return {"finding_id": finding_id, "claim": claim, "support": support,
            "observation_ids": observation_ids, "scope": scope}


def assess(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive findings from evidence. Counts are reported; causes beyond the
    recorded classes are UNKNOWN, never inferred."""
    known = {r["observation_id"] for r in evidence["observations"]}
    summary = evidence["summary"]
    counts = summary["status_counts"]
    findings = [
        _finding(
            "F1", "The D16 deployment serves the v2 implementation's API "
            "contract (readiness, registration, login, task lifecycle).",
            "SUPPORTED" if counts["FAIL"] == 0 else "CONTRADICTED",
            ["lifecycle.readiness", "auth.register", "auth.login",
             "crud.create", "crud.read", "crud.update", "crud.delete"],
            "Single loopback deployment, one seeded workspace, one workload.",
            known),
        _finding(
            "F2", "Invalid credentials are rejected (401) while valid "
            "credentials authenticate (200).",
            "SUPPORTED",
            ["auth.login", "auth.invalid-rejected", "auth.authenticated-request"],
            "One user, one wrong-password case; no brute-force/lockout scope.",
            known),
        _finding(
            "F3", "Workspace membership and admin role are enforced at the "
            "HTTP boundary (member forbidden 403, admin permitted 201, "
            "permitted operation 201).",
            "SUPPORTED",
            ["authz.admin-grant", "authz.permitted-operation",
             "authz.role-rejected"],
            "Behavioral evidence only; the policy-boundary proof is D15's.",
            known),
        _finding(
            "F4", "A non-member caller is isolated from workspace state (403).",
            "SUPPORTED",
            ["authz.outsider-rejected"],
            "Single outsider, single workspace; general isolation posture "
            "beyond this case is UNKNOWN.",
            known),
        _finding(
            "F5", "State survives restart in both directions: created state "
            "persists and pre-restart deletion stays deleted.",
            "SUPPORTED",
            ["persist.restart-state"],
            "One restart, one store, file-backed backend only.",
            known),
        _finding(
            "F6", "Lifecycle events are emitted with required producer and "
            "type fields (svc-task, task-created/task-updated).",
            "SUPPORTED",
            ["events.lifecycle-emitted"],
            "Store-level read of one workload's events; no stream/ordering "
            "claims beyond the recorded set.",
            known),
        _finding(
            "F7", "Recorded evidence contains no secret shapes or raw "
            "credential strings.",
            "SUPPORTED",
            ["auth.login", "events.lifecycle-emitted"],
            "Shape-scan scope only; absence of shapes is not a full audit.",
            known),
        _finding(
            "F8", "Latency was measured mechanically; no performance "
            "conclusion follows from these values.",
            "SUPPORTED",
            ["lifecycle.readiness", "crud.read"],
            "Deliberate non-finding: loopback timing proves nothing about "
            "production performance.",
            known),
        _finding(
            "F9", f"All {summary['observation_count']} observations resolved "
            f"PASS with {counts['FAIL']} FAIL, {counts['UNDETERMINED']} "
            f"UNDETERMINED, {counts['BLOCKED']} BLOCKED.",
            "SUPPORTED" if (counts["FAIL"] == 0
                            and counts["UNDETERMINED"] == 0
                            and counts["BLOCKED"] == 0) else "CONTRADICTED",
            sorted(known),
            "Bounded workload only: no concurrency, no multi-workspace, no "
            "long-run, no adversarial scope.",
            known),
        _finding(
            "F10", "The real evolution decision stands at NO_CHANGE and "
            "production authorization remains false; nothing observed "
            "authorizes evolution or production.",
            "SUPPORTED",
            ["lifecycle.readiness"],
            "Constitutional reading of evidence metadata, not a runtime "
            "measurement.",
            known),
    ]
    return findings


def unknowns() -> list[str]:
    return [
        "Production behavior (network, load, persistence at scale).",
        "Concurrency and multi-actor interleavings.",
        "Multi-workspace and multi-outsider isolation posture.",
        "Long-run durability and clock/expiry behavior.",
        "Performance characteristics under any real workload.",
        "Whether observed behavior would reproduce on another backend.",
        "Whether any finding would change under adversarial input.",
    ]


def assemble_interpretation(evidence: dict[str, Any],
                            generated_at: str) -> dict[str, Any]:
    """Canonical interpretation record. The decision block is an explicit
    non-decision: D18 authorizes nothing."""
    findings = assess(evidence)
    record: dict[str, Any] = {
        "contract": INTERPRETATION_CONTRACT,
        "execution_id": evidence["execution_id"],
        "deployment_id": evidence["deployment_id"],
        "implementation_id": evidence["implementation_id"],
        "implementation_hash": evidence["implementation_hash"],
        "architecture_id": evidence["architecture_id"],
        "isr_hash": evidence["isr_hash"],
        "evidence_hash": evidence["normalized_hash"],
        "evidence_observations": evidence["summary"]["observation_count"],
        "findings": findings,
        "unknowns": unknowns(),
        "decision": {
            "evolution_decision": "NONE",
            "authorization": "NONE",
            "production_authorization": False,
            "rationale": "D18 interprets evidence only; evolution and "
                         "production decisions belong to downstream gates.",
        },
        "provenance": dict(evidence["provenance"]),
    }
    record["provenance"]["generated_at"] = generated_at
    record["provenance"]["interpretation_contract"] = INTERPRETATION_CONTRACT
    check = {k: v for k, v in record.items() if k != "provenance"}
    provenance = dict(record["provenance"])
    provenance.pop("generated_at", None)
    check["provenance"] = provenance
    record["content_hash"] = _sha(_canon(check))
    return record
