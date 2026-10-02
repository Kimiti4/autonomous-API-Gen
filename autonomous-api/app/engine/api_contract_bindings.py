"""Verify backend/frontend contracts against a canonical API contract."""
from __future__ import annotations
from .api_ir import ApiContractIR, validate_api_contract
from .backend_ir import BackendProjectIR
from .frontend_ir import FrontendProjectIR
from .backend_contracts import contract_manifest
from .frontend_contracts import frontend_contract_manifest


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
    for screen in fm["screens"]:
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
