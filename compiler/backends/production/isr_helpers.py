"""
Shared helpers for extracting and normalizing ISR structures.
"""

from __future__ import annotations

import re
from typing import Any


def snake_case(value: Any) -> str:
    """Convert a value to snake_case."""

    text = str(value)

    text = re.sub(r"(?<!^)(?=[A-Z])", "_", text)
    text = text.replace("-", "_")
    text = text.replace(" ", "_")
    text = re.sub(r"[^0-9a-zA-Z_]", "", text)

    return text.lower()


def pascal_case(value: Any) -> str:
    """Convert a value to PascalCase."""

    parts = re.split(r"[^0-9a-zA-Z]+", str(value))

    return "".join(part.capitalize() for part in parts if part)


def kebab_case(value: Any) -> str:
    """Convert a value to kebab-case."""

    return snake_case(value).replace("_", "-")


def python_identifier(value: Any) -> str:
    """Convert a value into a safe Python identifier."""

    slug = snake_case(value)

    if not slug:
        return "generated"

    if slug[0].isdigit():
        slug = f"_{slug}"

    return slug


def project_name(isr: dict[str, Any]) -> str:
    """Return the ISR project name."""

    return str(isr.get("name", "Generated System"))


def project_slug(isr: dict[str, Any]) -> str:
    """Return a safe project slug."""

    return snake_case(isr.get("name", "system")) or "system"


def iter_services(isr: dict[str, Any]):
    """Yield service definitions from ISR."""

    domains = isr.get("domains", []) or []

    used_ids: set[str] = set()

    for domain in domains:
        if not isinstance(domain, dict):
            continue

        services = domain.get("services", []) or []

        for service in services:
            if isinstance(service, dict):
                name = service.get("name", "Service")
                key = f"service:{name}"

                if key not in used_ids:
                    used_ids.add(key)
                    yield service
            elif isinstance(service, str):
                key = f"service:{service}"

                if key not in used_ids:
                    used_ids.add(key)
                    yield {"name": service}

    services = isr.get("services", []) or []

    for service in services:
        if isinstance(service, dict):
            name = service.get("name", "Service")
            key = f"service:{name}"

            if key not in used_ids:
                used_ids.add(key)
                yield service
        elif isinstance(service, str):
            key = f"service:{service}"

            if key not in used_ids:
                used_ids.add(key)
                yield {"name": service}


def iter_data_models(isr: dict[str, Any]):
    """Yield data model definitions from ISR."""

    used_ids: set[str] = set()

    for model in isr.get("data_models", []) or []:
        name = python_identifier(model.get("name") if isinstance(model, dict) else model)
        key = f"model:{name}"

        if key not in used_ids:
            used_ids.add(key)
            yield model

    for service in iter_services(isr):
        for model in service.get("data_models", []) or []:
            name = python_identifier(model.get("name") if isinstance(model, dict) else model)
            key = f"model:{name}"

            if key not in used_ids:
                used_ids.add(key)
                yield model


def normalize_data_model(model: Any) -> dict[str, Any]:
    """Normalize a data model definition."""

    if isinstance(model, str):
        return {
            "name": model,
            "fields": {},
        }

    if isinstance(model, dict):
        return {
            "name": model.get("name", "UnnamedModel"),
            "fields": model.get("fields", {}) or {},
        }

    return {
        "name": "UnnamedModel",
        "fields": {},
    }


def normalize_api(api: Any) -> dict[str, Any]:
    """Normalize an API definition."""

    if isinstance(api, str):
        return {
            "name": api,
        }

    if isinstance(api, dict):
        return api

    return {
        "name": "unnamed",
    }


def infer_http_method(api_name: str) -> str:
    """Infer HTTP method from API operation name."""

    name = api_name.lower()

    if any(name.startswith(prefix) for prefix in ("get", "list", "find", "search")):
        return "GET"

    if any(name.startswith(prefix) for prefix in ("create", "add", "register", "post")):
        return "POST"

    if any(name.startswith(prefix) for prefix in ("update", "patch", "modify")):
        return "PUT"

    if any(name.startswith(prefix) for prefix in ("delete", "remove")):
        return "DELETE"

    return "POST"


def python_type(field_type: Any) -> str:
    """Map ISR field type to Python type."""

    mapping = {
        "string": "str",
        "str": "str",
        "text": "str",
        "uuid": "str",
        "integer": "int",
        "int": "int",
        "number": "float",
        "float": "float",
        "decimal": "float",
        "boolean": "bool",
        "bool": "bool",
        "datetime": "datetime",
        "date": "datetime",
        "time": "datetime",
        "object": "Dict[str, Any]",
        "dict": "Dict[str, Any]",
        "array": "List[Any]",
        "list": "List[Any]",
    }

    return mapping.get(str(field_type).lower(), "str")


def sql_type(field_type: Any) -> str:
    """Map ISR field type to PostgreSQL type."""

    mapping = {
        "string": "TEXT",
        "str": "TEXT",
        "text": "TEXT",
        "uuid": "UUID",
        "integer": "BIGINT",
        "int": "BIGINT",
        "number": "DOUBLE PRECISION",
        "float": "DOUBLE PRECISION",
        "decimal": "NUMERIC",
        "boolean": "BOOLEAN",
        "bool": "BOOLEAN",
        "datetime": "TIMESTAMPTZ",
        "date": "DATE",
        "time": "TIME",
        "object": "JSONB",
        "dict": "JSONB",
        "array": "JSONB",
        "list": "JSONB",
    }

    return mapping.get(str(field_type).lower(), "TEXT")


def openapi_type(field_type: Any) -> str:
    """Map ISR field type to OpenAPI type."""

    mapping = {
        "string": "string",
        "str": "string",
        "text": "string",
        "uuid": "string",
        "integer": "integer",
        "int": "integer",
        "number": "number",
        "float": "number",
        "decimal": "number",
        "boolean": "boolean",
        "bool": "boolean",
        "datetime": "string",
        "date": "string",
        "time": "string",
        "object": "object",
        "dict": "object",
        "array": "array",
        "list": "array",
    }

    return mapping.get(str(field_type).lower(), "string")