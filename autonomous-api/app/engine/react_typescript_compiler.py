"""Contract-complete React/TypeScript frontend compiler."""
from __future__ import annotations
import json
import re
from .frontend_ir import FrontendProjectIR, validate_frontend_ir
from .frontend_registry import FrontendCompilation


def _component_name(value: str) -> str:
    parts = [p for p in re.split(r"[^A-Za-z0-9]+", value) if p]
    return "".join(p[:1].upper() + p[1:] for p in parts) or "Screen"


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
            auth = screen.authorization_policy or "none"
            data = screen.data_contract or "none"
            actions = list(screen.actions)
            a11y = list(screen.accessibility_requirements)
            components.append(
                f"""export function {name}() {{
  const actions = {json.dumps(actions)};
  const accessibilityRequirements = {json.dumps(a11y)};
  const authorizationPolicy = {json.dumps(auth)};
  const dataContract = {json.dumps(data)};
  return (
    <main
      aria-label={json.dumps(screen.title)}
      data-screen-id={json.dumps(screen.screen_id)}
      data-auth-policy={authorizationPolicy}
      data-data-contract={dataContract}
      data-actions={JSON.stringify(actions)}
      data-accessibility={JSON.stringify(accessibilityRequirements)}
    >
      <h1>{screen.title}</h1>
    </main>
  );
}}"""
            )
            routes.append(
                f"  {{ path: {json.dumps(screen.route)}, element: <{name} /> }},"
            )

        app = (
            "import React from 'react';\n\n"
            + "\n\n".join(components)
            + "\n\nexport const routes = [\n"
            + "\n".join(routes)
            + "\n];\n"
        )
        config = "\n".join(
            f"export const {key} = import.meta.env.{key};"
            for key in ir.configuration_keys
        ) + ("\n" if ir.configuration_keys else "")
        contract = json.dumps(
            {
                "schema_version": ir.schema_version,
                "application_id": ir.application_id,
                "api_contract_version": ir.api_contract_version,
                "screens": [
                    {
                        "screen_id": s.screen_id,
                        "route": s.route,
                        "title": s.title,
                        "data_contract": s.data_contract,
                        "authorization_policy": s.authorization_policy,
                        "actions": list(s.actions),
                        "accessibility_requirements": list(s.accessibility_requirements),
                    }
                    for s in ir.screens
                ],
                "platform_requirements": list(ir.platform_requirements),
                "configuration_keys": list(ir.configuration_keys),
            },
            indent=2,
            sort_keys=True,
        ) + "\n"
        artifacts = tuple(
            type("Artifact", (), {"path": path, "content": body, "kind": kind})()
            for path, body, kind in (
                ("src/App.tsx", app, "source"),
                ("src/config.ts", config, "source"),
                ("src/contracts.json", contract, "contract"),
            )
        )
        return FrontendCompilation(self.target, ir.schema_version, artifacts, ())
