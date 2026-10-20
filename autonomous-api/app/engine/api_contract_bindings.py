"""Verify backend/frontend contracts against a canonical API contract."""
from __future__ import annotations
from .api_ir import ApiContractIR, validate_api_contract
from .backend_ir import BackendProjectIR
from .frontend_ir import FrontendProjectIR
from .backend_contracts import contract_manifest
from .frontend_contracts import frontend_contract_manifest
from .schema_ir import schema_map


def verify_api_contract_bindings(
    api: ApiContractIR,
    backend: BackendProjectIR,
    frontend: FrontendProjectIR,
) -> tuple[str, ...]:
    findings = list(validate_api_contract(api))
    canonical = {
        (o.method.upper(), o.path): o for o in api.operations
    }
    for op in contract_manifest(backend)["operations"]:
        key = (op["method"].upper(), op["path"])
        c = canonical.get(key)
        if c is None:
            findings.append(f"backend operation not in API contract: {key}")
            continue
        if op["request_schema"] != c.request_schema:
            findings.append(f"request schema mismatch: {key}")
        if op["response_schema"] != c.response_schema:
            findings.append(f"response schema mismatch: {key}")
        if op["authorization_policy"] != c.authorization_policy:
            findings.append(f"authorization mismatch: {key}")

    fm = frontend_contract_manifest(frontend)
    canonical_by_id = {operation.operation_id: operation for operation in api.operations}
    schemas_by_name = schema_map(api.schemas)
    for screen in fm["screens"]:
        bindings = screen.get("action_bindings", [])
        if bindings:
            for binding in bindings:
                operation = canonical_by_id.get(binding["api_operation_id"])
                if operation is None:
                    findings.append(
                        f"frontend action references unknown API operation: {binding['api_operation_id']}"
                    )
                    continue
                if operation.method.upper() != binding["method"].upper():
                    findings.append(f"frontend action HTTP method mismatch: {binding['action_id']}")
                if operation.path != binding["path"]:
                    findings.append(f"frontend action API path mismatch: {binding['action_id']}")
                if binding["authorization_policy"] and operation.authorization_policy != binding["authorization_policy"]:
                    findings.append(f"frontend action authorization mismatch: {binding['action_id']}")
                if operation.request_schema:
                    schema = schemas_by_name.get(operation.request_schema)
                    if schema is None:
                        findings.append(f"frontend action request schema is unknown: {operation.request_schema}")
                        continue
                    available = set(binding["request_fields"])
                    declared = {field.name for field in schema.fields}
                    unknown = sorted(available - declared)
                    missing = sorted(field.name for field in schema.fields if field.required and field.name not in available)
                    if unknown:
                        findings.append(f"frontend action has unknown request fields: {binding['action_id']}: {unknown}")
                    if missing:
                        findings.append(f"frontend action omits required request fields: {binding['action_id']}: {missing}")
            continue
        if not screen["data_contract"] and not screen["actions"]:
            continue
        matches = [c for (method, path), c in canonical.items() if path == screen["route"]]
        if not matches:
            findings.append(f"frontend route not in API contract: {screen['route']}")
            continue
        if screen["authorization_policy"] and not any(
            c.authorization_policy == screen["authorization_policy"] for c in matches
        ):
            findings.append(f"frontend authorization mismatch: {screen['screen_id']}")

    return tuple(findings)
