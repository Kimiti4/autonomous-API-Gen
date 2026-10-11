"""Deterministic, technology-neutral TaskFlow ISR profile from canonical inputs.

This is a partial semantic profile, not an application generator. It maps only
explicit capability names and acceptance gates. Domain entities, fields,
relationships, and executable security semantics remain UNKNOWN until the
problem/acceptance contract specifies them or a governed clarification resolves
them. No model, provider, network, golden application, or golden architecture is
used.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from constitutional_architecture.isr.model.entity import Entity
from constitutional_architecture.isr.model.isr import ISR, ISRProvenance
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.policy import Policy, PolicyRule, PolicyType
from constitutional_architecture.isr.model.system import System, SystemMetadata
from constitutional_architecture.isr.semantics.capability import BusinessCapability
from constitutional_architecture.isr.semantics.requirement import (
    AcceptanceCriterion,
    ObligationKind,
    Requirement,
)


@dataclass(frozen=True)
class TaskFlowProfile:
    isr: ISR
    source_contract_sha256: str
    source_problem_sha256: str
    traceability: dict[str, Any]
    assumptions: tuple[dict[str, str], ...]
    generation_blockers: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        from constitutional_architecture.isr.serialization.serializer import ISRSerializer

        # Exclude wall-clock provenance so repeated same-input runs have the
        # same serialized semantic ISR and digest.
        isr_payload = {
            "version": self.isr.version,
            "system": ISRSerializer._to_dict(self.isr.system),
            "content_hash": self.isr.content_hash,
        }
        return {
            "schema": "tiannara.taskflow.deterministic-isr-profile.v1",
            "source_contract_sha256": self.source_contract_sha256,
            "source_problem_sha256": self.source_problem_sha256,
            "isr": isr_payload,
            "isr_sha256": self.isr.content_hash,
            "isr_structurally_valid": self.isr.validate_structure(),
            "traceability": self.traceability,
            "assumptions": list(self.assumptions),
            "generation_blockers": list(self.generation_blockers),
            "generation_allowed": not self.generation_blockers,
            "certified": False,
            "provider_required": False,
            "network_calls": 0,
            "compiler_compatibility": {
                "native_cap_c_system_model_adapter": "MISSING",
                "constitutional_isr_pipeline": "SEPARATE_TYPE",
                "generation_status": "BLOCKED",
                "reason": (
                    "This profile emits constitutional_architecture.isr.model.isr.ISR; "
                    "the live Cap-C runner requires tiannara.domain.models.isr."
                    "IntermediateSoftwareRepresentation carrying a typed SystemModel."
                ),
                "evidence_status": "STATIC_INTERFACE_AUDIT_ONLY",
            },
        }


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:16].upper()}"


def build_taskflow_profile(
    problem: str,
    acceptance: Mapping[str, Any],
    *,
    problem_source: str = "snapshot:inputs/experiments/taskflow-native/PROBLEM.md",
    acceptance_source: str = "snapshot:inputs/golden-projects/taskflow/ACCEPTANCE.json",
) -> TaskFlowProfile:
    """Build a repeatable partial ISR using only the supplied snapshot payloads."""
    if not isinstance(problem, str) or not problem.strip():
        raise ValueError("problem must be a non-empty string")
    if not isinstance(acceptance, Mapping):
        raise TypeError("acceptance must be a JSON object")

    project_id = acceptance.get("project_id")
    capabilities = acceptance.get("required_capabilities")
    gates = acceptance.get("quality_gates")
    negative_cases = acceptance.get("negative_cases")
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("project_id must be a non-empty string")
    if not isinstance(capabilities, list) or not capabilities or any(
        not isinstance(item, str) or not item.strip() for item in capabilities
    ):
        raise ValueError("required_capabilities must be a non-empty list of names")
    if len(set(capabilities)) != len(capabilities):
        raise ValueError("required_capabilities contains duplicates")
    if not isinstance(gates, Mapping) or any(
        not isinstance(name, str) or not isinstance(enabled, bool)
        for name, enabled in gates.items()
    ):
        raise ValueError("quality_gates must map names to boolean values")
    if not isinstance(negative_cases, list) or any(
        not isinstance(item, str) or not item.strip() for item in negative_cases
    ):
        raise ValueError("negative_cases must be a list of names")
    if len(set(negative_cases)) != len(negative_cases):
        raise ValueError("negative_cases contains duplicates")

    canonical_contract = json.dumps(
        acceptance, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    contract_sha = _digest_bytes(canonical_contract)
    problem_sha = _digest_bytes(problem.encode("utf-8"))

    problem_obligations = []
    active_section = None
    allowed_sections = {
        "Security and correctness requirements",
        "Operational requirements",
    }
    for line_number, line in enumerate(problem.splitlines(), start=1):
        stripped = line.strip()
        if stripped.endswith(":") and not stripped.startswith("-"):
            heading = stripped[:-1]
            active_section = heading if heading in allowed_sections else None
            continue
        if active_section and stripped.startswith("- "):
            statement = stripped[2:].strip()
            problem_obligations.append({
                "requirement_id": _stable_id("REQ-PROBLEM", statement),
                "source_path": problem_source,
                "source_line": line_number,
                "source_section": active_section,
                "statement": statement,
                "status": "UNKNOWN",
            })

    # Explicit semantic mapping to acceptance capabilities. Mapping is not
    # evidence of implementation or correctness; unsupported mappings fail closed.
    obligation_capability_map = {
        "A user can access only workspaces to which they belong.": ("workspace-tenancy",),
        "Cross-workspace reads and writes fail closed.": ("workspace-tenancy",),
        "An assignee must belong to the task's workspace.": ("tasks", "workspace-tenancy"),
        "Owner-only operations cannot be performed by ordinary members.": ("rbac",),
        "Task/project/workspace relationships remain consistent.": ("tasks", "projects", "workspace-tenancy"),
        "Archived records do not reappear in normal active queries.": ("tasks", "projects"),
        "Authorization outcomes are deterministic and fail closed.": ("rbac", "workspace-tenancy"),
        "Requests explicitly declared idempotent do not create duplicate effects.": ("audit-trail",),
        "Security-sensitive mutations have a unique auditable effect identity.": ("audit-trail",),
        "Authentication sessions can be invalidated and invalidated sessions cannot continue to authorize requests.": ("authentication",),
        "Expose health/readiness information.": ("operational-observability",),
        "Produce structured operational/audit evidence.": ("operational-observability", "audit-trail"),
        "Support repeatable automated verification.": ("operational-observability",),
        "Be deployable in a reproducible environment.": ("operational-observability",),
        "Preserve enough provenance to trace each certified capability back to the specification.": ("audit-trail",),
    }
    missing_mappings = sorted(
        item["statement"] for item in problem_obligations
        if item["statement"] not in obligation_capability_map
    )
    if missing_mappings:
        raise ValueError(f"unmapped canonical problem obligations: {missing_mappings}")
    capability_ids = {name: _stable_id("CAP", name) for name in capabilities}
    unknown_targets = sorted({
        target
        for targets in obligation_capability_map.values()
        for target in targets
        if target not in capability_ids
    })
    if unknown_targets:
        raise ValueError(f"problem obligations target undeclared capabilities: {unknown_targets}")

    policy_id = _stable_id("POLICY", "taskflow-spec-obligations")
    obligation_policy = Policy(
        id=policy_id,
        name="TaskFlow Canonical Specification Obligations",
        policy_type=PolicyType.COMPLIANCE,
        description="Source-traced declarative obligations; none imply implementation or verification.",
        strategy="fail_closed_unknown",
        rules=tuple(
            PolicyRule(
                id=item["requirement_id"],
                name=f"Specification obligation at line {item['source_line']}",
                description=item["statement"],
                rule_type="specification_obligation",
                parameters={
                    "source_path": item["source_path"],
                    "source_line": item["source_line"],
                    "source_section": item["source_section"],
                    "status": "UNKNOWN",
                    "target_capabilities": list(obligation_capability_map[item["statement"]]),
                },
                priority=100,
            )
            for item in problem_obligations
        ),
        metadata={"source": problem_source, "evidence_status": "UNKNOWN"},
    )

    criteria = []
    for name, enabled in sorted(gates.items()):
        if enabled:
            criteria.append(AcceptanceCriterion(
                criterion_id=_stable_id("AC-GATE", name),
                obligation=f"Required quality gate must be executed with independently verifiable evidence: {name}",
                kind=ObligationKind.PRESENCE,
            ))
    for name in negative_cases:
        criteria.append(AcceptanceCriterion(
            criterion_id=_stable_id("AC-NEG", name),
            obligation=f"Required negative case must be executed and its observed outcome recorded: {name}",
            kind=ObligationKind.PRESENCE,
        ))
    for item in problem_obligations:
        criterion_id = _stable_id("AC-PROBLEM", item["statement"])
        criteria.append(AcceptanceCriterion(
            criterion_id=criterion_id,
            obligation=f"Canonical specification obligation must be independently demonstrated: {item['statement']}",
            kind=(
                ObligationKind.INVARIANT
                if item["source_section"] == "Security and correctness requirements"
                else ObligationKind.PRESENCE
            ),
            subject_refs=(policy_id,),
        ))
        item["target_capabilities"] = list(obligation_capability_map[item["statement"]])
        item["acceptance_criterion_id"] = criterion_id
        item["policy_id"] = policy_id

    capability_requirement_refs = {name: [_stable_id("REQ", name)] for name in capabilities}
    obligation_requirements = []
    for item in problem_obligations:
        target_names = obligation_capability_map[item["statement"]]
        obligation_requirements.append(Requirement(
            requirement_id=item["requirement_id"],
            statement=item["statement"],
            target_refs=tuple(capability_ids[name] for name in target_names),
            acceptance_refs=(item["acceptance_criterion_id"],),
            constraint_refs=(policy_id,),
        ))
        for name in target_names:
            capability_requirement_refs[name].append(item["requirement_id"])

    capability_genes = tuple(
        BusinessCapability(
            capability_id=capability_ids[name],
            intent=f"Required TaskFlow capability: {name}",
            requirement_refs=tuple(capability_requirement_refs[name]),
        )
        for name in capabilities
    )
    base_requirements = tuple(
        Requirement(
            requirement_id=_stable_id("REQ", name),
            statement=f"Acceptance contract requires capability: {name}",
            target_refs=(capability_ids[name],),
        )
        for name in capabilities
    )
    requirements = base_requirements + tuple(obligation_requirements)

    # Inventory only explicitly named domain concepts from the canonical problem.
    # No fields, relationships, cardinalities, or persistence choices are inferred.
    entity_terms = (
        ("user", "user"),
        ("workspace", "workspace"),
        ("project", "project"),
        ("task", "task"),
        ("comment", "comment"),
        ("activity history", "activity history"),
        ("session", "session"),
    )
    entities = tuple(
        Entity(
            id=_stable_id("ENT", name),
            name=name.title().replace(" ", ""),
            description=f"Concept explicitly named by problem text; schema remains UNKNOWN: {name}",
            metadata={"source": problem_source, "matched_term": term, "schema_status": "UNKNOWN"},
        )
        for name, term in entity_terms
        if term in problem.casefold()
    )
    module = Module(
        id="taskflow-domain",
        name="TaskFlow Domain",
        description="Technology-neutral capability and acceptance profile; entity schemas and relationships unresolved.",
        entities=entities,
        policies=(obligation_policy,),
    )
    system = System(
        id=_stable_id("SYS", project_id),
        name="TaskFlow",
        description="Deterministic partial profile derived from immutable problem and acceptance inputs.",
        modules=(module,),
        metadata=SystemMetadata(
            version=str(acceptance.get("version", "unspecified")),
            description="Provider-free partial ISR; not sufficient for application generation.",
            tags=("taskflow", "partial-profile", "non-certified"),
        ),
        business_capabilities=capability_genes,
        requirements=requirements,
        acceptance_criteria=tuple(criteria),
        global_policies=(
            "Technology-neutral: implementation technology is selected only after ISR validation.",
            "Unspecified domain schema and authorization semantics remain UNKNOWN.",
            "No certification from profile construction or static structure alone.",
        ),
    )
    isr = ISR(
        system=system,
        provenance=ISRProvenance(
            created_by="deterministic-taskflow-profile",
            mutation_description="Built from verified snapshot problem and acceptance contract",
        ),
    )

    traceability = {
        "source_problem": {"path": problem_source, "sha256": problem_sha},
        "problem_obligations": problem_obligations,
        "source_acceptance": {"path": acceptance_source, "sha256": contract_sha},
        "capabilities": [
            {
                "source_pointer": f"/required_capabilities/{index}",
                "source_name": name,
                "requirement_id": _stable_id("REQ", name),
                "capability_id": _stable_id("CAP", name),
            }
            for index, name in enumerate(capabilities)
        ],
        "entities": [
            {
                "entity_id": entity.id,
                "entity_name": entity.name,
                "source": problem_source,
                "matched_term": entity.metadata["matched_term"],
                "schema_status": "UNKNOWN",
            }
            for entity in entities
        ],
        "quality_gates": [
            {"source_pointer": f"/quality_gates/{name}", "criterion_id": _stable_id("AC-GATE", name), "status": "UNKNOWN"}
            for name, enabled in sorted(gates.items()) if enabled
        ],
        "negative_cases": [
            {"source_pointer": f"/negative_cases/{index}", "source_name": name, "criterion_id": _stable_id("AC-NEG", name), "status": "UNKNOWN"}
            for index, name in enumerate(negative_cases)
        ],
    }
    assumptions = (
        {"id": "ASM-DOMAIN-001", "topic": "domain entities and fields", "status": "UNKNOWN", "reason": "The problem names domain concepts, but does not define field schemas, identity rules, or field constraints."},
        {"id": "ASM-REL-001", "topic": "entity relationships and lifecycle", "status": "UNKNOWN", "reason": "Exact relationship cardinalities, deletion semantics, and lifecycle transitions are underspecified."},
        {"id": "ASM-RBAC-001", "topic": "role-permission matrix", "status": "UNKNOWN", "reason": "Owner/manager/member roles are named, but the complete permission matrix is not defined."},
        {"id": "ASM-API-001", "topic": "API and frontend contracts", "status": "UNKNOWN", "reason": "Endpoint shapes, request/response schemas, and view interaction contracts are not specified."},
        {"id": "ASM-IDEM-001", "topic": "idempotent operations", "status": "UNKNOWN", "reason": "The contract requires idempotency where declared but does not identify the complete set of idempotent operations."},
    )
    blockers = (
        "Domain entity schemas, field types, and relationship constraints are UNKNOWN.",
        "Complete role-permission matrix and session invalidation semantics are UNKNOWN.",
        "API/frontend contracts and executable operation semantics are not specified.",
        "15 explicit problem obligations are mapped to typed requirements and a declarative policy, but their implementation semantics and evidence remain UNKNOWN.",
        "No lossless adapter connects this constitutional ISR to the native Cap-C SystemModel compiler path.",
        "No compiler backend output has been generated or independently tested.",
    )
    return TaskFlowProfile(
        isr=isr,
        source_contract_sha256=contract_sha,
        source_problem_sha256=problem_sha,
        traceability=traceability,
        assumptions=assumptions,
        generation_blockers=blockers,
    )



def main(argv: list[str] | None = None) -> int:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Build a deterministic partial TaskFlow ISR profile offline.")
    parser.add_argument("--problem", required=True, help="Path to the snapshotted problem text")
    parser.add_argument("--acceptance", required=True, help="Path to the snapshotted acceptance JSON")
    parser.add_argument("--output", required=True, help="Output JSON path")
    args = parser.parse_args(argv)

    problem_path = Path(args.problem)
    acceptance_path = Path(args.acceptance)
    output_path = Path(args.output)
    problem = problem_path.read_text(encoding="utf-8")
    acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
    profile = build_taskflow_profile(
        problem,
        acceptance,
        problem_source=f"snapshot:{problem_path.as_posix()}",
        acceptance_source=f"snapshot:{acceptance_path.as_posix()}",
    ).as_dict()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(profile, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "profile_sha256": profile["isr_sha256"],
        "capabilities": len(profile["traceability"]["capabilities"]),
        "entities": len(profile["traceability"]["entities"]),
        "problem_obligations": len(profile["traceability"]["problem_obligations"]),
        "quality_gates": len(profile["traceability"]["quality_gates"]),
        "negative_cases": len(profile["traceability"]["negative_cases"]),
        "generation_allowed": profile["generation_allowed"],
        "certified": profile["certified"],
        "output": str(output_path),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
