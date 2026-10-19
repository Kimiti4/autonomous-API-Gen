"""React/Vite frontend emitter consuming the canonical CompilationPlan."""
from __future__ import annotations

import html
import json
from typing import Any

from compiler.core.capabilities import (
    BackendCapabilities,
    SemanticFeature,
    UnsupportedSemanticsError,
    assert_frontend_plan_supported,
)
from compiler.core.plan import CompilationPlan
from compiler.core.repository import GeneratedRepository, build_repository


class ReactFrontendBackend:
    """Emit a runnable React/TypeScript app from explicit frontend ISR semantics."""

    name = "react-vite"
    language = "typescript"
    framework = "react-vite"
    version = "1.0.0"
    supported_features = frozenset({
        SemanticFeature.FRONTEND_ROUTES,
        SemanticFeature.FRONTEND_INTERACTIONS,
        SemanticFeature.API_CONTRACTS,
    })

    def compile(self, plan: CompilationPlan) -> GeneratedRepository:
        assert_frontend_plan_supported(
            plan,
            BackendCapabilities(
                backend_id=self.name,
                version=self.version,
                supported_features=self.supported_features,
            ),
        )
        routes = self._routes(plan)
        title = next((r["title"] for r in routes), plan.isr_id)
        files = {
            "package.json": json.dumps({
                "name": "isr-generated-frontend",
                "private": True,
                "version": "0.1.0",
                "type": "module",
                "scripts": {"build": "tsc --noEmit && vite build", "test": "vitest run"},
                "dependencies": {
                    "@vitejs/plugin-react": "^4.3.4",
                    "react": "^18.3.1",
                    "react-dom": "^18.3.1",
                    "vite": "^6.0.0",
                },
                "devDependencies": {
                    "@testing-library/jest-dom": "^6.6.3",
                    "@testing-library/react": "^16.1.0",
                    "@testing-library/user-event": "^14.5.2",
                    "@types/react": "^18.3.12",
                    "@types/react-dom": "^18.3.1",
                    "jsdom": "^25.0.1",
                    "typescript": "^5.7.2",
                    "vitest": "^2.1.8",
                },
            }, indent=2) + "\n",
            "index.html": self._index(title),
            "vite.config.ts": self._vite_config(),
            "tsconfig.json": self._tsconfig(),
            "src/main.tsx": self._main(),
            "src/style.css": self._style(),
            "src/App.tsx": self._app(routes),
            "src/App.test.tsx": self._tests(routes),
            "README.md": self._readme(plan, routes),
        }
        return build_repository(files)

    def _routes(self, plan: CompilationPlan) -> list[dict[str, Any]]:
        if not plan.frontend_routes:
            raise UnsupportedSemanticsError(
                "React generation requires explicit frontend_route ISR nodes"
            )
        routes: list[dict[str, Any]] = []
        for route in plan.frontend_routes:
            if route.behavior is None:
                raise UnsupportedSemanticsError(
                    f"Frontend route {route.id!r} has no typed route payload"
                )
            if route.behavior.requires_auth:
                raise UnsupportedSemanticsError(
                    f"Frontend route {route.id!r} requires an authentication flow not implemented by this backend"
                )
            api_operations = []
            for api in route.api_operations:
                if api.behavior is None:
                    raise UnsupportedSemanticsError(
                        f"Route {route.id!r} references API {api.id!r} without an explicit API contract"
                    )
                api_operations.append({
                    "id": api.id,
                    "operationId": api.behavior.operation_id,
                    "method": api.behavior.method,
                    "path": api.behavior.path,
                })
            interactions = []
            for interaction in route.interactions:
                if interaction.behavior is None:
                    raise UnsupportedSemanticsError(
                        f"Interaction {interaction.id!r} has no typed interaction payload"
                    )
                target = interaction.target_api_operation
                if interaction.behavior.action != "toggle":
                    if target is None or target.behavior is None:
                        raise UnsupportedSemanticsError(
                            f"Interaction {interaction.id!r} has no explicit target API contract"
                        )
                    api = target.behavior
                    interactions.append({
                        "id": interaction.id,
                        "label": interaction.behavior.label,
                        "action": interaction.behavior.action,
                        "successMessage": interaction.behavior.success_message,
                        "operationId": api.operation_id,
                        "method": api.method,
                        "path": api.path,
                        "fields": [field.model_dump(mode="json") for field in api.request_fields],
                    })
                else:
                    interactions.append({
                        "id": interaction.id,
                        "label": interaction.behavior.label,
                        "action": "toggle",
                        "successMessage": interaction.behavior.success_message,
                        "operationId": None,
                        "method": None,
                        "path": None,
                        "fields": [],
                    })
            routes.append({
                "id": route.id,
                "path": route.behavior.path,
                "title": route.behavior.title,
                "requiresAuth": route.behavior.requires_auth,
                "apiOperations": api_operations,
                "interactions": interactions,
            })
        return routes

    def _index(self, title: str) -> str:
        return (
            "<!doctype html>\n<html lang=\"en\">\n<head>\n"
            "  <meta charset=\"UTF-8\" />\n"
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n"
            f"  <title>{html.escape(title)}</title>\n"
            "</head>\n<body>\n<div id=\"root\"></div>\n"
            "<script type=\"module\" src=\"/src/main.tsx\"></script>\n"
            "</body>\n</html>\n"
        )

    def _vite_config(self) -> str:
        return (
            "import { defineConfig } from 'vitest/config';\n"
            "import react from '@vitejs/plugin-react';\n\n"
            "export default defineConfig({ plugins: [react()], test: { environment: 'jsdom' } });\n"
        )

    def _tsconfig(self) -> str:
        return json.dumps({
            "compilerOptions": {
                "target": "ES2022",
                "lib": ["ES2022", "DOM", "DOM.Iterable"],
                "skipLibCheck": True,
                "esModuleInterop": True,
                "module": "ESNext",
                "moduleResolution": "Bundler",
                "resolveJsonModule": True,
                "isolatedModules": True,
                "noEmit": True,
                "jsx": "react-jsx",
                "strict": True,
                "types": ["vite/client", "vitest/globals"],
            },
            "include": ["src", "vite.config.ts"],
        }, indent=2) + "\n"

    def _main(self) -> str:
        return (
            "import React from 'react';\n"
            "import { createRoot } from 'react-dom/client';\n"
            "import App from './App';\n"
            "import './style.css';\n\n"
            "createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);\n"
        )

    def _style(self) -> str:
        return (
            ":root { font-family: system-ui, sans-serif; color: #18212f; background: #f6f8fb; }\n"
            "body { margin: 0; }\n"
            "main { max-width: 960px; margin: 0 auto; padding: 2rem; }\n"
            "nav { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 2rem; }\n"
            "section { background: white; border: 1px solid #dce3ec; border-radius: .75rem; padding: 1rem; margin: 1rem 0; }\n"
            "form { display: grid; gap: .75rem; max-width: 32rem; margin: 1rem 0; }\n"
            "label { display: grid; gap: .25rem; }\n"
            "input, button { font: inherit; padding: .6rem; }\n"
            "button, a { cursor: pointer; }\n"
            "pre { overflow: auto; white-space: pre-wrap; }\n"
        )

    def _app(self, routes: list[dict[str, Any]]) -> str:
        return (
            "import { useState, type FormEvent } from 'react';\n\n"
            "type FieldSpec = { name: string; value_type: string; required: boolean; nullable: boolean };\n"
            "type ApiOperation = { id: string; operationId: string; method: string; path: string };\n"
            "type Interaction = { id: string; label: string; action: 'submit' | 'refresh' | 'delete' | 'toggle'; "
            "successMessage: string | null; operationId: string | null; method: string | null; path: string | null; fields: FieldSpec[] };\n"
            "type RouteSpec = { id: string; path: string; title: string; requiresAuth: boolean; apiOperations: ApiOperation[]; interactions: Interaction[] };\n"
            f"const ROUTES: RouteSpec[] = {json.dumps(routes, ensure_ascii=False, indent=2)};\n\n"
            "function toPayload(values: Record<string, string>, fields: FieldSpec[]): Record<string, unknown> {\n"
            "  const payload: Record<string, unknown> = {};\n"
            "  for (const field of fields) {\n"
            "    if (!(field.name in values)) continue;\n"
            "    const value = values[field.name];\n"
            "    if (field.value_type === 'integer') payload[field.name] = Number.parseInt(value, 10);\n"
            "    else if (field.value_type === 'boolean') payload[field.name] = value === 'true';\n"
            "    else payload[field.name] = value;\n"
            "  }\n"
            "  return payload;\n"
            "}\n\n"
            "function InteractionView({ item }: { item: Interaction }) {\n"
            "  const [values, setValues] = useState<Record<string, string>>({});\n"
            "  const [message, setMessage] = useState('');\n"
            "  const [result, setResult] = useState('');\n"
            "  async function invoke(event: FormEvent<HTMLFormElement>) {\n"
            "    event.preventDefault();\n"
            "    if (item.action === 'toggle') { setMessage(message ? '' : (item.successMessage ?? 'Toggled')); return; }\n"
            "    if (!item.method || !item.path) { setMessage('Missing API contract'); return; }\n"
            "    const path = item.path.replace(/\\{([^}]+)\\}/g, (_match, key: string) => encodeURIComponent(values[key] ?? ''));\n"
            "    const payload = toPayload(values, item.fields);\n"
            "    const hasBody = ['POST', 'PUT', 'PATCH'].includes(item.method);\n"
            "    const response = await fetch(path, { method: item.method, headers: hasBody ? { 'Content-Type': 'application/json' } : {}, body: hasBody ? JSON.stringify(payload) : undefined });\n"
            "    const text = await response.text();\n"
            "    setMessage(response.ok ? (item.successMessage ?? 'Request completed') : 'Request failed (' + response.status + ')');\n"
            "    setResult(text);\n"
            "  }\n"
            "  return <section aria-label={item.label}><h2>{item.label}</h2>\n"
            "    {item.action === 'toggle' ? <button type=\"button\" onClick={() => setMessage(message ? '' : (item.successMessage ?? 'Toggled'))}>{item.label}</button> : <form onSubmit={invoke}>\n"
            "      {item.fields.map((field) => <label key={field.name}>{field.name.replaceAll('_', ' ')}\n"
            "        <input aria-label={field.name} name={field.name} required={field.required} "
            "type={field.value_type === 'boolean' ? 'checkbox' : field.value_type === 'integer' || field.value_type === 'decimal' || field.value_type === 'money' ? 'number' : 'text'} "
            "step={field.value_type === 'decimal' || field.value_type === 'money' ? 'any' : undefined} "
            "checked={field.value_type === 'boolean' ? values[field.name] === 'true' : undefined} "
            "value={field.value_type === 'boolean' ? undefined : (values[field.name] ?? '')} "
            "onChange={(event) => setValues({ ...values, [field.name]: field.value_type === 'boolean' ? String(event.target.checked) : event.target.value })} />\n"
            "      </label>)}\n"
            "      <button type=\"submit\">{item.label}</button>\n"
            "    </form>}\n"
            "    {message && <p role=\"status\">{message}</p>}{result && <pre>{result}</pre>}\n"
            "  </section>;\n"
            "}\n\n"
            "export default function App() {\n"
            "  const route = ROUTES.find((item) => item.path === window.location.pathname) ?? ROUTES[0];\n"
            "  if (!route) return <main><h1>No frontend routes defined in ISR</h1></main>;\n"
            "  return <main><nav aria-label=\"Pages\">{ROUTES.map((item) => <a key={item.id} href={item.path}>{item.title}</a>)}</nav>\n"
            "    <h1>{route.title}</h1><p>Generated from the canonical ISR.</p>\n"
            "    {route.apiOperations.length > 0 && <section><h2>Available API operations</h2><ul>{route.apiOperations.map((api) => <li key={api.id}><code>{api.method} {api.path}</code></li>)}</ul></section>}\n"
            "    {route.interactions.map((item) => <InteractionView key={item.id} item={item} />)}\n"
            "  </main>;\n"
            "}\n"
        )

    def _tests(self, routes: list[dict[str, Any]]) -> str:
        route = routes[0]
        interaction = next((item for item in route["interactions"] if item["action"] != "toggle"), None)
        lines = [
            "import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';",
            "import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';",
            "import App from './App';",
            "",
            "describe('ISR-generated frontend', () => {",
            "  beforeEach(() => {",
            f"    window.history.pushState({}, '', {json.dumps(route['path'])});",
            "    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, status: 200, text: async () => '{\"status\":\"ok\"}' }) as unknown as typeof fetch;",
            "  });",
            "  afterEach(() => { cleanup(); vi.restoreAllMocks(); });",
            "",
            "  it('renders the ISR route title and interactions', () => {",
            "    render(<App />);",
            f"    expect(screen.getByRole('heading', {{ name: {json.dumps(route['title'])} }})).toBeTruthy();",
        ]
        for item in route["interactions"]:
            lines.append(f"    expect(screen.getByRole('heading', {{ name: {json.dumps(item['label'])} }})).toBeTruthy();")
        lines.append("  });")
        if interaction is not None:
            fields = interaction["fields"]
            sample_values: dict[str, str] = {}
            for field in fields:
                kind = field["value_type"]
                sample_values[field["name"]] = (
                    "sample" if kind in ("string", "identifier", "date", "datetime")
                    else "2" if kind == "integer"
                    else "10.00" if kind in ("decimal", "money")
                    else "true"
                )
            expected_path = interaction["path"] or ""
            for key, value in sample_values.items():
                expected_path = expected_path.replace("{" + key + "}", value)
            lines += [
                "",
                "  it('calls the declared API when the interaction is submitted', async () => {",
                "    render(<App />);",
            ]
            for field in fields:
                if field["value_type"] == "boolean":
                    lines.append(f"    fireEvent.click(screen.getByLabelText({json.dumps(field['name'])}));")
                else:
                    lines.append(f"    fireEvent.change(screen.getByLabelText({json.dumps(field['name'])}), {{ target: {{ value: {json.dumps(sample_values[field['name']])} }} }});")
            lines += [
                f"    fireEvent.click(screen.getByRole('button', {{ name: {json.dumps(interaction['label'])} }}));",
                "    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalled());",
                f"    expect(globalThis.fetch).toHaveBeenCalledWith({json.dumps(expected_path)}, expect.objectContaining({{ method: {json.dumps(interaction['method'])} }}));",
                "    expect(screen.getByRole('status').textContent).toBeTruthy();",
                "  });",
            ]
        lines += ["});", ""]
        return "\n".join(lines)

    def _readme(self, plan: CompilationPlan, routes: list[dict[str, Any]]) -> str:
        lines = [
            f"# {plan.isr_id} generated React frontend",
            "",
            "Generated from explicit frontend route and interaction semantics in the canonical ISR.",
            "",
            "## Routes",
        ]
        for route in routes:
            lines.append(f"- {route['path']} — {route['title']}")
            for interaction in route["interactions"]:
                target = f" ({interaction['method']} {interaction['path']})" if interaction["path"] else ""
                lines.append(f"  - {interaction['label']}: {interaction['action']}{target}")
        lines += [
            "",
            "## Build and test",
            "",
            "    npm install",
            "    npm test",
            "    npm run build",
            "",
            "The compiler refuses routes without typed semantics, interactions without explicit API contracts, and auth-required routes until a real frontend authentication flow exists.",
            "",
        ]
        return "\n".join(lines)
