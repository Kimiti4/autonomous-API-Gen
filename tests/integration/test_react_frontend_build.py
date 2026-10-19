"""Build and exercise an actual generated React app with npm/Vitest/Vite."""
from __future__ import annotations

import subprocess
from pathlib import Path

from compiler.backends.react_frontend import ReactFrontendBackend
from compiler.core.lowering import isr_to_plan
from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision


def _plan():
    nodes = {
        "api:create-record": Node(id="api:create-record", type=NodeType.API, properties={
            "label": "CreateRecord",
            "behavior": {
                "operation_id": "record.create",
                "method": "POST",
                "path": "/api/records",
                "request_fields": [{"name": "record_name", "value_type": "string"}],
                "response_fields": [{"name": "id", "value_type": "identifier"}],
            },
        }),
        "frontend:records": Node(id="frontend:records", type=NodeType.FRONTEND_ROUTE, properties={
            "label": "RecordsPage",
            "behavior": {"path": "/records", "title": "Records", "requires_auth": False},
        }),
        "interaction:create-record": Node(id="interaction:create-record", type=NodeType.FRONTEND_INTERACTION, properties={
            "label": "Create record",
            "behavior": {"label": "Create record", "action": "submit", "success_message": "Record created"},
        }),
    }
    edges = {
        "route-api": Edge(id="route-api", type=EdgeType.ROUTES_TO, source_id="frontend:records", target_id="api:create-record"),
        "route-interaction": Edge(id="route-interaction", type=EdgeType.CONTAINS, source_id="frontend:records", target_id="interaction:create-record"),
        "interaction-api": Edge(id="interaction-api", type=EdgeType.INVOKES, source_id="interaction:create-record", target_id="api:create-record"),
    }
    revision = ISRRevision.create(
        "react-build-smoke",
        "rev-1",
        "1.0",
        ISRGraph(nodes=nodes, edges=edges),
        Provenance(created_by="react-build-smoke", created_at="2025-01-01T00:00:00Z"),
    )
    return isr_to_plan(revision)


def test_generated_react_app_passes_vitest_and_production_build(tmp_path: Path):
    repo = ReactFrontendBackend().compile(_plan())
    for relative_path, content in repo.files.items():
        destination = tmp_path / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")

    subprocess.run(
        ["npm", "install", "--no-audit", "--no-fund"],
        cwd=tmp_path,
        check=True,
        timeout=600,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["npm", "test"],
        cwd=tmp_path,
        check=True,
        timeout=180,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["npm", "run", "build"],
        cwd=tmp_path,
        check=True,
        timeout=180,
        capture_output=True,
        text=True,
    )
    assert (tmp_path / "dist" / "index.html").is_file()
