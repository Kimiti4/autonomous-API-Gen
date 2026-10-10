# Provider-free TaskFlow requirement analysis

This is the first deterministic intake/traceability slice for ESAP's provider-free path. It uses only the Python standard library. It does not invoke an LLM, call a model endpoint, or make network requests.

From the TaskFlow trial directory, run:

```bash
python -m provider_free.cli --acceptance ../../golden-projects/taskflow/ACCEPTANCE.json
```

To persist the analysis report:

```bash
python -m provider_free.cli \
  --acceptance ../../golden-projects/taskflow/ACCEPTANCE.json \
  --output out/provider-free-analysis.json
```

When running in a snapshot-based trial, pass the snapshotted ACCEPTANCE.json path, not the mutable source path.

## Evidence semantics

- Each requirement receives a stable identifier and a reference to its source.
- The canonical contract digest is computed from deterministic JSON serialization.
- Required capabilities are UNSUPPORTED unless a callable provider-free compiler handler is registered in the analysis API.
- Required quality gates and negative cases are UNKNOWN until executed and supported by evidence.
- The report always states `certified: false`: requirement analysis is not code generation, testing, or certification.
- A handler registration means only that a handler exists; it does not prove that the resulting capability works.

This slice intentionally does not generate TaskFlow yet. The next implementation step is to connect real, capability-declared compiler handlers and emit artifact-level traceability, followed by independent build/API/UI/runtime/security/persistence tests.
