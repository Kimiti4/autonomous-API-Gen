"""Deterministic OpenAPI 3.1 projection of the technology-neutral API IR."""
from __future__ import annotations
from .api_ir import ApiContractIR


def to_openapi(ir: ApiContractIR) -> dict:
    paths: dict = {}
    for op in sorted(ir.operations, key=lambda x: (x.path, x.method.upper(), x.operation_id)):
        method = op.method.lower()
        item = paths.setdefault(op.path, {})
        operation = {
            "operationId": op.operation_id,
            "responses": {
                str(e.status): {
                    "description": e.code,
                    "x-error-code": e.code,
                    "x-retryable": e.retryable,
                }
                for e in op.errors
            },
            "x-authorization-policy": op.authorization_policy,
            "x-idempotency-required": op.idempotency_required,
            "x-paginated": op.paginated,
            "x-api-version": op.version,
        }
        if not operation["responses"]:
            operation["responses"] = {"200": {"description": "Success"}}
        if op.request_schema:
            operation["x-request-schema"] = op.request_schema
        if op.response_schema:
            operation["x-response-schema"] = op.response_schema
        item[method] = operation

    doc = {
        "openapi": "3.1.0",
        "info": {"title": ir.contract_id, "version": ir.schema_version},
        "paths": paths,
        "x-global-error-contract": ir.global_error_contract,
    }
    if ir.auth_scheme:
        doc["components"] = {"securitySchemes": {
            "default": {"type": "http", "scheme": ir.auth_scheme}
        }}
    return doc
