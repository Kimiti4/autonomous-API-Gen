"""Minimal React/TypeScript frontend compiler target."""
from __future__ import annotations
import re
from .frontend_ir import FrontendProjectIR, validate_frontend_ir
from .frontend_registry import FrontendCompilation


def _safe(v: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", v).strip("_") or "screen"


class ReactTypeScriptCompiler:
    target = "web-react-typescript"

    def compile(self, ir: FrontendProjectIR) -> FrontendCompilation:
        findings = validate_frontend_ir(ir)
        if findings:
            return FrontendCompilation(self.target, ir.schema_version, (), findings)
        routes = []
        screens = []
        for s in ir.screens:
            name = "".join(p.capitalize() for p in re.split(r"[^A-Za-z0-9]+", s.screen_id))
            name = name or "Screen"
            routes.append(f'  {{ path: "{s.route}", element: <{name} /> }},')
            auth = s.authorization_policy or "none"
            data = s.data_contract or "none"
            actions = ", ".join(repr(a) for a in s.actions)
            a11y = ", ".join(repr(a) for a in s.accessibility_requirements)
            screens.append(
                f'export function {name}() {{\n'
                f'  return <main aria-label="{s.title}" data-auth-policy="{auth}" '
                f'data-data-contract="{data}" data-actions={{{actions!r}}} '
                f'data-accessibility={{{a11y!r}}}><h1>{s.title}</h1></main>;\n}}'
            )
        app = (
            "import React from 'react';\n"
            + "\n".join(screens)
            + "\n\nexport const routes = [\n"
            + "\n".join(routes)
            + "\n];\n"
        )
        return FrontendCompilation(
            self.target, ir.schema_version,
            tuple(type("Artifact", (), {"path": p, "content": c, "kind": k})()
                  for p, c, k in (
                      ("src/App.tsx", app, "source"),
                      ("src/contracts.json", str(ir.to_dict()), "contract"),
                  )),
            (),
        )
