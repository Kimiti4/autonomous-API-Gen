"""Deterministic OpenAPI 3.1 projection of the technology-neutral API IR."""
from __future__ import annotations
from .api_ir import ApiContractIR
from .schema_ir import SchemaIR


def _schema_ref(name: str) -> dict:
    return {"$ref": f"#/components/schemas/{name}"}


def _schema_definition(schema: SchemaIR) -> dict:
    if schema.kind != "object":
        return {"type": schema.kind}
    properties, required = {}, []
    for field in schema.fields:
        value = {"type": field.type}
        if field.format:
            value["format"] = field.format
        if field.type == "array":
            value["items"] = {"type": field.items_type}
        if field.nullable:
            value["type"] = [field.type, "null"]
        properties[field.name] = value
        if field.required:
            required.append(field.name)
    result = {"type": "object", "properties": properties}
    if required:
        result["required"] = required
    return result


def to_openapi(ir: ApiContractIR) -> dict:
    paths = {}
    for op in sorted(ir.operations, key=lambda x: (x.path, x.method.upper(), x.operation_id)):
        method = op.method.lower()
        item = paths.setdefault(op.path, {})
        responses = {str(e.status): {"description": e.code, "x-error-code": e.code, "x-retryable": e.retryable}
                     for e in op.errors}
        if not responses:
            responses = {"200": {"description": "Success"}}
        operation = {
            "operationId": op.operation_id, "responses": responses,
            "x-authorization-policy": op.authorization_policy,
            "x-request-schema": op.request_schema,
            "x-response-schema": op.response_schema,
            "x-idempotency-required": op.idempotency_required,
            "x-paginated": op.paginated, "x-api-version": op.version,
        }
        if op.request_schema:
            operation["requestBody"] = {"required": True, "content": {"application/json": {"schema": _schema_ref(op.request_schema)}}}
        if op.response_schema:
            success = operation["responses"].setdefault("200", {"description": "Success"})
            success["content"] = {"application/json": {"schema": _schema_ref(op.response_schema)}}
        item[method] = operation
    doc = {
        "openapi": "3.1.0",
        "info": {"title": ir.contract_id, "version": ir.schema_version},
        "paths": paths,
        "components": {"schemas": {s.name: _schema_definition(s) for s in ir.schemas}},
        "x-global-error-contract": ir.global_error_contract,
    }
    if ir.auth_scheme:
        doc["components"]["securitySchemes"] = {"default": {"type": "http", "scheme": ir.auth_scheme}}
    return doc
