"""VS-D23 — candidate generation against admitted objective VS1-OBJ-001.

Generates bounded, competing, materially distinct architectural candidates
for task priority (LOW/MEDIUM/HIGH) while preserving existing obligations.
Generation ONLY: no selection, implementation, deployment, observation,
optimization, production change, commit, or push. ISR immutable. Historical
D13/D14 synthetic lineage untouched; new candidates carry their own
vs1-obj001 lineage. Deterministic: content-addressed candidate identities,
canonical evidence, no timestamps/PIDs/paths in identity.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

GENERATION_CONTRACT = "vs1-candidate-generation-d23"
GENERATION_POLICY_ID = "vs1-candidate-generation-policy-v1"
OBJECTIVE_ID = "VS1-OBJ-001"
D22_PATH = "vertical_slice/objective_intake_d22_evidence.json"
SOURCE_PATH = "vertical_slice/objective_source_VS1-OBJ-001.json"

EXPECTED_ISR = "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb"
EXPECTED_SOURCE_SHA = (
    "4a9cde9ab822980985dc59e1f05649a456ee6ae3be6b30421183801d12ac6848"
)
PRIORITY_VALUES: tuple[str, str, str] = ("LOW", "MEDIUM", "HIGH")
LEGACY_DEFAULT = "MEDIUM"

SUCCESS_CRITERIA: tuple[str, ...] = tuple(f"SC{i:02d}" for i in range(1, 14))

# Coverage classes (architectural path only; runtime proof is downstream).
DIRECT = "DIRECTLY_SUPPORTED"
WITH_IMPL = "SUPPORTED_WITH_IMPLEMENTATION"
DOWNSTREAM = "REQUIRES_DOWNSTREAM_VERIFICATION"


class CandidateError(Exception):
    """Fail-closed candidate-generation failure."""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canon(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def _load_json(path: str) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as f:
            record = json.load(f)
    except (OSError, ValueError) as exc:
        raise CandidateError(f"input unavailable: {path}: {exc}")
    if not isinstance(record, dict):
        raise CandidateError(f"input malformed: {path}")
    return record


def verify_upstream(d22_path: str = D22_PATH,
                      source_path: str = SOURCE_PATH) -> dict[str, Any]:
    """D22 admission + source digest + ISR pin (read-only, fail-closed)."""
    from vertical_slice import implementation as IMPL

    d22 = _load_json(d22_path)
    if d22.get("status") != "PASS" or not d22.get("admission", {}).get(
            "objective_admitted"):
        raise CandidateError("D22 admission absent")
    if d22.get("objective_id") != OBJECTIVE_ID:
        raise CandidateError("objective drift")
    if not isinstance(d22.get("objective"), dict) or not d22["objective"].get(
            "objective_hash"):
        raise CandidateError("admitted objective content missing")
    try:
        with open(source_path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
    except OSError as exc:
        raise CandidateError(f"source unavailable: {exc}")
    if digest != EXPECTED_SOURCE_SHA:
        raise CandidateError("objective source digest mismatch")
    if IMPL.frozen_input_identity()["vs-d02-isr-content-hash"] != EXPECTED_ISR:
        raise CandidateError("ISR drift")
    if d22.get("isr_hash") != EXPECTED_ISR:
        raise CandidateError("D22 ISR drift")
    return {"d22": d22, "source_sha256": digest, "isr_hash": EXPECTED_ISR}


def _coverage(api_direct: bool) -> dict[str, str]:
    """Coverage skeleton shared by all candidates (architectural paths only).

    API-model criteria are DIRECTLY_SUPPORTED where the existing task
    service/API owns the path; UI-realization criteria need downstream
    implementation (no UI layer exists in the current slice); selection-,
    deployment-, and observation-dependent criteria require downstream
    verification; lineage is established here.
    """
    filt = DIRECT if api_direct else WITH_IMPL
    return {
        "SC01": DIRECT, "SC02": DIRECT, "SC03": DIRECT, "SC04": DIRECT,
        "SC05": DIRECT, "SC06": WITH_IMPL, "SC07": filt, "SC08": DIRECT,
        "SC09": DOWNSTREAM, "SC10": DOWNSTREAM, "SC11": DOWNSTREAM,
        "SC12": DOWNSTREAM, "SC13": DIRECT,
    }


_FAILURES: tuple[tuple[str, str], ...] = (
    ("invalid priority", "deterministic 422 rejection at validation boundary"),
    ("missing priority", "deterministic default MEDIUM applied"),
    ("legacy records", "one-time deterministic defaulting on load/persist"),
    ("unauthorized filter request", "401 without token, 403 for outsider"),
    ("cross-tenant filter attempt", "403 via existing membership policy"),
    ("invalid API input", "422 via existing validation behavior"),
    ("database inconsistency", "fail closed on load validation error"),
    ("migration failure", "abort before atomic replace; store untouched"),
    ("partial update", "single-task atomic persist; no torn writes"),
    ("event compatibility failure", "no event contract change; names stable"),
)


def _candidate(profile: str, problem: str, strategy: str,
               components: list[dict[str, str]], api: str, data: str,
               persistence: str, filtering: str, security: str,
               events: str, migration: str, behavior: str,
               tradeoffs: str, risks: str, complexity: str,
               reversibility: str, feasibility: str,
               operational: str, evolutionary: str,
               api_direct: bool) -> dict[str, Any]:
    return {
        "candidate_version": "v1",
        "priority_values": list(PRIORITY_VALUES),
        "legacy_default": LEGACY_DEFAULT,
        "objective_id": OBJECTIVE_ID,
        "parent_architecture_context": "vs1-evolved-96fe2d29fd76/central-policy",
        "parent_implementation_context": "vs1-impl-v2",
        "architecture_profile": profile,
        "problem_statement": problem,
        "architectural_strategy": strategy,
        "components": components,
        "service_boundaries": "existing svc-task/svc-workspace/svc-identity "
                              "unchanged unless noted per component",
        "api_changes": api,
        "data_model_changes": data,
        "persistence_strategy": persistence,
        "filtering_strategy": filtering,
        "security_strategy": security,
        "event_strategy": events,
        "event_classification": "NO_EVENT_CHANGE_REQUIRED",
        "migration_strategy": migration,
        "behavior_preservation_strategy": behavior,
        "requirement_mappings": ["req-task-create", "req-task-read",
                                 "req-task-update", "req-task-delete",
                                 "req-tenant-isolation", "req-credential-safety",
                                 "req-durability"],
        "isr_mappings": ["svc-task", "api-task", "dm-task",
                         "sec-tenant-isolation", "sec-credential-safety",
                         "ev-task-created", "ev-task-updated"],
        "objective_mappings": list(SUCCESS_CRITERIA),
        "constraints": ["C01-C10 per VS1-OBJ-001 source record"],
        "risks": risks,
        "failure_modes": [{"failure": f, "behavior": b} for f, b in _FAILURES],
        "operational_implications": operational,
        "scaling_implications": "unchanged query scaling; filter is O(tasks) "
                                "as today; no new scaling claim",
        "complexity": complexity,
        "reversibility": reversibility,
        "implementation_feasibility": feasibility,
        "verification_strategy": "existing CRUD suite (SC08) + new priority "
                                 "contract tests (SC09) + deployment smoke "
                                 "(SC11) + runtime observation (SC12)",
        "trade_offs": tradeoffs,
        "evolutionary_value": evolutionary,
        "coverage": _coverage(api_direct),
    }


def _definitions() -> list[dict[str, Any]]:
    task_comp = {"component": "dm-task.priority",
                 "responsibility": "persisted priority attribute, closed enum"}
    return [
        _candidate(
            profile="domain-model-extension",
            problem="Priority must be creatable, updatable, readable, and "
                    "filterable per task without disturbing existing behavior.",
            strategy="Priority becomes a first-class attribute of the "
                     "existing Task domain model; the task service/API stays "
                     "authoritative and filtering is a task query capability.",
            components=[
                task_comp,
                {"component": "svc-task.priority-validation",
                 "responsibility": "closed-enum validation + MEDIUM default"},
                {"component": "svc-task.priority-filter",
                 "responsibility": "priority predicate in task listing"},
                {"component": "api-task.priority-contract",
                 "responsibility": "create/update/read/filter contract"},
            ],
            api="TaskCreateBody/TaskUpdateBody gain priority; GET list "
                "accepts ?priority=; invalid values 422; responses echo "
                "priority; contract backward compatible (default on omit).",
            data="Task gains priority: LOW|MEDIUM|HIGH, default MEDIUM; "
                 "store persists the field; load validates or fails closed.",
            persistence="JSON-file store extended by one field; atomic "
                        "replace unchanged; legacy records default MEDIUM on "
                        "first persist.",
            filtering="service-level predicate over workspace tasks; "
                      "membership check precedes filtering (no bypass).",
            security="existing session/member/admin policy untouched; "
                     "priority never an authorization input; filter runs "
                     "after membership check.",
            events="task-created/task-updated names and producers unchanged.",
            migration="deterministic default MEDIUM for records lacking the "
                      "field; repeatable; observable via count; reversible "
                      "by field removal (original fields untouched).",
            behavior="all existing CRUD paths preserved; omit-priority "
                     "requests behave as before plus default.",
            tradeoffs="minimal disruption vs tighter coupling of task model "
                      "to the new concern.",
            risks="model bloat if further attributes follow the same path.",
            complexity="low",
            reversibility="high (single additive field)",
            feasibility="high: same service/store/API shape as today",
            operational="one-field migration; unchanged rollback (redeploy "
                        "prior build reads store ignoring unknown field only "
                        "if loader tolerates it — verified downstream)",
            evolutionary="extends the proven task authority; future task "
                         "attributes could follow, at coupling cost.",
            api_direct=True,
        ),
        _candidate(
            profile="query-policy-separation",
            problem="Same as model extension, with filtering semantics "
                    "isolated behind an explicit policy boundary (precedent: "
                    "AuthorizationPolicy) rather than inline in the service.",
            strategy="Task owns persistence; a dedicated PriorityQueryPolicy "
                     "owns validation of filter semantics and predicate "
                     "construction; the service delegates.",
            components=[
                task_comp,
                {"component": "priority-query-policy",
                 "responsibility": "filter-semantics + predicate decisions"},
                {"component": "svc-task.priority-delegation",
                 "responsibility": "delegate validation/filtering to policy"},
                {"component": "api-task.priority-contract",
                 "responsibility": "create/update/read/filter contract"},
            ],
            api="same priority contract surface as model extension; filtering "
                "errors map through the policy to 422/403 deterministically.",
            data="same Task.priority field and store representation.",
            persistence="same store extension; policy holds no state.",
            filtering="policy-built predicate applied post-membership-check; "
                      "semantics auditable in one place.",
            security="policy boundary is authorization-adjacent but never "
                     "authorization: membership enforced before delegation; "
                     "priority never grants access.",
            events="task-created/task-updated names and producers unchanged.",
            migration="same deterministic MEDIUM defaulting as model "
                      "extension; reversible by field removal.",
            behavior="identical observable behavior to model extension; "
                     "responsibility placement differs.",
            tradeoffs="clearer filtering-policy seam vs extra internal "
                      "boundary and coordination cost.",
            risks="boundary may be unjustified ceremony for one predicate.",
            complexity="medium-low",
            reversibility="high (policy removable; service falls back)",
            feasibility="high: mirrors the existing AuthorizationPolicy seam",
            operational="same migration as model extension; one more unit "
                        "under test.",
            evolutionary="establishes a query-policy pattern reusable for "
                         "future task query capabilities.",
            api_direct=False,
        ),
        _candidate(
            profile="capability-oriented-extension",
            problem="Same capability, isolated as an explicit Priority "
                    "Capability so lifecycle authority never absorbs "
                    "evolving attribute concerns.",
            strategy="Task lifecycle authority unchanged; a Priority "
                    "Capability boundary owns validation, representation, "
                    "and filtering integration for priority.",
            components=[
                {"component": "priority-capability.validation",
                 "responsibility": "closed-enum validation + defaulting"},
                {"component": "priority-capability.representation",
                 "responsibility": "API/store representation mapping"},
                {"component": "priority-capability.filtering",
                 "responsibility": "filter integration with lifecycle reads"},
                {"component": "dm-task.priority-ref",
                 "responsibility": "stored value owned by lifecycle, "
                                   "interpreted by capability"},
            ],
            api="same priority contract surface; capability maps "
                "representation at the boundary; invalid values 422.",
            data="stored value on Task; interpretation centralized in the "
                "capability.",
            persistence="same store extension; capability is stateless.",
            filtering="capability-provided predicate composed into "
                      "lifecycle reads after membership check.",
            security="capability has no authorization role; lifecycle "
                     "membership checks precede capability invocation.",
            events="task-created/task-updated names and producers unchanged.",
            migration="same deterministic MEDIUM defaulting; reversible "
                      "by field removal.",
            behavior="lifecycle paths byte-equivalent in behavior; "
                     "capability only interprets the new field.",
            tradeoffs="strongest isolation of the evolving concern vs "
                      "abstraction cost for a small feature.",
            risks="over-abstraction; capability/lifecycle drift.",
            complexity="medium",
            reversibility="medium (capability removable; stored values inert)",
            feasibility="medium-high: new seam, unchanged lifecycle core",
            operational="same migration; capability versioned separately.",
            evolutionary="cleanest host for future task attributes as "
                         "capabilities; highest seam count.",
            api_direct=False,
        ),
    ]


def build_candidates(d22_path: str = D22_PATH,
                     source_path: str = SOURCE_PATH) -> list[dict[str, Any]]:
    """Deterministic construction with content-addressed identities."""
    upstream = verify_upstream(d22_path, source_path)
    candidates = []
    for definition in _definitions():
        identity = _sha(_canon(definition))
        candidates.append({
            "candidate_id": f"vs1-obj001-candidate-{identity[:12]}",
            "candidate_hash": identity,
            "lineage": {
                "candidate": "self",
                "objective": OBJECTIVE_ID,
                "d22_admission": upstream["d22"]["intake_hash"],
                "isr": upstream["isr_hash"],
                "objective_source_sha256": upstream["source_sha256"],
            },
            **definition,
        })
    candidates.sort(key=lambda c: c["candidate_id"])
    return candidates


def validate_lineage(candidates: list[dict[str, Any]]) -> None:
    """Every component maps to a requirement/obligation; every SC covered;
    every ISR mapping resolves. Fail-closed."""
    from vertical_slice.isr import build_task_tracker_isr
    from vertical_slice.requirements import build_task_tracker_requirements

    graph = build_task_tracker_requirements()
    rev = build_task_tracker_isr()
    for candidate in candidates:
        for component in candidate["components"]:
            if not component.get("responsibility", "").strip():
                raise CandidateError(
                    f"{candidate['candidate_id']}: responsibility missing")
        for req in candidate["requirement_mappings"]:
            if req not in graph.nodes:
                raise CandidateError(f"orphan requirement: {req}")
        for node in candidate["isr_mappings"]:
            if node not in rev.graph.nodes:
                raise CandidateError(f"orphan ISR node: {node}")
        missing = [sc for sc in SUCCESS_CRITERIA
                   if sc not in candidate["coverage"]]
        if missing:
            raise CandidateError(f"orphan obligations: {missing}")
        if sorted(candidate.get("priority_values", [])) != sorted(PRIORITY_VALUES):
            raise CandidateError(
                f"{candidate['candidate_id']}: priority values not closed "
                f"to LOW/MEDIUM/HIGH")
        if candidate.get("legacy_default") != LEGACY_DEFAULT:
            raise CandidateError(
                f"{candidate['candidate_id']}: legacy default not MEDIUM")


def comparison_matrix(candidates: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Neutral descriptive attributes only — no ranking, no winner."""
    rows = []
    for candidate in candidates:
        direct = sum(1 for v in candidate["coverage"].values() if v == DIRECT)
        rows.append({
            "candidate_id": candidate["candidate_id"],
            "profile": candidate["architecture_profile"],
            "direct_coverage": f"{direct}/{len(SUCCESS_CRITERIA)}",
            "complexity": candidate["complexity"],
            "reversibility": candidate["reversibility"],
            "coupling_note": candidate["trade_offs"],
            "risk_note": candidate["risks"],
        })
    return rows


def assemble_evidence(generated_at: str, d22_path: str = D22_PATH,
                        source_path: str = SOURCE_PATH) -> dict[str, Any]:
    """Canonical candidate evidence. Selection/implementation/deployment
    flags are explicit falsehoods, not omissions."""
    upstream = verify_upstream(d22_path, source_path)
    candidates = build_candidates(d22_path, source_path)
    validate_lineage(candidates)
    record: dict[str, Any] = {
        "contract": GENERATION_CONTRACT,
        "policy_id": GENERATION_POLICY_ID,
        "stage": "candidate-generation",
        "objective_id": OBJECTIVE_ID,
        "objective_hash": upstream["d22"]["objective_hash"],
        "objective_source_reference": upstream["d22"]["source_reference"],
        "objective_source_sha256": upstream["source_sha256"],
        "isr_hash": upstream["isr_hash"],
        "upstream_d19": upstream["d22"]["upstream"]["d19_decision"],
        "upstream_d20": upstream["d22"]["upstream"]["d20_closure"],
        "upstream_d21": "HOLD",
        "upstream_d22": upstream["d22"]["intake_hash"],
        "generation_policy_hash": _sha(_canon({
            "policy": GENERATION_POLICY_ID,
            "objective": OBJECTIVE_ID,
            "profiles": ["domain-model-extension", "query-policy-separation",
                         "capability-oriented-extension"],
            "priority_values": list(PRIORITY_VALUES),
            "legacy_default": LEGACY_DEFAULT,
        })),
        "candidate_count": len(candidates),
        "candidate_ids": [c["candidate_id"] for c in candidates],
        "candidate_hashes": [c["candidate_hash"] for c in candidates],
        "candidates": candidates,
        "comparison": comparison_matrix(candidates),
        "objective_coverage": {sc: sorted({c["coverage"][sc] for c in candidates})
                               for sc in SUCCESS_CRITERIA},
        "isr_coverage": sorted({n for c in candidates
                                for n in c["isr_mappings"]}),
        "security_coverage": ["authentication", "authorization",
                              "tenant-isolation", "credential-safety",
                              "input-validation", "secret-handling"],
        "selection_performed": False,
        "implementation_performed": False,
        "deployment_performed": False,
        "observation_performed": False,
        "optimization_performed": False,
        "production_authorization": False,
        "push_authorization": "NONE",
        "provenance": {
            "contract": GENERATION_CONTRACT,
            "objective": OBJECTIVE_ID,
            "d22_intake": upstream["d22"]["intake_hash"],
            "isr_hash": upstream["isr_hash"],
        },
    }
    record["provenance"]["generated_at"] = generated_at
    check = {k: v for k, v in record.items() if k != "provenance"}
    provenance = dict(record["provenance"])
    provenance.pop("generated_at", None)
    check["provenance"] = provenance
    record["generation_hash"] = _sha(_canon(check))
    return record
