"""CAP-003 Node/Express backend target compiler.

Express-specific lowering lives entirely in this compiler. The source Backend
IR remains technology-neutral and immutable.
"""
from __future__ import annotations
import json
import re
from .backend_ir import BackendProjectIR, BackendEndpoint, validate_backend_ir
from .backend_compiler import BackendCompilation, GeneratedArtifact


def _name(value: str) -> str:
    x = re.sub(r"[^A-Za-z0-9_]", "_", value).strip("_").lower()
    return x or "operation"


class ExpressBackendCompiler:
    target = "node-express"

    def compile(self, ir: BackendProjectIR) -> BackendCompilation:
        findings = validate_backend_ir(ir)
        if findings:
            return BackendCompilation(self.target, ir.schema_version, (), findings)

        routes = "
".join(
            f'router.{e.method.lower()}("{e.path}", async (req, res) => {{
'
            f'  const result = await service.{_name(e.operation)}(req.body);
'
            "  res.json(result);
"
            "});
"
            for e in ir.endpoints
        )
        main = (
            "const express = require('express');
"
            "const app = express();
"
            "app.use(express.json());
"
            "const router = express.Router();

"
            f"{routes}
"
            "app.get('/health', (_req, res) => res.json({status: 'ok'}));
"
            "app.use(router);

"
            "module.exports = app;
"
        )
        service = "
".join(
            f"async function {_name(e.operation)}(payload) {{
"
            f"  return repository.{_name(e.operation)}(payload);
"
            "}
"
            for e in ir.endpoints
        ) or "module.exports = {};
"
        service = "const repository = require('./repository');

" + service + "
module.exports = {
" + ",
".join(f"  {_name(e.operation)}" for e in ir.endpoints) + "
};
"
        repository = "
".join(
            f"async function {_name(e.operation)}(_payload) {{
"
            "  throw new Error('Repository operation not implemented');
"
            "}
"
            for e in ir.endpoints
        ) or "const noop = async () => undefined;
"
        repository += "
module.exports = {
" + ",
".join(f"  {_name(e.operation)}" for e in ir.endpoints) + "
};
"
        package = json.dumps({
            "private": True,
            "scripts": {"start": "node server.js", "test": "node --test"},
            "dependencies": {"express": "^5.1.0"},
        }, indent=2, sort_keys=True) + "
"
        server = "const app = require('./app');
app.listen(process.env.PORT || 3000);
"
        errors = json.dumps({"contract": ir.error_contract, "lifecycle": list(ir.lifecycle)}, indent=2, sort_keys=True) + "
"
        artifacts = (
            GeneratedArtifact("app.js", main, "source"),
            GeneratedArtifact("service.js", service, "source"),
            GeneratedArtifact("repository.js", repository, "repository"),
            GeneratedArtifact("server.js", server, "source"),
            GeneratedArtifact("package.json", package, "dependency"),
            GeneratedArtifact("contracts/errors.json", errors, "contract"),
            GeneratedArtifact(
                "test/health.test.js",
                "const test = require('node:test');
const assert = require('node:assert');
"
                "test('health contract exists', () => assert.ok(true));
",
                "test",
            ),
        )
        return BackendCompilation(self.target, ir.schema_version, artifacts, ())
