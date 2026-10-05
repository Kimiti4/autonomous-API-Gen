"""CAP-003 Node/Express backend target compiler."""
from __future__ import annotations

import json
import re

from .backend_compiler import BackendCompilation, GeneratedArtifact
from .backend_ir import BackendProjectIR, validate_backend_ir


def _name(value: str) -> str:
    x = re.sub(r"[^A-Za-z0-9_]", "_", value).strip("_").lower()
    return x or "operation"


class ExpressBackendCompiler:
    target = "node-express"

    def compile(self, ir: BackendProjectIR) -> BackendCompilation:
        findings = validate_backend_ir(ir)
        if findings:
            return BackendCompilation(self.target, ir.schema_version, (), findings)

        routes = "\n".join(
            f'''router.{e.method.lower()}("{e.path}", async (req, res) => {{
  const result = await service.{_name(e.operation)}(req.body);
  res.json(result);
}});'''
            for e in ir.endpoints
        )
        main = (
            "const express = require('express');\n"
            "const app = express();\n"
            "app.use(express.json());\n"
            "const router = express.Router();\n\n"
            + routes
            + "\napp.get('/health', (_req, res) => res.json({status: 'ok'}));\n"
            + "app.use(router);\n\n"
            + "module.exports = app;\n"
        )
        service = "\n".join(
            f'''async function {_name(e.operation)}(payload) {{
  return repository.{_name(e.operation)}(payload);
}}'''
            for e in ir.endpoints
        ) or "module.exports = {};\n"
        service = (
            "const repository = require('./repository');\n\n"
            + service
            + "\nmodule.exports = {\n"
            + ",\n".join(f"  {_name(e.operation)}" for e in ir.endpoints)
            + "\n};\n"
        )
        repository = "\n".join(
            f'''async function {_name(e.operation)}(_payload) {{
  throw new Error('Repository operation not implemented');
}}'''
            for e in ir.endpoints
        ) or "const noop = async () => undefined;\n"
        repository += (
            "\nmodule.exports = {\n"
            + ",\n".join(f"  {_name(e.operation)}" for e in ir.endpoints)
            + "\n};\n"
        )
        package = json.dumps(
            {
                "private": True,
                "scripts": {"start": "node server.js", "test": "node --test"},
                "dependencies": {"express": "^5.1.0"},
            },
            indent=2,
            sort_keys=True,
        ) + "\n"
        server = "const app = require('./app');\napp.listen(process.env.PORT || 3000);\n"
        errors = (
            json.dumps(
                {"contract": ir.error_contract, "lifecycle": list(ir.lifecycle)},
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        artifacts = (
            GeneratedArtifact("app.js", main, "source"),
            GeneratedArtifact("service.js", service, "source"),
            GeneratedArtifact("repository.js", repository, "repository"),
            GeneratedArtifact("server.js", server, "source"),
            GeneratedArtifact("package.json", package, "dependency"),
            GeneratedArtifact("contracts/errors.json", errors, "contract"),
            GeneratedArtifact(
                "test/health.test.js",
                "const test = require('node:test');\n"
                "const assert = require('node:assert');\n"
                "test('health contract exists', () => assert.ok(true));\n",
                "test",
            ),
        )
        return BackendCompilation(self.target, ir.schema_version, artifacts, ())
