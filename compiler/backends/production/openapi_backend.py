"""
OpenAPI compiler backend.

Compiles ISR APIs and data models into an OpenAPI 3.1 contract.
"""

from __future__ import annotations

from ...models import (
    BackendCapabilities,
    BackendManifest,
    CompilationContext,
    CompilationOutput,
)
from ...sdk.artifacts import CompilationOutputBuilder
from ...sdk.base import CompilerBackendBase
from .isr_helpers import (
    infer_http_method,
    iter_data_models,
    iter_services,
    normalize_api,
    normalize_data_model,
    openapi_type,
    project_name,
    project_slug,
    python_identifier,
    snake_case,
)


class OpenAPIBackend(CompilerBackendBase):
    """Compiles ISR into OpenAPI artifacts."""

    def __init__(self) -> None:
        self.manifest = BackendManifest(
            backend_id="openapi.spec",
            name="OpenAPI Specification Backend",
            version="0.1.0",
            description="Compiles ISR into OpenAPI contracts.",
            capabilities=BackendCapabilities(
                supported_targets=["contract"],
                languages=["technology-neutral"],
                frameworks=["OpenAPI"],
                artifact_types=["openapi", "json", "markdown"],
                deployment_targets=["documentation"],
                maturity="production",
            ),
            entrypoint="compiler.backends.production.openapi_backend:OpenAPIBackend",
        )
        self.config = {}

    def compile(self, context: CompilationContext) -> CompilationOutput:
        isr = context.isr

        builder = CompilationOutputBuilder()

        openapi = {
            "openapi": "3.1.0",
            "info": {
                "title": project_name(isr),
                "version": str(isr.get("version", "0.1.0")),
                "description": (
                    "OpenAPI contract compiled from the Intermediate Software "
                    "Representation. The ISR remains the architectural source "
                    "of truth."
                ),
            },
            "paths": {},
            "components": {
                "schemas": {},
            },
        }

        # Data model schemas and generic model CRUD paths.
        seen_models: set[str] = set()

        for raw_model in iter_data_models(isr):
            model = normalize_data_model(raw_model)
            model_slug = python_identifier(model["name"])

            if not model_slug or model_slug in seen_models:
                continue

            seen_models.add(model_slug)

            properties = {
                "id": {
                    "type": "string",
                },
                "created_at": {
                    "type": "string",
                    "format": "date-time",
                },
            }

            fields = model.get("fields", {}) or {}

            for field_name, field_type in fields.items():
                field_slug = python_identifier(field_name)

                if not field_slug:
                    continue

                properties[field_slug] = {
                    "type": openapi_type(field_type),
                }

            openapi["components"]["schemas"][model_slug] = {
                "type": "object",
                "properties": properties,
            }

            base_path = f"/models/{model_slug}"
            item_path = f"/models/{model_slug}/{{item_id}}"

            openapi["paths"].setdefault(base_path, {})
            openapi["paths"].setdefault(item_path, {})

            openapi["paths"][base_path]["get"] = {
                "operationId": f"list_{model_slug}",
                "summary": f"List {model_slug}",
                "responses": {
                    "200": {
                        "description": f"A list of {model_slug}.",
                    }
                },
            }

            openapi["paths"][base_path]["post"] = {
                "operationId": f"create_{model_slug}",
                "summary": f"Create {model_slug}",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": f"#/components/schemas/{model_slug}"
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": f"Created {model_slug}.",
                    }
                },
            }

            openapi["paths"][item_path]["get"] = {
                "operationId": f"get_{model_slug}",
                "summary": f"Get {model_slug}",
                "parameters": [
                    {
                        "name": "item_id",
                        "in": "path",
                        "required": True,
                        "schema": {
                            "type": "string",
                        },
                    }
                ],
                "responses": {
                    "200": {
                        "description": f"A {model_slug}.",
                    }
                },
            }

            openapi["paths"][item_path]["put"] = {
                "operationId": f"update_{model_slug}",
                "summary": f"Update {model_slug}",
                "parameters": [
                    {
                        "name": "item_id",
                        "in": "path",
                        "required": True,
                        "schema": {
                            "type": "string",
                        },
                    }
                ],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": f"#/components/schemas/{model_slug}"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": f"Updated {model_slug}.",
                    }
                },
            }

            openapi["paths"][item_path]["delete"] = {
                "operationId": f"delete_{model_slug}",
                "summary": f"Delete {model_slug}",
                "parameters": [
                    {
                        "name": "item_id",
                        "in": "path",
                        "required": True,
                        "schema": {
                            "type": "string",
                        },
                    }
                ],
                "responses": {
                    "204": {
                        "description": f"Deleted {model_slug}.",
                    }
                },
            }

        # Service operation paths.
        for service in iter_services(isr):
            service_name = service.get("name", "Service")
            service_slug = python_identifier(service_name)

            if not service_slug:
                continue

            apis = service.get("apis", []) or []

            for raw_api in apis:
                api = normalize_api(raw_api)
                api_name = api.get("name", "operation")
                api_slug = python_identifier(api_name)

                if not api_slug:
                    continue

                method = infer_http_method(api_name).lower()

                path = f"/operations/{service_slug}/{api_slug}"

                operation = {
                    "operationId": f"{service_slug}_{api_slug}",
                    "summary": api_name,
                    "responses": {
                        "200": {
                            "description": f"{api_name} completed.",
                        }
                    },
                }

                if method in {"post", "put", "patch"}:
                    operation["requestBody"] = {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                }
                            }
                        }
                    }

                openapi["paths"].setdefault(path, {})
                openapi["paths"][path][method] = operation

        builder.add_json_artifact(
            path="openapi/openapi.json",
            payload=openapi,
        )

        builder.add_markdown_artifact(
            path="docs/openapi-summary.md",
            content="\n".join(
                [
                    "# OpenAPI Contract",
                    "",
                    f"Project: {project_name(isr)}",
                    f"Project slug: {project_slug(isr)}",
                    "",
                    "This contract was compiled from the ISR.",
                    "",
                ]
            ),
        )

        builder.add_log("Compiled OpenAPI contract from ISR.")

        return builder.build()