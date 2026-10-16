"""Fail-closed boundary for source-bound full-stack IR projection.

This module deliberately does not infer routes, authorization, effects, or
replay policies from requirement prose. A trusted projection must provide
explicit mappings with provenance back to source requirement IDs. Until that
contract is populated by the authoritative ISR adapter, callers receive
structured blockers rather than fabricated IR.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping


REQUIRED_LAYERS = ("frontend", "api", "backend", "effects", "consequences")


@dataclass(frozen=True)
class ProjectionBlocker:
    code: str
    message: str
    source_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceBoundProjection:
    status: str
    source_hash: str
    candidate_hash: str
    inputs: tuple[Any, Any, Any, Any, Any] | None
    blockers: tuple[ProjectionBlocker, ...]
    mapping_hash: str | None

    @property
    def ready(self) -> bool:
        return self.status == "ready" and self.inputs is not None and not self.blockers


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _as_dict(value: Any) -> dict[str, Any] | None:
    if hasattr(value, "model_dump"):
        try:
            result = value.model_dump(mode="json")
        except TypeError:
            result = value.model_dump()
    elif hasattr(value, "to_dict"):
        result = value.to_dict()
    elif isinstance(value, Mapping):
        result = dict(value)
    else:
        return None
    return result if isinstance(result, dict) else None


def source_snapshot_from_plan_artifacts(plan_artifacts: Any) -> dict[str, Any]:
    """Create a deterministic snapshot from the real Campaign A PlanArtifacts.

    The snapshot inventories identifiers from the requirement graph and ISR
    graph and preserves the plan/revision/genome payloads. It does not claim
    that these identifiers are equivalent or that semantic lowering occurred.
    """
    if plan_artifacts is None:
        raise ValueError("PlanArtifacts are required")

    def dump(value: Any, label: str) -> dict[str, Any]:
        payload = _as_dict(value)
        if payload is None:
            raise ValueError(f"{label} is not canonically serializable")
        return payload

    plan = dump(getattr(plan_artifacts, "plan", None), "compilation plan")
    revision = dump(getattr(plan_artifacts, "revision", None), "ISR revision")
    genome = dump(getattr(plan_artifacts, "genome", None), "genome")
    req_graph = dump(getattr(plan_artifacts, "requirement_graph", None), "requirement graph")

    refs: set[str] = set()
    req_nodes = req_graph.get("nodes")
    if isinstance(req_nodes, Mapping):
        refs.update(str(key) for key in req_nodes)
        for node in req_nodes.values():
            if isinstance(node, Mapping):
                node_id = node.get("id")
                if isinstance(node_id, str) and node_id:
                    refs.add(node_id)
    elif isinstance(req_nodes, (list, tuple)):
        for node in req_nodes:
            if isinstance(node, Mapping) and isinstance(node.get("id"), str):
                refs.add(node["id"])

    revision_graph = revision.get("graph")
    if isinstance(revision_graph, Mapping):
        isr_nodes = revision_graph.get("nodes")
        if isinstance(isr_nodes, Mapping):
            refs.update(str(key) for key in isr_nodes)
        elif isinstance(isr_nodes, (list, tuple)):
            for node in isr_nodes:
                if isinstance(node, Mapping) and isinstance(node.get("id"), str):
                    refs.add(node["id"])

    if not refs:
        raise ValueError("source artifacts expose no canonical requirement/ISR identifiers")

    return {
        "schema": "source-bound-plan-snapshot/1",
        "source_refs": sorted(refs),
        "plan": plan,
        "revision": revision,
        "genome": genome,
        "requirement_graph": req_graph,
        "declared_hashes": {
            "requirement_graph_hash": getattr(plan_artifacts, "requirement_graph_hash", ""),
            "genome_hash": getattr(plan_artifacts, "genome_hash", ""),
            "plan_hash": getattr(plan_artifacts, "plan_hash", ""),
            "isr_content_hash": revision.get("content_hash", ""),
        },
    }


def project_source_bound_full_stack(
    *,
    source_artifacts: Any,
    candidate_files: Mapping[str, str],
    explicit_mapping: Mapping[str, Any] | None = None,
) -> SourceBoundProjection:
    """Validate an explicit source-to-IR mapping; never guess missing semantics.

    explicit_mapping must contain all five layers and provenance references.
    This is a fail-closed contract seam, not yet a semantic lowering engine.
    """
    blockers: list[ProjectionBlocker] = []
    source_dict = _as_dict(source_artifacts)
    if source_dict is None:
        source_hash = ""
        blockers.append(ProjectionBlocker(
            "SBFS-001", "source artifacts are not canonically serializable"
        ))
    else:
        source_hash = _canonical_hash(source_dict)

    if not isinstance(candidate_files, Mapping) or not candidate_files:
        candidate_hash = ""
        blockers.append(ProjectionBlocker(
            "SBFS-002", "candidate file manifest is missing or empty"
        ))
    elif any(not isinstance(path, str) or not path or not isinstance(body, str)
             for path, body in candidate_files.items()):
        candidate_hash = ""
        blockers.append(ProjectionBlocker(
            "SBFS-003", "candidate manifest must map non-empty paths to text contents"
        ))
    else:
        candidate_hash = _canonical_hash(dict(candidate_files))

    if not isinstance(explicit_mapping, Mapping):
        blockers.append(ProjectionBlocker(
            "SBFS-004",
            "explicit source-to-architecture mapping is absent; semantics will not be inferred"
        ))
        mapping_hash = None
    else:
        mapping_hash = _canonical_hash(dict(explicit_mapping))
        missing = [layer for layer in REQUIRED_LAYERS if layer not in explicit_mapping]
        for layer in missing:
            blockers.append(ProjectionBlocker(
                "SBFS-005", f"required architectural layer is unmapped: {layer}"
            ))
        provenance = explicit_mapping.get("provenance")
        if not isinstance(provenance, Mapping):
            blockers.append(ProjectionBlocker(
                "SBFS-006", "mapping provenance is missing"
            ))
        else:
            source_refs = provenance.get("source_refs")
            if not isinstance(source_refs, (list, tuple)) or not source_refs:
                blockers.append(ProjectionBlocker(
                    "SBFS-007", "mapping must reference source requirement/ISR identifiers"
                ))
            elif source_dict is not None:
                known_refs = source_dict.get("source_refs")
                if not isinstance(known_refs, (list, tuple, set)) or not known_refs:
                    blockers.append(ProjectionBlocker(
                        "SBFS-010",
                        "source artifacts do not expose a canonical source_refs inventory",
                    ))
                elif not set(source_refs).issubset(set(known_refs)):
                    blockers.append(ProjectionBlocker(
                        "SBFS-008", "mapping references source identifiers absent from source artifacts",
                        tuple(str(x) for x in source_refs),
                    ))

        for layer in REQUIRED_LAYERS:
            if layer in explicit_mapping and explicit_mapping[layer] is None:
                blockers.append(ProjectionBlocker(
                    "SBFS-009", f"architectural layer is explicitly null: {layer}"
                ))
        if source_dict is not None and isinstance(provenance, Mapping):
            bound_source_hash = provenance.get("source_hash")
            if bound_source_hash is not None and bound_source_hash != source_hash:
                blockers.append(ProjectionBlocker(
                    "SBFS-032",
                    "mapping provenance is bound to a stale source hash; semantic bindings must be rebuilt",
                ))

    if source_dict is not None and isinstance(explicit_mapping, Mapping):
        blockers.extend(_validate_semantic_obligations(source_dict, explicit_mapping))

    # Do not construct IR objects here. A mapping contract is not proof that
    # it has been lowered into canonical IR classes or independently validated.
    return SourceBoundProjection(
        status="blocked" if blockers else "mapping_present_unverified",
        source_hash=source_hash,
        candidate_hash=candidate_hash,
        inputs=None,
        blockers=tuple(blockers),
        mapping_hash=mapping_hash,
    )



@dataclass(frozen=True)
class LoweredFullStackIR:
    """Canonical IR built only from explicit, loss-checked mapping data."""
    frontend: Any | None
    api: Any | None
    backend: Any | None
    effects: tuple[Any, ...]
    consequences: tuple[Any, ...]
    mapping_hash: str
    source_refs: tuple[str, ...]
    findings: tuple[str, ...]

    @property
    def structurally_valid(self) -> bool:
        return not self.findings and all(
            value is not None for value in (self.frontend, self.api, self.backend)
        )


def lower_explicit_mapping_to_full_stack_ir(
    explicit_mapping: Mapping[str, Any],
) -> LoweredFullStackIR:
    """Lower a complete explicit mapping into canonical IR without defaults.

    Unknown keys are rejected to prevent silent semantic loss. This is not a
    natural-language parser and does not infer omitted architecture. All
    security/effect/replay policies must be explicitly supplied by upstream
    source-bound analysis.
    """
    from .api_ir import ApiContractIR, ApiError, ApiOperation, validate_api_contract
    from .implementation_ir import BackendIR, DataFlowIR, FrontendIR, ModuleIR
    from .schema_ir import SchemaField, SchemaIR, validate_schema
    from .effect_coherence import EffectPath
    from .effect_consequences import EffectConsequence

    findings: list[str] = []
    if not isinstance(explicit_mapping, Mapping):
        raise TypeError("explicit_mapping must be a mapping")

    allowed_top = set(REQUIRED_LAYERS) | {"provenance", "requirement_bindings"}
    extra_top = set(explicit_mapping) - allowed_top
    if extra_top:
        findings.append(f"unsupported top-level mapping keys: {sorted(extra_top)}")
    missing = set(REQUIRED_LAYERS) | {"provenance"} - set(explicit_mapping)
    # Parentheses matter: required layers and provenance must all be present.
    missing = (set(REQUIRED_LAYERS) | {"provenance"}) - set(explicit_mapping)
    if missing:
        findings.append(f"missing mapping sections: {sorted(missing)}")

    provenance = explicit_mapping.get("provenance")
    source_refs = provenance.get("source_refs") if isinstance(provenance, Mapping) else None
    if not isinstance(source_refs, (list, tuple)) or not source_refs or any(
        not isinstance(ref, str) or not ref for ref in source_refs
    ):
        findings.append("provenance.source_refs must be a non-empty list of non-empty strings")
        normalized_refs: tuple[str, ...] = ()
    else:
        normalized_refs = tuple(sorted(set(source_refs)))
        if len(normalized_refs) != len(source_refs):
            findings.append("provenance.source_refs contains duplicate identifiers")

    def section(name: str, required: set[str]) -> Mapping[str, Any] | None:
        value = explicit_mapping.get(name)
        if not isinstance(value, Mapping):
            findings.append(f"{name} must be an object")
            return None
        missing_keys = required - set(value)
        extra_keys = set(value) - required
        if missing_keys:
            findings.append(f"{name} missing keys: {sorted(missing_keys)}")
        if extra_keys:
            findings.append(f"{name} has unsupported keys: {sorted(extra_keys)}")
        return value

    frontend_data = section("frontend", {
        "schema_version", "contract_id", "routes", "api_contract_id",
        "quality_obligation_ids", "state_domains", "interaction_flows",
        "accessibility_requirements", "observability_requirements", "modules",
        "data_flows", "security_boundaries", "failure_states", "design_constraints",
    })
    api_data = section("api", {
        "schema_version", "contract_id", "operations", "global_error_contract",
        "auth_scheme", "schemas",
    })
    backend_data = section("backend", {
        "schema_version", "contract_id", "domain_modules", "api_contract_id",
        "quality_obligation_ids", "persistence_targets", "event_targets",
        "observability_requirements", "modules", "data_flows",
        "security_boundaries", "failure_modes",
    })

    def strings(value: Any, label: str) -> tuple[str, ...]:
        if not isinstance(value, (list, tuple)) or any(
            not isinstance(item, str) or not item for item in value
        ):
            findings.append(f"{label} must be a list of non-empty strings")
            return ()
        return tuple(value)

    def modules(value: Any, label: str) -> tuple[Any, ...]:
        if not isinstance(value, (list, tuple)):
            findings.append(f"{label} must be a list")
            return ()
        result = []
        for index, item in enumerate(value):
            if not isinstance(item, Mapping) or set(item) != {
                "module_id", "responsibility", "dependencies", "invariants"
            }:
                findings.append(f"{label}[{index}] has missing/unsupported fields")
                continue
            if not isinstance(item["module_id"], str) or not item["module_id"] or not isinstance(item["responsibility"], str) or not item["responsibility"]:
                findings.append(f"{label}[{index}] lacks module identity/responsibility")
                continue
            result.append(ModuleIR(
                item["module_id"], item["responsibility"],
                strings(item["dependencies"], f"{label}[{index}].dependencies"),
                strings(item["invariants"], f"{label}[{index}].invariants"),
            ))
        return tuple(result)

    def flows(value: Any, label: str) -> tuple[Any, ...]:
        if not isinstance(value, (list, tuple)):
            findings.append(f"{label} must be a list")
            return ()
        result = []
        for index, item in enumerate(value):
            keys = {"flow_id", "source", "destination", "contract", "failure_policy"}
            if not isinstance(item, Mapping) or set(item) != keys or any(
                not isinstance(item[k], str) or not item[k] for k in keys
            ):
                findings.append(f"{label}[{index}] requires explicit flow_id/source/destination/contract/failure_policy")
                continue
            result.append(DataFlowIR(**item))
        return tuple(result)

    api = frontend = backend = None
    if api_data is not None:
        try:
            schema_values = []
            if not isinstance(api_data.get("schemas"), (list, tuple)):
                raise ValueError("api.schemas must be a list")
            for schema in api_data["schemas"]:
                if not isinstance(schema, Mapping) or set(schema) != {"name", "kind", "fields"}:
                    raise ValueError("each schema requires exactly name/kind/fields")
                fields = []
                for field in schema["fields"]:
                    if not isinstance(field, Mapping) or set(field) != {
                        "name", "type", "required", "nullable", "format", "items_type"
                    }:
                        raise ValueError(f"schema {schema['name']} has malformed field")
                    fields.append(SchemaField(**field))
                item = SchemaIR(schema["name"], schema["kind"], tuple(fields))
                findings.extend(validate_schema(item))
                schema_values.append(item)
            operations = []
            if not isinstance(api_data.get("operations"), (list, tuple)):
                raise ValueError("api.operations must be a list")
            for operation in api_data["operations"]:
                if not isinstance(operation, Mapping) or set(operation) != {
                    "operation_id", "method", "path", "request_schema", "response_schema",
                    "authorization_policy", "errors", "idempotency_required", "paginated", "version"
                }:
                    raise ValueError("each API operation must provide every canonical field")
                errors = []
                for error in operation["errors"]:
                    if not isinstance(error, Mapping) or set(error) != {"code", "status", "retryable"}:
                        raise ValueError(f"operation {operation['operation_id']} has malformed error contract")
                    errors.append(ApiError(**error))
                operations.append(ApiOperation(
                    operation_id=operation["operation_id"], method=operation["method"],
                    path=operation["path"], request_schema=operation["request_schema"],
                    response_schema=operation["response_schema"],
                    authorization_policy=operation["authorization_policy"],
                    errors=tuple(errors), idempotency_required=operation["idempotency_required"],
                    paginated=operation["paginated"], version=operation["version"],
                ))
            api = ApiContractIR(
                schema_version=api_data["schema_version"], contract_id=api_data["contract_id"],
                operations=tuple(operations), global_error_contract=api_data["global_error_contract"],
                auth_scheme=api_data["auth_scheme"], schemas=tuple(schema_values),
            )
            findings.extend(validate_api_contract(api))
        except (KeyError, TypeError, ValueError) as exc:
            findings.append(f"API lowering blocked: {exc}")

    if frontend_data is not None:
        try:
            frontend = FrontendIR(
                schema_version=frontend_data["schema_version"],
                contract_id=frontend_data["contract_id"],
                routes=strings(frontend_data["routes"], "frontend.routes"),
                api_contract_id=frontend_data["api_contract_id"],
                quality_obligation_ids=strings(frontend_data["quality_obligation_ids"], "frontend.quality_obligation_ids"),
                state_domains=strings(frontend_data["state_domains"], "frontend.state_domains"),
                interaction_flows=strings(frontend_data["interaction_flows"], "frontend.interaction_flows"),
                accessibility_requirements=strings(frontend_data["accessibility_requirements"], "frontend.accessibility_requirements"),
                observability_requirements=strings(frontend_data["observability_requirements"], "frontend.observability_requirements"),
                modules=modules(frontend_data["modules"], "frontend.modules"),
                data_flows=flows(frontend_data["data_flows"], "frontend.data_flows"),
                security_boundaries=strings(frontend_data["security_boundaries"], "frontend.security_boundaries"),
                failure_states=strings(frontend_data["failure_states"], "frontend.failure_states"),
                design_constraints=strings(frontend_data["design_constraints"], "frontend.design_constraints"),
            )
        except (KeyError, TypeError) as exc:
            findings.append(f"frontend lowering blocked: {exc}")

    if backend_data is not None:
        try:
            backend = BackendIR(
                schema_version=backend_data["schema_version"],
                contract_id=backend_data["contract_id"],
                domain_modules=strings(backend_data["domain_modules"], "backend.domain_modules"),
                api_contract_id=backend_data["api_contract_id"],
                quality_obligation_ids=strings(backend_data["quality_obligation_ids"], "backend.quality_obligation_ids"),
                persistence_targets=strings(backend_data["persistence_targets"], "backend.persistence_targets"),
                event_targets=strings(backend_data["event_targets"], "backend.event_targets"),
                observability_requirements=strings(backend_data["observability_requirements"], "backend.observability_requirements"),
                modules=modules(backend_data["modules"], "backend.modules"),
                data_flows=flows(backend_data["data_flows"], "backend.data_flows"),
                security_boundaries=strings(backend_data["security_boundaries"], "backend.security_boundaries"),
                failure_modes=strings(backend_data["failure_modes"], "backend.failure_modes"),
            )
        except (KeyError, TypeError) as exc:
            findings.append(f"backend lowering blocked: {exc}")

    effect_values: list[Any] = []
    raw_effects = explicit_mapping.get("effects")
    if not isinstance(raw_effects, (list, tuple)):
        findings.append("effects must be a list")
    else:
        for index, item in enumerate(raw_effects):
            keys = {"operation_id", "frontend_flow_id", "domain_module", "effect_id", "authorization_boundary", "consequence"}
            if not isinstance(item, Mapping) or set(item) != keys or any(
                not isinstance(item[k], str) or not item[k] for k in keys
            ):
                findings.append(f"effects[{index}] requires all six explicit EffectPath fields")
                continue
            effect_values.append(EffectPath(**item))

    consequence_values: list[Any] = []
    raw_consequences = explicit_mapping.get("consequences")
    if not isinstance(raw_consequences, (list, tuple)):
        findings.append("consequences must be a list")
    else:
        for index, item in enumerate(raw_consequences):
            keys = {"effect_id", "persistence", "event", "idempotency_key", "uniqueness_constraint", "retry_policy", "concurrency_policy", "recovery_policy"}
            if not isinstance(item, Mapping) or set(item) != keys or any(
                not isinstance(item[k], str) for k in keys
            ):
                findings.append(f"consequences[{index}] requires all eight explicit EffectConsequence fields")
                continue
            consequence_values.append(EffectConsequence(**item))

    return LoweredFullStackIR(
        frontend=frontend, api=api, backend=backend,
        effects=tuple(effect_values), consequences=tuple(consequence_values),
        mapping_hash=_canonical_hash(dict(explicit_mapping)),
        source_refs=normalized_refs,
        findings=tuple(findings),
    )



@dataclass(frozen=True)
class ArchitectureFacts:
    """Loss-aware facts extracted from authoritative plan/ISR snapshots.

    These facts are not full-stack IR and never imply that omitted frontend,
    API-operation, authorization-enforcement, or effect semantics are known.
    """
    services: tuple[dict[str, Any], ...]
    data_models: tuple[dict[str, Any], ...]
    published_events: tuple[dict[str, Any], ...]
    consumed_events: tuple[dict[str, Any], ...]
    security_policy_ids: tuple[str, ...]
    isr_nodes: tuple[dict[str, Any], ...]
    isr_edges: tuple[dict[str, Any], ...]
    source_refs: tuple[str, ...]
    source_hash: str
    blockers: tuple[str, ...]

    @property
    def complete_for_full_stack(self) -> bool:
        # The current PlanArtifacts schema does not encode all required layers.
        return False


def extract_architecture_facts(snapshot: Mapping[str, Any]) -> ArchitectureFacts:
    """Extract only explicit service/data/event/security/ISR facts.

    No route, HTTP operation, auth policy, event delivery guarantee, or effect
    policy is synthesized from identifiers or names.
    """
    if not isinstance(snapshot, Mapping):
        raise TypeError("snapshot must be a mapping")

    blockers: list[str] = []
    plan = snapshot.get("plan")
    revision = snapshot.get("revision")
    if not isinstance(plan, Mapping):
        plan = {}
        blockers.append("compilation plan is missing")
    if not isinstance(revision, Mapping):
        revision = {}
        blockers.append("ISR revision is missing")

    raw_services = plan.get("services")
    if not isinstance(raw_services, (list, tuple)):
        raw_services = []
        blockers.append("plan services are not explicitly represented as a list")

    services: list[dict[str, Any]] = []
    data_models: list[dict[str, Any]] = []
    published: list[dict[str, Any]] = []
    consumed: list[dict[str, Any]] = []
    security_ids: set[str] = set()
    seen_service_ids: set[str] = set()
    seen_model_ids: set[str] = set()
    seen_event_ids: set[str] = set()

    def collect_events(value: Any, *, service_id: str, direction: str) -> None:
        if not isinstance(value, (list, tuple)):
            blockers.append(f"service {service_id} {direction} events are malformed")
            return
        for event in value:
            if not isinstance(event, Mapping) or not isinstance(event.get("id"), str) or not event.get("id") or not isinstance(event.get("name"), str) or not event.get("name"):
                blockers.append(f"service {service_id} has event without explicit id/name")
                continue
            event_id = event["id"]
            identity = f"{direction}:{service_id}:{event_id}"
            if identity in seen_event_ids:
                blockers.append(f"duplicate event declaration: {identity}")
                continue
            seen_event_ids.add(identity)
            item = {"id": event_id, "name": event["name"], "service_id": service_id}
            (published if direction == "published" else consumed).append(item)

    for index, service in enumerate(raw_services):
        if not isinstance(service, Mapping) or not all(
            isinstance(service.get(key), str) and service.get(key)
            for key in ("id", "name")
        ):
            blockers.append(f"service[{index}] lacks explicit id/name")
            continue
        service_id = service["id"]
        if service_id in seen_service_ids:
            blockers.append(f"duplicate service id: {service_id}")
            continue
        seen_service_ids.add(service_id)
        services.append({"id": service_id, "name": service["name"]})

        raw_models = service.get("data_models")
        if not isinstance(raw_models, (list, tuple)):
            blockers.append(f"service {service_id} data_models are malformed")
        else:
            for model in raw_models:
                if not isinstance(model, Mapping) or not all(
                    isinstance(model.get(key), str) and model.get(key)
                    for key in ("id", "entity_name")
                ):
                    blockers.append(f"service {service_id} has data model without explicit id/entity_name")
                    continue
                if model["id"] in seen_model_ids:
                    blockers.append(f"duplicate data model id: {model['id']}")
                    continue
                seen_model_ids.add(model["id"])
                data_models.append({
                    "id": model["id"], "entity_name": model["entity_name"],
                    "service_id": service_id,
                })

        collect_events(service.get("published_events", []), service_id=service_id, direction="published")
        collect_events(service.get("consumed_events", []), service_id=service_id, direction="consumed")

    raw_security = plan.get("security")
    if not isinstance(raw_security, (list, tuple)):
        blockers.append("plan security policies are not explicitly represented as a list")
    else:
        for policy in raw_security:
            if not isinstance(policy, Mapping) or not isinstance(policy.get("policy_id"), str) or not policy.get("policy_id"):
                blockers.append("security policy lacks explicit policy_id")
                continue
            security_ids.add(policy["policy_id"])

    graph = revision.get("graph")
    if not isinstance(graph, Mapping):
        graph = {}
        blockers.append("ISR graph is missing")
    def normalize_graph_items(raw: Any, label: str) -> tuple[dict[str, Any], ...]:
        if isinstance(raw, Mapping):
            items = []
            for key, value in raw.items():
                if not isinstance(value, Mapping):
                    blockers.append(f"ISR {label} {key} is not an object")
                    continue
                item = dict(value)
                item.setdefault("id", str(key))
                items.append(item)
            return tuple(sorted(items, key=lambda item: str(item.get("id", ""))))
        if isinstance(raw, (list, tuple)):
            items = []
            for index, value in enumerate(raw):
                if not isinstance(value, Mapping) or not isinstance(value.get("id"), str) or not value.get("id"):
                    blockers.append(f"ISR {label}[{index}] lacks explicit id")
                    continue
                items.append(dict(value))
            return tuple(sorted(items, key=lambda item: str(item.get("id", ""))))
        blockers.append(f"ISR {label} are not explicitly represented")
        return ()

    isr_nodes = normalize_graph_items(graph.get("nodes"), "nodes")
    isr_edges = normalize_graph_items(graph.get("edges"), "edges")
    refs = snapshot.get("source_refs")
    if not isinstance(refs, (list, tuple)) or not refs or any(not isinstance(ref, str) or not ref for ref in refs):
        blockers.append("canonical source_refs inventory is missing")
        normalized_refs: tuple[str, ...] = ()
    else:
        normalized_refs = tuple(sorted(set(refs)))
        if len(normalized_refs) != len(refs):
            blockers.append("canonical source_refs inventory contains duplicates")

    source_hash = _canonical_hash(dict(snapshot))
    if not services:
        blockers.append("no explicit services are available for architectural lowering")
    if not data_models:
        blockers.append("no explicit data models are available for architectural lowering")
    if not published and not consumed:
        blockers.append("no explicit event declarations are available for event lowering")
    if not security_ids:
        blockers.append("no explicit security policy identifiers are available for security lowering")

    return ArchitectureFacts(
        services=tuple(services),
        data_models=tuple(data_models),
        published_events=tuple(sorted(published, key=lambda item: (item["service_id"], item["id"]))),
        consumed_events=tuple(sorted(consumed, key=lambda item: (item["service_id"], item["id"]))),
        security_policy_ids=tuple(sorted(security_ids)),
        isr_nodes=isr_nodes,
        isr_edges=isr_edges,
        source_refs=normalized_refs,
        source_hash=source_hash,
        blockers=tuple(blockers),
    )



@dataclass(frozen=True)
class SourceBoundLowering:
    """Result of binding explicit canonical IR to one immutable source snapshot."""
    source_hash: str
    candidate_hash: str
    mapping_hash: str | None
    lowered: LoweredFullStackIR | None
    blockers: tuple[ProjectionBlocker, ...]

    @property
    def ready_for_verification(self) -> bool:
        return (
            not self.blockers
            and self.lowered is not None
            and self.lowered.structurally_valid
            and bool(self.source_hash)
            and bool(self.candidate_hash)
            and bool(self.mapping_hash)
        )


def lower_source_bound_candidate(
    *,
    source_artifacts: Any,
    candidate_files: Mapping[str, str],
    explicit_mapping: Mapping[str, Any] | None,
) -> SourceBoundLowering:
    """Bind explicit semantic lowering to the exact source and candidate.

    This closes the adapter boundary: source refs must exist in the canonical
    snapshot; every required layer must lower without findings; the mapping
    must declare the exact source and candidate digests it was produced for.
    It does not itself authorize certification or prove runtime enforcement.
    """
    blockers: list[ProjectionBlocker] = []
    source = _as_dict(source_artifacts)
    source_hash = _canonical_hash(source) if source is not None else ""
    if source is None:
        blockers.append(ProjectionBlocker("SBFS-001", "source artifacts are not canonically serializable"))

    candidate_hash = ""
    if not isinstance(candidate_files, Mapping) or not candidate_files:
        blockers.append(ProjectionBlocker("SBFS-002", "candidate file manifest is missing or empty"))
    elif any(not isinstance(path, str) or not path or not isinstance(body, str)
             for path, body in candidate_files.items()):
        blockers.append(ProjectionBlocker("SBFS-003", "candidate manifest must map non-empty paths to text contents"))
    else:
        candidate_hash = _canonical_hash(dict(candidate_files))

    if not isinstance(explicit_mapping, Mapping):
        blockers.append(ProjectionBlocker("SBFS-004", "explicit source-to-architecture mapping is absent"))
        return SourceBoundLowering(source_hash, candidate_hash, None, None, tuple(blockers))

    mapping_hash = _canonical_hash(dict(explicit_mapping))
    if source is not None:
        blockers.extend(_validate_requirement_coverage(source, explicit_mapping))
        blockers.extend(_validate_typed_requirement_bindings(source, explicit_mapping))
        blockers.extend(_validate_semantic_obligations(source, explicit_mapping))
    provenance = explicit_mapping.get("provenance")
    refs = provenance.get("source_refs") if isinstance(provenance, Mapping) else None
    if not isinstance(refs, (list, tuple)) or not refs or any(not isinstance(ref, str) or not ref for ref in refs):
        blockers.append(ProjectionBlocker("SBFS-007", "mapping provenance must contain explicit source_refs"))
    elif source is not None:
        known = source.get("source_refs")
        if not isinstance(known, (list, tuple, set)) or not set(refs).issubset(set(known)):
            blockers.append(ProjectionBlocker(
                "SBFS-008", "mapping references source identifiers absent from source snapshot",
                tuple(str(ref) for ref in refs),
            ))

    if not isinstance(provenance, Mapping) or provenance.get("source_hash") != source_hash:
        blockers.append(ProjectionBlocker("SBFS-011", "mapping source_hash does not match the canonical source snapshot"))
    if not isinstance(provenance, Mapping) or provenance.get("candidate_hash") != candidate_hash:
        blockers.append(ProjectionBlocker("SBFS-012", "mapping candidate_hash does not match the candidate file manifest"))

    lowered: LoweredFullStackIR | None = None
    try:
        lowered = lower_explicit_mapping_to_full_stack_ir(explicit_mapping)
    except (TypeError, ValueError, KeyError) as exc:
        blockers.append(ProjectionBlocker("SBFS-013", f"explicit mapping could not be lowered: {type(exc).__name__}: {exc}"))
    if lowered is not None:
        if not lowered.structurally_valid:
            blockers.extend(
                ProjectionBlocker("SBFS-014", finding, lowered.source_refs)
                for finding in lowered.findings
            )
        if source is not None:
            known = set(source.get("source_refs", ()))
            if not set(lowered.source_refs).issubset(known):
                blockers.append(ProjectionBlocker(
                    "SBFS-008", "lowered IR provenance contains unknown source identifiers",
                    lowered.source_refs,
                ))
    return SourceBoundLowering(
        source_hash, candidate_hash, mapping_hash, lowered, tuple(blockers)
    )



def _canonical_requirement_ids(source: Mapping[str, Any]) -> tuple[str, ...] | None:
    """Return requirement node IDs when the source snapshot carries a graph."""
    graph = source.get("requirement_graph")
    if not isinstance(graph, Mapping):
        return None
    nodes = graph.get("nodes")
    if isinstance(nodes, Mapping):
        identifiers = []
        for key, node in nodes.items():
            if not isinstance(key, str) or not key:
                return ()
            if isinstance(node, Mapping):
                node_id = node.get("id", key)
                if not isinstance(node_id, str) or not node_id:
                    return ()
                if node_id != key:
                    # A keyed graph whose key and declared ID disagree is ambiguous.
                    return ()
                identifiers.append(node_id)
            else:
                return ()
        return tuple(sorted(set(identifiers)))
    if isinstance(nodes, (list, tuple)):
        identifiers = []
        for node in nodes:
            if not isinstance(node, Mapping) or not isinstance(node.get("id"), str) or not node.get("id"):
                return ()
            identifiers.append(node["id"])
        if len(set(identifiers)) != len(identifiers):
            return ()
        return tuple(sorted(identifiers))
    return ()


def _validate_requirement_coverage(
    source: Mapping[str, Any],
    mapping: Mapping[str, Any],
) -> tuple[ProjectionBlocker, ...]:
    """Require every authoritative requirement node to have an explicit mapping reference.

    This is traceability coverage, not proof that the mapped decision is
    semantically correct. That still requires domain-specific verification.
    """
    requirement_ids = _canonical_requirement_ids(source)
    if requirement_ids is None:
        # Lightweight callers without a requirement graph retain the explicit
        # source_refs contract; real PlanArtifacts snapshots include the graph.
        return ()
    if not requirement_ids:
        return (ProjectionBlocker(
            "SBFS-015", "requirement graph is malformed or has no unambiguous requirement IDs"
        ),)

    provenance = mapping.get("provenance")
    refs = provenance.get("source_refs") if isinstance(provenance, Mapping) else None
    if not isinstance(refs, (list, tuple)) or any(not isinstance(ref, str) or not ref for ref in refs):
        return (ProjectionBlocker(
            "SBFS-016", "requirement coverage cannot be evaluated without valid provenance.source_refs"
        ),)

    missing = sorted(set(requirement_ids) - set(refs))
    if missing:
        return (ProjectionBlocker(
            "SBFS-017",
            "authoritative requirements are not represented in mapping provenance",
            tuple(missing),
        ),)
    return ()



def _walk_ids(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in {"id", "module_id", "operation_id", "contract_id", "flow_id", "policy_id", "requirement_id", "schema_id", "event_id", "route_id", "decision_id"} and isinstance(item, str) and item:
                found.add(item)
            found.update(_walk_ids(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            found.update(_walk_ids(item))
    return found


def _validate_typed_requirement_bindings(
    source: Mapping[str, Any],
    mapping: Mapping[str, Any],
) -> tuple[ProjectionBlocker, ...]:
    """Require each requirement to target a real typed architecture object.

    The requirement digest binds the decision record to the exact source
    statement. It is not a semantic proof; domain-specific validators must
    still verify that the selected target satisfies the statement.
    """
    graph = source.get("requirement_graph")
    if not isinstance(graph, Mapping):
        return ()
    nodes = graph.get("nodes")
    if isinstance(nodes, Mapping):
        requirements = {}
        for key, node in nodes.items():
            if not isinstance(key, str) or not key or not isinstance(node, Mapping):
                return (ProjectionBlocker("SBFS-018", "cannot validate typed bindings against malformed requirement nodes"),)
            rid = node.get("id", key)
            if rid != key or not isinstance(rid, str) or not rid:
                return (ProjectionBlocker("SBFS-018", "requirement graph key/id mismatch prevents typed binding"),)
            requirements[rid] = node
    elif isinstance(nodes, (list, tuple)):
        requirements = {}
        for node in nodes:
            if not isinstance(node, Mapping) or not isinstance(node.get("id"), str) or not node["id"] or node["id"] in requirements:
                return (ProjectionBlocker("SBFS-018", "requirement list has missing or duplicate IDs"),)
            requirements[node["id"]] = node
    else:
        return (ProjectionBlocker("SBFS-018", "requirement graph has no canonical nodes"),)

    bindings = mapping.get("requirement_bindings")
    if not isinstance(bindings, (list, tuple)):
        return (ProjectionBlocker("SBFS-019", "typed requirement_bindings are required when a requirement graph is present"),)

    layers = {name: mapping.get(name) for name in REQUIRED_LAYERS}
    targets = {name: _walk_ids(value) for name, value in layers.items()}
    seen: set[str] = set()
    blockers: list[ProjectionBlocker] = []
    for binding in bindings:
        if not isinstance(binding, Mapping):
            blockers.append(ProjectionBlocker("SBFS-020", "requirement binding must be an object"))
            continue
        rid = binding.get("requirement_id")
        layer = binding.get("layer")
        target_id = binding.get("target_id")
        if not isinstance(rid, str) or rid not in requirements:
            blockers.append(ProjectionBlocker("SBFS-021", "binding references an unknown requirement", (str(rid),)))
            continue
        if rid in seen:
            blockers.append(ProjectionBlocker("SBFS-022", "requirement has duplicate typed bindings", (rid,)))
            continue
        seen.add(rid)
        node = requirements[rid]
        expected_hash = _canonical_hash(node)
        if binding.get("requirement_hash") != expected_hash:
            blockers.append(ProjectionBlocker("SBFS-023", "binding does not match the current requirement content", (rid,)))
        if layer not in targets or not isinstance(target_id, str) or not target_id or target_id not in targets.get(layer, set()):
            blockers.append(ProjectionBlocker("SBFS-024", "binding target is absent from the declared architecture layer", (rid, str(target_id))))
    missing = sorted(set(requirements) - seen)
    if missing:
        blockers.append(ProjectionBlocker("SBFS-025", "requirements lack typed architecture bindings", tuple(missing)))
    return tuple(blockers)



def _validate_semantic_obligations(source: Mapping[str, Any], mapping: Mapping[str, Any]) -> tuple[ProjectionBlocker, ...]:
    """Enforce minimum typed architecture obligations; linkage is not proof."""
    graph = source.get("requirement_graph")
    nodes = graph.get("nodes") if isinstance(graph, Mapping) else None
    if isinstance(nodes, Mapping):
        requirements = {str(k): v for k, v in nodes.items() if isinstance(v, Mapping)}
    elif isinstance(nodes, (list, tuple)):
        requirements = {v.get("id"): v for v in nodes if isinstance(v, Mapping) and isinstance(v.get("id"), str)}
    else:
        return ()
    bindings = mapping.get("requirement_bindings")
    if not isinstance(bindings, (list, tuple)):
        return ()
    blockers: list[ProjectionBlocker] = []
    layers = {name: mapping.get(name) for name in REQUIRED_LAYERS}

    def objects(value: Any):
        if isinstance(value, Mapping):
            yield value
            for child in value.values():
                yield from objects(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                yield from objects(child)

    for binding in bindings:
        if not isinstance(binding, Mapping):
            continue
        rid, layer, target_id = binding.get("requirement_id"), binding.get("layer"), binding.get("target_id")
        req = requirements.get(rid) if isinstance(rid, str) else None
        if not isinstance(req, Mapping) or not isinstance(layer, str) or not isinstance(target_id, str):
            continue
        statement = str(req.get("statement", req.get("text", ""))).casefold()
        target = next((obj for obj in objects(layers.get(layer)) if target_id in {
            obj.get("id"), obj.get("module_id"), obj.get("operation_id"), obj.get("contract_id"),
            obj.get("policy_id"), obj.get("route_id"), obj.get("schema_id"), obj.get("field_id")
        }), None)
        if target is None:
            continue
        auth = any(x in statement for x in ("authorization", "authorisation", "permission", "role-based", "rbac", "access control", "only the owner", "only administrators", "authorized users", "authorised users"))
        api = any(x in statement for x in ("api", "endpoint", "http", "rest", "request", "response", "route", "pagination", "openapi"))
        integrity = any(x in statement for x in ("must not", "unique", "invariant", "consistency", "integrity", "cannot be empty", "cannot exceed", "foreign key", "atomic"))
        if auth:
            policies = target.get("security_boundaries", target.get("policies", target.get("security_policies")))
            enforceable_policies = [
                p for p in policies if isinstance(p, Mapping)
                and p.get("enforcement") in {"runtime", "middleware", "policy_engine", "database"}
                and isinstance(p.get("policy_id", p.get("id")), str)
            ] if isinstance(policies, (list, tuple)) else []
            if layer != "backend" or not enforceable_policies:
                blockers.append(ProjectionBlocker("SBFS-026", "authorization requirement must bind to a backend object with an explicit enforceable security policy", (rid, target_id)))
            owner_only = any(term in statement for term in ("only the owner", "owner only", "workspace owner"))
            admin_only = any(term in statement for term in ("only administrators", "administrators only", "admin-only"))
            for policy in enforceable_policies:
                roles = policy.get("allowed_roles", policy.get("roles"))
                if isinstance(roles, (list, tuple, set)):
                    normalized_roles = {role.casefold() for role in roles if isinstance(role, str)}
                    broad_roles = {"member", "all", "everyone", "authenticated", "owner"}
                    if owner_only and normalized_roles.intersection(broad_roles - {"owner"}):
                        blockers.append(ProjectionBlocker("SBFS-029", "architecture policy contradicts an owner-only authorization requirement", (rid, target_id, str(policy.get("policy_id", policy.get("id"))))))
                    if admin_only and normalized_roles.intersection(broad_roles):
                        blockers.append(ProjectionBlocker("SBFS-029", "architecture policy contradicts an administrator-only authorization requirement", (rid, target_id, str(policy.get("policy_id", policy.get("id"))))))
            tenant_isolation = any(term in statement for term in ("tenant isolation", "cross-tenant", "other workspaces", "own workspace only", "strict isolation"))
            if tenant_isolation:
                scope = str(target.get("access_scope", target.get("tenant_scope", ""))).casefold()
                if target.get("cross_tenant_access") is True or scope in {"global", "all_tenants", "cross_tenant", "unrestricted"}:
                    blockers.append(ProjectionBlocker("SBFS-030", "architecture data-access scope contradicts tenant-isolation requirements", (rid, target_id)))
        if api:
            is_contract = layer == "api" and bool(target.get("contract_id")) and (isinstance(target.get("operations"), (list, tuple)) or isinstance(target.get("operation_id"), str))
            is_operation = layer == "api" and bool(target.get("operation_id")) and bool(target.get("method")) and bool(target.get("path"))
            if not (is_contract or is_operation):
                blockers.append(ProjectionBlocker("SBFS-027", "API requirement must bind to an explicit API contract or operation", (rid, target_id)))
            if is_operation:
                required_method = next((m for verb, m in (("delete", "DELETE"), ("remove", "DELETE"), ("create", "POST"), ("register", "POST"), ("update", "PATCH"), ("edit", "PATCH"), ("list", "GET"), ("read", "GET"), ("retrieve", "GET")) if re.search(r"\b" + verb + r"\b", statement)), None)
                actual_method = str(target.get("method", "")).upper()
                if required_method and actual_method and actual_method != required_method:
                    blockers.append(ProjectionBlocker("SBFS-031", f"API method {actual_method} contradicts inferred requirement operation {required_method}", (rid, target_id)))
        if integrity:
            invariants = target.get("invariants")
            fields = target.get("fields")
            has_invariants = isinstance(invariants, (list, tuple)) and bool(invariants)
            has_constraints = isinstance(fields, (list, tuple)) and any(isinstance(f, Mapping) and any(k in f for k in ("constraints", "required", "unique", "minimum", "maximum")) for f in fields)
            if layer != "backend" or not (has_invariants or has_constraints):
                blockers.append(ProjectionBlocker("SBFS-028", "data-integrity requirement must bind to a backend invariant or constrained data schema", (rid, target_id)))
    return tuple(blockers)


@dataclass(frozen=True)
class SemanticCorrespondenceResult:
    """Recomputed evidence for source → explicit mapping → exact candidate."""
    passed: bool
    source_hash: str
    mapping_hash: str
    candidate_hash: str
    findings: tuple[str, ...]


class SourceBoundSemanticCorrespondenceVerifier:
    """Production verifier for structural semantic correspondence.

    Inputs must contain source_artifacts, explicit_mapping, and candidate_files.
    Hashes are recomputed from those payloads; caller-supplied hashes are never
    accepted as proof. This verifies source provenance and cross-layer IR
    coherence, not runtime behavior; build/test/runtime gates remain separate.
    """

    def verify_bound(
        self, inputs: Mapping[str, Any], candidate_hash: str,
    ) -> SemanticCorrespondenceResult:
        findings: list[str] = []
        source_hash = ""
        mapping_hash = ""
        computed_candidate_hash = ""

        if not isinstance(inputs, Mapping):
            return SemanticCorrespondenceResult(
                False, "", "", "", ("semantic verifier inputs must be a mapping",)
            )

        source = inputs.get("source_artifacts")
        mapping = inputs.get("explicit_mapping")
        files = inputs.get("candidate_files")
        producer_findings = inputs.get("mapping_producer_findings", ())
        if not isinstance(producer_findings, (list, tuple)):
            findings.append("mapping_producer_findings must be a list")
        else:
            findings.extend(
                f"architecture mapping producer: {item}"
                for item in producer_findings
                if isinstance(item, str) and item
            )

        source_dict = _as_dict(source)
        if source_dict is None:
            findings.append("source_artifacts are missing or not canonically serializable")
        else:
            source_hash = _canonical_hash(source_dict)

        if not isinstance(mapping, Mapping):
            findings.append("explicit_mapping is missing")
        else:
            mapping_hash = _canonical_hash(dict(mapping))
            provenance = mapping.get("provenance")
            if not isinstance(provenance, Mapping):
                findings.append("mapping provenance is missing")
            else:
                if provenance.get("source_hash") != source_hash or not source_hash:
                    findings.append("mapping source_hash does not match recomputed source artifacts")
                refs = provenance.get("source_refs")
                known = source_dict.get("source_refs") if source_dict else None
                if not isinstance(refs, (list, tuple)) or not refs:
                    findings.append("mapping source_refs are missing")
                elif not isinstance(known, (list, tuple, set)) or not set(refs).issubset(set(known)):
                    findings.append("mapping references unknown source identifiers")

        if not isinstance(files, Mapping) or not files:
            findings.append("candidate_files manifest is missing or empty")
        elif any(
            not isinstance(path, str) or not path
            or not isinstance(body, str)
            for path, body in files.items()
        ):
            findings.append("candidate_files must map non-empty paths to text contents")
        else:
            # Exactly matches compiler.core.repository.build_repository.
            canonical_files = json.dumps(
                {key: value for key, value in sorted(files.items())},
                sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            )
            computed_candidate_hash = hashlib.sha256(
                canonical_files.encode("utf-8")
            ).hexdigest()
            if not candidate_hash or computed_candidate_hash != candidate_hash:
                findings.append("candidate hash does not match recomputed repository contents")

        if isinstance(mapping, Mapping):
            try:
                lowered = lower_explicit_mapping_to_full_stack_ir(mapping)
                findings.extend(lowered.findings)
                if lowered.structurally_valid:
                    from .full_stack_verification import verify_full_stack
                    report = verify_full_stack(
                        lowered.frontend, lowered.api, lowered.backend,
                        lowered.effects, lowered.consequences,
                    )
                    findings.extend(
                        f"full-stack coherence: {item!r}" for item in report.findings
                    )
            except Exception as exc:
                findings.append(
                    f"mapping lowering/verification failed closed: {type(exc).__name__}: {exc}"
                )

        return SemanticCorrespondenceResult(
            passed=not findings and bool(source_hash and mapping_hash and computed_candidate_hash),
            source_hash=source_hash,
            mapping_hash=mapping_hash,
            candidate_hash=computed_candidate_hash,
            findings=tuple(findings),
        )


@dataclass(frozen=True)
class ArchitectureMappingProduction:
    """Deterministic ISR-to-architecture mapping attempt with explicit gaps."""
    mapping: Mapping[str, Any] | None
    blockers: tuple[ProjectionBlocker, ...]

    @property
    def complete(self) -> bool:
        return self.mapping is not None and not self.blockers


def produce_architecture_mapping(source_snapshot: Mapping[str, Any]) -> ArchitectureMappingProduction:
    """Derive only architecture semantics explicitly represented in the ISR.

    This producer preserves identifiers and typed relationships. It refuses to
    invent frontend routes, API operation details, effect/replay semantics, or
    consequence policies where the ISR does not carry the required fields.
    A partial structural inventory is returned for diagnostics, but mapping is
    publishable only when all required layers can be represented faithfully.
    """
    blockers: list[ProjectionBlocker] = []
    if not isinstance(source_snapshot, Mapping):
        return ArchitectureMappingProduction(None, (
            ProjectionBlocker("MAP-001", "source snapshot must be a mapping"),
        ))

    revision = source_snapshot.get("revision")
    revision = revision if isinstance(revision, Mapping) else {}
    graph = revision.get("graph")
    graph = graph if isinstance(graph, Mapping) else {}
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, Mapping) or not isinstance(edges, Mapping):
        return ArchitectureMappingProduction(None, (
            ProjectionBlocker("MAP-002", "ISR revision lacks canonical graph nodes/edges"),
        ))

    node_records: dict[str, dict[str, Any]] = {}
    for key, raw in nodes.items():
        if not isinstance(raw, Mapping):
            blockers.append(ProjectionBlocker("MAP-003", f"ISR node {key!r} is not an object"))
            continue
        node_id = raw.get("id", key)
        node_type = raw.get("type")
        if not isinstance(node_id, str) or not node_id or not isinstance(node_type, str):
            blockers.append(ProjectionBlocker("MAP-004", f"ISR node {key!r} lacks a stable id/type"))
            continue
        properties = raw.get("properties", {})
        if not isinstance(properties, Mapping):
            blockers.append(ProjectionBlocker("MAP-005", f"ISR node {node_id!r} properties are malformed"))
            continue
        node_records[node_id] = {
            "id": node_id, "type": node_type,
            "properties": dict(properties),
        }

    edge_records: list[dict[str, Any]] = []
    for key, raw in edges.items():
        if not isinstance(raw, Mapping):
            blockers.append(ProjectionBlocker("MAP-006", f"ISR edge {key!r} is not an object"))
            continue
        edge_id, edge_type = raw.get("id", key), raw.get("type")
        source_id, target_id = raw.get("source_id"), raw.get("target_id")
        if not all(isinstance(value, str) and value for value in (edge_id, edge_type, source_id, target_id)):
            blockers.append(ProjectionBlocker("MAP-007", f"ISR edge {key!r} lacks stable identity/type/endpoints"))
            continue
        if source_id not in node_records or target_id not in node_records:
            blockers.append(ProjectionBlocker("MAP-008", f"ISR edge {edge_id!r} references an unknown endpoint", (source_id, target_id)))
            continue
        edge_records.append({
            "id": edge_id, "type": edge_type,
            "source_id": source_id, "target_id": target_id,
            "properties": dict(raw.get("properties", {}))
            if isinstance(raw.get("properties", {}), Mapping) else {},
        })

    def typed(*types: str) -> list[dict[str, Any]]:
        return [dict(node) for node in node_records.values() if node["type"] in types]

    domains = typed("domain")
    capabilities = typed("capability")
    services = typed("service")
    apis = typed("api")
    data_models = typed("data_model")
    events = typed("event")
    policies = typed("security_policy")
    infra = typed("infrastructure_target")
    requirements = typed("requirement_ref")
    frontend_routes = typed("frontend_route")
    frontend_interactions = typed("frontend_interaction")
    effects = typed("effect")
    invariants = typed("invariant")
    consequences = typed("consequence")

    if not requirements:
        blockers.append(ProjectionBlocker(
            "MAP-REQ-000", "ISR contains no authoritative requirement references to bind architecture against",
        ))

    # The ISR graph currently carries API node identity but not necessarily
    # operation-level method/path/schema/error/idempotency contracts.
    for api in apis:
        props = api["properties"]
        if not all(key in props for key in ("operations", "global_error_contract", "auth_scheme")):
            blockers.append(ProjectionBlocker(
                "MAP-API-001",
                f"API {api['id']!r} lacks explicit operations/error/auth contract fields",
                (api["id"],),
            ))
    for api in apis:
        operations = api["properties"].get("operations")
        if not isinstance(operations, list) or not operations:
            blockers.append(ProjectionBlocker(
                "MAP-API-002", f"API {api['id']!r} must declare at least one operation",
                (api["id"],),
            ))
            continue
        seen_operation_ids: set[str] = set()
        for operation in operations:
            if not isinstance(operation, Mapping):
                blockers.append(ProjectionBlocker("MAP-API-003", f"API {api['id']!r} contains a malformed operation", (api["id"],)))
                continue
            operation_id, method, path = operation.get("operation_id"), operation.get("method"), operation.get("path")
            if not all(isinstance(value, str) and value.strip() for value in (operation_id, method, path)):
                blockers.append(ProjectionBlocker("MAP-API-004", f"API {api['id']!r} operation lacks operation_id, method or path", (api["id"],)))
                continue
            if operation_id in seen_operation_ids:
                blockers.append(ProjectionBlocker("MAP-API-005", f"API {api['id']!r} repeats operation_id {operation_id!r}", (api["id"],)))
            seen_operation_ids.add(operation_id)
            if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}:
                blockers.append(ProjectionBlocker("MAP-API-006", f"API operation {operation_id!r} has unsupported HTTP method {method!r}", (api["id"], operation_id)))
            if not path.startswith("/"):
                blockers.append(ProjectionBlocker("MAP-API-007", f"API operation {operation_id!r} path must be absolute", (api["id"], operation_id)))

    for service in services:
        props = service["properties"]
        if not isinstance(props.get("responsibility", props.get("description")), str):
            blockers.append(ProjectionBlocker(
                "MAP-SVC-001", f"service {service['id']!r} lacks an explicit responsibility",
                (service["id"],),
            ))
    for event in events:
        props = event["properties"]
        if not all(key in props for key in ("delivery_guarantee", "ordering", "payload_schema")):
            blockers.append(ProjectionBlocker(
                "MAP-EVT-001", f"event {event['id']!r} lacks delivery, ordering, or payload semantics",
                (event["id"],),
            ))
    for model in data_models:
        props = model["properties"]
        if not all(key in props for key in ("fields", "invariants")):
            blockers.append(ProjectionBlocker(
                "MAP-DATA-001", f"data model {model['id']!r} lacks explicit fields or invariants",
                (model["id"],),
            ))

    if not frontend_routes or not frontend_interactions:
        blockers.append(ProjectionBlocker(
            "MAP-FE-001", "ISR requires first-class frontend routes and interactions",
        ))
    for route in frontend_routes:
        if not any(key in route["properties"] for key in ("path", "route", "url")):
            blockers.append(ProjectionBlocker("MAP-FE-002", f"frontend route {route['id']!r} lacks an explicit path", (route["id"],)))
    for interaction in frontend_interactions:
        if not all(key in interaction["properties"] for key in ("action", "flow_id")):
            blockers.append(ProjectionBlocker("MAP-FE-003", f"frontend interaction {interaction['id']!r} lacks action/flow semantics", (interaction["id"],)))
    if not effects:
        blockers.append(ProjectionBlocker("MAP-EFFECT-001", "ISR contains no first-class effect nodes"))
    for effect in effects:
        if not all(key in effect["properties"] for key in ("effect_type", "idempotency_policy", "replay_policy", "failure_policy")):
            blockers.append(ProjectionBlocker("MAP-EFFECT-002", f"effect {effect['id']!r} lacks type/idempotency/replay/failure semantics", (effect["id"],)))
    if not invariants:
        blockers.append(ProjectionBlocker("MAP-INV-001", "ISR contains no first-class invariant nodes"))
    for invariant in invariants:
        if not all(key in invariant["properties"] for key in ("expression", "enforcement_point", "verification_method")):
            blockers.append(ProjectionBlocker("MAP-INV-002", f"invariant {invariant['id']!r} lacks expression/enforcement/verification semantics", (invariant["id"],)))
    if not consequences:
        blockers.append(ProjectionBlocker("MAP-CONSEQ-001", "ISR contains no first-class consequence nodes"))
    for consequence in consequences:
        if not all(key in consequence["properties"] for key in ("trigger", "outcome", "failure_policy")):
            blockers.append(ProjectionBlocker("MAP-CONSEQ-002", f"consequence {consequence['id']!r} lacks trigger/outcome/failure semantics", (consequence["id"],)))
    if not policies:
        blockers.append(ProjectionBlocker("MAP-SEC-001", "ISR contains no explicit security-policy nodes"))

    # Typed requirement obligations: a reference is not traceability by itself.
    # Each requirement must carry semantic content and resolve through explicit
    # satisfies -> capability -> implemented_by -> service edges. The target
    # must expose a typed enforcement/verification construct appropriate to the
    # requirement class; otherwise the complete mapping is blocked.
    requirement_obligations: list[dict[str, Any]] = []
    requirement_edges = [
        edge for edge in edge_records
        if edge["type"] == "satisfies" and edge["target_id"] in {item["id"] for item in requirements}
    ]
    capabilities_by_id = {item["id"]: item for item in capabilities}
    services_by_id = {item["id"]: item for item in services}
    policy_by_id = {item["id"]: item for item in policies}
    invariants_by_id = {item["id"]: item for item in invariants}
    api_by_id = {item["id"]: item for item in apis}

    for requirement in requirements:
        props = requirement["properties"]
        requirement_id = props.get("requirement_id", requirement["id"])
        semantic_content = props.get("semantic_content", props.get("statement", props.get("text")))
        if not isinstance(requirement_id, str) or not requirement_id.strip():
            blockers.append(ProjectionBlocker("MAP-REQ-001", f"requirement reference {requirement['id']!r} lacks a stable requirement_id", (requirement["id"],)))
            continue
        if not isinstance(semantic_content, str) or not semantic_content.strip():
            blockers.append(ProjectionBlocker("MAP-REQ-002", f"requirement {requirement_id!r} lacks authoritative semantic content", (requirement["id"],)))
            continue
        if not isinstance(props.get("source_ref"), str) or not props.get("source_ref"):
            blockers.append(ProjectionBlocker("MAP-REQ-003", f"requirement {requirement_id!r} lacks source_ref provenance", (requirement["id"],)))
        if not isinstance(props.get("revision"), (str, int)) or str(props.get("revision")).strip() == "":
            blockers.append(ProjectionBlocker("MAP-REQ-004", f"requirement {requirement_id!r} lacks an authoritative revision", (requirement["id"],)))

        matches = [edge for edge in requirement_edges if edge["target_id"] == requirement["id"]]
        if len(matches) != 1:
            blockers.append(ProjectionBlocker("MAP-REQ-005", f"requirement {requirement_id!r} must have exactly one explicit satisfies edge; found {len(matches)}", (requirement["id"],)))
            continue
        satisfies_edge = matches[0]
        capability = capabilities_by_id.get(satisfies_edge["source_id"])
        if capability is None:
            blockers.append(ProjectionBlocker("MAP-REQ-006", f"requirement {requirement_id!r} must be satisfied by a typed capability", (requirement["id"], satisfies_edge["id"])))
            continue
        implementation_edges = [
            edge for edge in edge_records
            if edge["type"] == "implemented_by" and edge["source_id"] == capability["id"]
        ]
        if len(implementation_edges) != 1:
            blockers.append(ProjectionBlocker("MAP-REQ-007", f"capability {capability['id']!r} for requirement {requirement_id!r} must map to exactly one service", (requirement["id"], capability["id"])))
            continue
        service = services_by_id.get(implementation_edges[0]["target_id"])
        if service is None:
            blockers.append(ProjectionBlocker("MAP-REQ-008", f"requirement {requirement_id!r} maps to a non-service implementation target", (requirement["id"], implementation_edges[0]["id"])))
            continue

        requirement_kind = str(props.get("requirement_kind", props.get("kind", "functional"))).lower()
        enforcement_targets: list[dict[str, str]] = []
        if requirement_kind in {"authorization", "security", "rbac", "abac"}:
            linked_policy_edges = [
                edge for edge in edge_records
                if edge["type"] in {"enforced_by", "governed_by"}
                and edge["source_id"] == service["id"]
                and edge["target_id"] in policy_by_id
            ]
            if not linked_policy_edges:
                blockers.append(ProjectionBlocker("MAP-REQ-SEC-001", f"authorization requirement {requirement_id!r} has no explicit service-to-security-policy enforcement edge", (requirement["id"], service["id"])))
            enforcement_targets.extend({"kind": "security_policy", "id": edge["target_id"]} for edge in linked_policy_edges)
        elif requirement_kind in {"data_integrity", "integrity", "consistency"}:
            linked_invariants = [
                edge for edge in edge_records
                if edge["type"] in {"requires_invariant", "enforces_invariant"}
                and edge["source_id"] in {service["id"], capability["id"]}
                and edge["target_id"] in invariants_by_id
            ]
            if not linked_invariants:
                blockers.append(ProjectionBlocker("MAP-REQ-DATA-001", f"data-integrity requirement {requirement_id!r} has no explicit applicable invariant edge", (requirement["id"], service["id"])))
            enforcement_targets.extend({"kind": "invariant", "id": edge["target_id"]} for edge in linked_invariants)
        elif requirement_kind in {"api", "api_contract", "interface"}:
            linked_api_edges = [
                edge for edge in edge_records
                if edge["type"] in {"exposes", "implements_contract", "serves"}
                and edge["source_id"] == service["id"]
                and edge["target_id"] in api_by_id
            ]
            if not linked_api_edges:
                blockers.append(ProjectionBlocker("MAP-REQ-API-001", f"API requirement {requirement_id!r} has no explicit service-to-API contract edge", (requirement["id"], service["id"])))
            enforcement_targets.extend({"kind": "api_contract", "id": edge["target_id"]} for edge in linked_api_edges)
        else:
            enforcement_targets.append({"kind": "service", "id": service["id"]})

        verification_method = props.get("verification_method")
        if not isinstance(verification_method, str) or not verification_method.strip():
            blockers.append(ProjectionBlocker("MAP-REQ-009", f"requirement {requirement_id!r} lacks a verification method", (requirement["id"],)))
        requirement_obligations.append({
            "requirement_id": requirement_id,
            "requirement_node_id": requirement["id"],
            "semantic_content": semantic_content,
            "requirement_kind": requirement_kind,
            "source_ref": props.get("source_ref"),
            "revision": str(props.get("revision", "")),
            "capability_id": capability["id"],
            "service_id": service["id"],
            "enforcement_targets": enforcement_targets,
            "verification_method": verification_method,
            "satisfies_edge_id": satisfies_edge["id"],
            "implementation_edge_id": implementation_edges[0]["id"],
        })

    source_refs = sorted(set(str(value) for value in source_snapshot.get("source_refs", ())))
    source_hash = _canonical_hash(dict(source_snapshot))
    inventory = {
        "schema": "isr-architecture-inventory/2",
        "domains": domains,
        "capabilities": capabilities,
        "services": services,
        "apis": apis,
        "data_models": data_models,
        "events": events,
        "security_policies": policies,
        "infrastructure_targets": infra,
        "requirement_refs": requirements,
        "frontend_routes": frontend_routes,
        "frontend_interactions": frontend_interactions,
        "effects": effects,
        "invariants": invariants,
        "consequences": consequences,
        "edges": sorted(edge_records, key=lambda item: item["id"]),
        "source_refs": source_refs,
        "source_hash": source_hash,
    }

    # A structurally populated mapping is still incomplete if the ISR
    # does not connect its layers. Validate relationships explicitly; never
    # infer a missing route/API/service/effect/invariant link from names.
    def has_edge(edge_type: str, source_types: set[str], target_types: set[str]) -> bool:
        return any(
            edge["type"] == edge_type
            and node_records[edge["source_id"]]["type"] in source_types
            and node_records[edge["target_id"]]["type"] in target_types
            for edge in edge_records
        )

    if frontend_routes and apis and not has_edge("routes_to", {"frontend_route"}, {"api"}):
        blockers.append(ProjectionBlocker(
            "MAP-REL-001", "frontend routes and APIs exist but no explicit routes_to relationship connects them",
        ))
    if frontend_interactions and apis and not has_edge("invokes", {"frontend_interaction"}, {"api"}):
        blockers.append(ProjectionBlocker(
            "MAP-REL-002", "frontend interactions and APIs exist but no explicit invokes relationship connects them",
        ))
    if capabilities and services and not has_edge("implemented_by", {"capability"}, {"service"}):
        blockers.append(ProjectionBlocker(
            "MAP-REL-003", "capabilities and services exist but no explicit implemented_by relationship connects them",
        ))
    if effects and invariants and not has_edge("requires_invariant", {"effect"}, {"invariant"}):
        blockers.append(ProjectionBlocker(
            "MAP-REL-004", "effects and invariants exist but no explicit requires_invariant relationship connects them",
        ))
    if effects and consequences and not has_edge("consequence_of", {"consequence"}, {"effect"}):
        blockers.append(ProjectionBlocker(
            "MAP-REL-005", "consequences and effects exist but no explicit consequence_of relationship connects them",
        ))
    for edge in edge_records:
        if edge["type"] in {"routes_to", "invokes", "implemented_by", "requires_invariant", "consequence_of", "emits", "consumes"}:
            expected = {
                "routes_to": ({"frontend_route"}, {"api"}),
                "invokes": ({"frontend_interaction"}, {"api"}),
                "implemented_by": ({"capability"}, {"service"}),
                "requires_invariant": ({"effect"}, {"invariant"}),
                "consequence_of": ({"consequence"}, {"effect"}),
                "emits": ({"service"}, {"event"}),
                "consumes": ({"service"}, {"event"}),
            }[edge["type"]]
            actual = (
                node_records[edge["source_id"]]["type"],
                node_records[edge["target_id"]]["type"],
            )
            if actual[0] not in expected[0] or actual[1] not in expected[1]:
                blockers.append(ProjectionBlocker(
                    "MAP-REL-006",
                    f"relationship {edge['id']!r} has incompatible endpoint types for {edge['type']!r}",
                    (edge["id"], edge["source_id"], edge["target_id"]),
                ))

    # Derive traceability only through explicit ISR edges. A capability must
    # satisfy a requirement reference and be implemented by a service; no
    # lexical guess is used to connect requirements to implementation targets.
    requirement_bindings: list[dict[str, str]] = []
    refs_by_id = {item["id"]: item for item in requirements}
    capabilities_by_id = {item["id"]: item for item in capabilities}
    for edge in edge_records:
        if edge["type"] != "satisfies" or edge["target_id"] not in refs_by_id:
            continue
        capability = capabilities_by_id.get(edge["source_id"])
        if capability is None:
            continue
        for implementation_edge in edge_records:
            if implementation_edge["type"] != "implemented_by" or implementation_edge["source_id"] != capability["id"]:
                continue
            service_id = implementation_edge["target_id"]
            requirement_id = refs_by_id[edge["target_id"]]["properties"].get("requirement_id", edge["target_id"])
            if isinstance(requirement_id, str) and requirement_id:
                requirement_bindings.append({
                    "requirement_id": requirement_id,
                    "layer": "backend",
                    "target_id": service_id,
                    "source_edge_id": edge["id"],
                    "implementation_edge_id": implementation_edge["id"],
                })

    # Full mapping follows the verifier's typed five-layer contract. If any
    # required semantic field is absent, only diagnostic blockers are returned.
    explicit_mapping = {
        "schema": "source-bound-architecture-mapping/1",
        "frontend": {"routes": frontend_routes, "interactions": frontend_interactions},
        "api": {"contracts": apis, "events": events},
        "backend": {"services": services, "data_models": data_models, "security_policies": policies, "domains": domains, "capabilities": capabilities},
        "effects": effects,
        "consequences": {"invariants": invariants, "consequences": consequences},
        "requirement_bindings": sorted(requirement_bindings, key=lambda item: (item["requirement_id"], item["target_id"])),
        "requirement_obligations": sorted(requirement_obligations, key=lambda item: item["requirement_id"]),
        "provenance": {"source_refs": source_refs, "source_hash": source_hash, "isr_content_hash": revision.get("content_hash", "")},
        "inventory": inventory,
    }
    return ArchitectureMappingProduction(
        mapping=explicit_mapping if not blockers else None,
        blockers=tuple(blockers),
    )
