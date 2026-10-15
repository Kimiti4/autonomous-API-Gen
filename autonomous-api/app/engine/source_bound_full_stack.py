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

    allowed_top = set(REQUIRED_LAYERS) | {"provenance"}
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
