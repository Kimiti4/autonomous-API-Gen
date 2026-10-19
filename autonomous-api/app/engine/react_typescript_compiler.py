"""Buildable React/TypeScript compiler with executable, explicit action bindings."""
from __future__ import annotations

import json
import re

from .frontend_ir import FrontendProjectIR, validate_frontend_ir
from .frontend_registry import FrontendCompilation


def _component_name(value: str) -> str:
    parts = [part for part in re.split(r"[^A-Za-z0-9]+", value) if part]
    name = "".join(part[:1].upper() + part[1:] for part in parts) or "Screen"
    return f"Screen{name}" if name[0].isdigit() else name


def _artifact(path: str, content: str, kind: str = "source"):
    return type("Artifact", (), {"path": path, "content": content, "kind": kind})()


class ReactTypeScriptCompiler:
    target = "web-react-typescript"

    def compile(self, ir: FrontendProjectIR) -> FrontendCompilation:
        findings = validate_frontend_ir(ir)
        if findings:
            return FrontendCompilation(self.target, ir.schema_version, (), findings)

        components: list[str] = []
        routes: list[str] = []
        for screen in ir.screens:
            name = _component_name(screen.screen_id)
            actions = list(screen.actions)
            bindings = [
                {
                    "action_id": binding.action_id,
                    "api_operation_id": binding.api_operation_id,
                    "method": binding.method.upper(),
                    "path": binding.path,
                    "request_fields": list(binding.request_fields),
                    "authorization_policy": binding.authorization_policy,
                }
                for binding in screen.action_bindings
            ]
            component = """export function __NAME__() {
  const title = __TITLE__;
  const screenId = __SCREEN_ID__;
  const routePath = __ROUTE__;
  const actions = __ACTIONS__;
  const actionBindings = __BINDINGS__;
  const authorizationPolicy: string = __AUTH__;
  const dataContract = __DATA__;
  const accessibilityRequirements = __A11Y__;
  const [status, setStatus] = useState("Ready");
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const formFields = Array.from(new Set([
    ...actionBindings.flatMap((binding) => binding.request_fields),
    ...actionBindings.flatMap((binding) => Array.from(binding.path.matchAll(/\\{([^}]+)\\}/g), (match) => match[1])),
  ]));

  async function runAction(actionId: string) {
    const binding = actionBindings.find((item) => item.action_id === actionId);
    if (!binding) {
      setStatus(`Action requested: ${actionId} (no API binding configured)`);
      return;
    }
    let path = binding.path;
    for (const match of path.matchAll(/\\{([^}]+)\\}/g)) {
      const field = match[1];
      const value = formValues[field];
      if (!value) {
        setStatus(`Missing required path value: ${field}`);
        return;
      }
      path = path.replace(`{${field}}`, encodeURIComponent(value));
    }
    const method = binding.method.toUpperCase();
    const payload = Object.fromEntries(binding.request_fields.map((field) => [field, formValues[field] ?? ""]));
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL ?? ""}${path}`, {
        method,
        headers: method === "GET" || method === "DELETE" ? {} : { "Content-Type": "application/json" },
        body: method === "GET" || method === "DELETE" ? undefined : JSON.stringify(payload),
      });
      setStatus(response.ok ? `Request completed: ${response.status}` : `Request rejected: ${response.status}`);
    } catch {
      setStatus("Request failed: API unavailable");
    }
  }

  return (
    <main
      aria-label={title}
      data-screen-id={screenId}
      data-route={routePath}
      data-auth-policy={authorizationPolicy}
      data-data-contract={dataContract}
      data-actions={JSON.stringify(actions)}
      data-accessibility={JSON.stringify(accessibilityRequirements)}
    >
      <h1>{title}</h1>
      {authorizationPolicy !== "none" && <p>Access policy: {authorizationPolicy}. The API remains authoritative for access control.</p>}
      {formFields.length > 0 && (
        <form aria-label={`${title} action inputs`} onSubmit={(event) => event.preventDefault()}>
          {formFields.map((field) => (
            <label key={field}>
              {field}
              <input
                name={field}
                value={formValues[field] ?? ""}
                onChange={(event) => setFormValues((previous) => ({ ...previous, [field]: event.target.value }))}
              />
            </label>
          ))}
        </form>
      )}
      <section aria-label={`${title} actions`}>
        {actions.map((action) => (
          <button key={action} type="button" onClick={() => void runAction(action)}>{action}</button>
        ))}
      </section>
      <p role="status" aria-live="polite">{status}</p>
    </main>
  );
}"""
            replacements = {
                "__NAME__": name,
                "__TITLE__": json.dumps(screen.title),
                "__SCREEN_ID__": json.dumps(screen.screen_id),
                "__ROUTE__": json.dumps(screen.route),
                "__ACTIONS__": json.dumps(actions, ensure_ascii=False),
                "__BINDINGS__": json.dumps(bindings, ensure_ascii=False),
                "__AUTH__": json.dumps(screen.authorization_policy or "none", ensure_ascii=False),
                "__DATA__": json.dumps(screen.data_contract or "none", ensure_ascii=False),
                "__A11Y__": json.dumps(list(screen.accessibility_requirements), ensure_ascii=False),
            }
            for token, value in replacements.items():
                component = component.replace(token, value)
            components.append(component)
            routes.append(f"  {{ path: {json.dumps(screen.route)}, element: <{name} /> }},")

        app = (
            "import { useState } from 'react';\n\n"
            + "\n\n".join(components)
            + "\n\nexport const routes = [\n"
            + "\n".join(routes)
            + "\n] as const;\n\n"
            + "export default function App() {\n"
            + "  const current = routes.find((route) => route.path === window.location.pathname) ?? routes[0];\n"
            + "  return current ? current.element : <main><h1>No route configured</h1></main>;\n"
            + "}\n"
        )
        config_lines = []
        for key in ir.configuration_keys:
            env_key = key if key.startswith("VITE_") else f"VITE_{key}"
            config_lines.append(f"export const {key} = import.meta.env.{env_key} ?? '';")
        config = "\n".join(config_lines) + ("\n" if config_lines else "")
        contract = json.dumps(ir.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        index = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="color-scheme" content="light dark" />
    <title>Generated application</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""
        main = """import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

const root = document.getElementById('root');
if (!root) throw new Error('root element is missing');
createRoot(root).render(<StrictMode><App /></StrictMode>);
"""
        if ir.screens and ir.screens[0].actions:
            first_screen = ir.screens[0]
            first_action = first_screen.actions[0]
            first_binding = next(
                (binding for binding in first_screen.action_bindings if binding.action_id == first_action),
                None,
            )
            if first_binding is not None:
                unit_test = """import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from './App';

afterEach(() => vi.unstubAllGlobals());

describe('generated frontend interaction', () => {
  it('sends a bound action to its declared API path and reports the response', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    vi.stubGlobal('fetch', fetchMock);
    window.history.replaceState({}, '', '/');
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: __ACTION__ }));
    await waitFor(() => expect(screen.getByRole('status').textContent).toContain('Request completed: 200'));
    expect(fetchMock).toHaveBeenCalledWith(
      __PATH__,
      expect.objectContaining({ method: __METHOD__ }),
    );
  });
});
""".replace("__ACTION__", json.dumps(first_action)).replace("__PATH__", json.dumps(first_binding.path)).replace("__METHOD__", json.dumps(first_binding.method.upper()))
            else:
                unit_test = """import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import App from './App';

describe('generated frontend interaction', () => {
  it('does not claim success for an action without an API binding', () => {
    window.history.replaceState({}, '', '/');
    render(<App />);
    const button = screen.queryByRole('button');
    if (button) {
      fireEvent.click(button);
      expect(screen.getByRole('status').textContent).toContain('no API binding configured');
    }
  });
});
"""
        else:
            unit_test = """import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import App from './App';

describe('generated frontend', () => {
  it('renders an explicit empty-route state', () => {
    render(<App />);
    expect(screen.getByRole('heading', { name: 'No route configured' })).toBeTruthy();
  });
});
"""
        # Browser E2E tests are generated from the first declared screen/action.
        if ir.screens:
            first = ir.screens[0]
            first_action = first.actions[0] if first.actions else None
            e2e_lines = [
                "import { expect, test } from '@playwright/test';",
                "",
                "test('generated screen supports an accessible interaction', async ({ page }) => {",
                f"  await page.goto({json.dumps(first.route)});",
                f"  await expect(page.getByRole('heading', {{ name: {json.dumps(first.title)} }})).toBeVisible();",
            ]
            if first_action is not None:
                binding = next((item for item in first.action_bindings if item.action_id == first_action), None)
                if binding is not None:
                    e2e_lines += [
                        f"  await page.route('**{binding.path}', async (route) => route.fulfill({{ status: 200, contentType: 'application/json', body: '{{\"ok\":true}}' }}));",
                        f"  await page.getByRole('button', {{ name: {json.dumps(first_action)} }}).click();",
                        "  await expect(page.getByRole('status')).toContainText('Request completed: 200');",
                    ]
                else:
                    e2e_lines += [
                        f"  await page.getByRole('button', {{ name: {json.dumps(first_action)} }}).click();",
                        "  await expect(page.getByRole('status')).toContainText('no API binding configured');",
                    ]
            e2e_lines.append("});")
            e2e = "\n".join(e2e_lines) + "\n"
        else:
            e2e = "import { test } from '@playwright/test';\ntest('empty screen manifest', async () => {});\n"

        package = {
            "name": re.sub(r"[^a-z0-9-]+", "-", ir.application_id.lower()).strip("-") or "generated-frontend",
            "private": True,
            "version": "0.1.0",
            "type": "module",
            "scripts": {
                "dev": "vite --host 127.0.0.1",
                "build": "tsc --noEmit && vite build",
                "test": "vitest run",
                "test:e2e": "playwright test",
            },
            "dependencies": {"react": "^18.3.1", "react-dom": "^18.3.1"},
            "devDependencies": {
                "@playwright/test": "^1.55.0",
                "@testing-library/react": "^16.3.0",
                "@types/react": "^18.3.24",
                "@types/react-dom": "^18.3.7",
                "@vitejs/plugin-react": "^4.7.0",
                "jsdom": "^26.1.0",
                "typescript": "^5.9.2",
                "vite": "^6.3.5",
                "vitest": "^3.2.4",
            },
        }
        vite_config = """import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  test: { environment: 'jsdom', include: ['src/**/*.test.tsx'] },
  server: { host: '127.0.0.1' },
});
"""
        tsconfig = {
            "compilerOptions": {
                "target": "ES2022",
                "useDefineForClassFields": True,
                "lib": ["ES2022", "DOM", "DOM.Iterable"],
                "module": "ESNext",
                "skipLibCheck": True,
                "moduleResolution": "Bundler",
                "allowImportingTsExtensions": True,
                "resolveJsonModule": True,
                "isolatedModules": True,
                "noEmit": True,
                "jsx": "react-jsx",
                "strict": True,
                "types": ["vite/client", "vitest/globals"],
            },
            "include": ["src", "vite.config.ts"],
        }
        playwright_config = """import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  use: { baseURL: 'http://127.0.0.1:5173', headless: true },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
"""
        artifacts = (
            _artifact("src/App.tsx", app),
            _artifact("src/main.tsx", main),
            _artifact("src/config.ts", config),
            _artifact("src/contracts.json", contract, "contract"),
            _artifact("src/App.test.tsx", unit_test, "test"),
            _artifact("e2e/generated-app.spec.ts", e2e, "test"),
            _artifact("index.html", index, "config"),
            _artifact("package.json", json.dumps(package, indent=2, sort_keys=True) + "\n", "config"),
            _artifact("vite.config.ts", vite_config, "config"),
            _artifact("tsconfig.json", json.dumps(tsconfig, indent=2, sort_keys=True) + "\n", "config"),
            _artifact("playwright.config.ts", playwright_config, "config"),
        )
        return FrontendCompilation(self.target, ir.schema_version, artifacts, ())
