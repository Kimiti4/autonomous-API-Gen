# TaskFlow Semantic Consumer Trace Audit

**Status:** SOURCE-INSPECTED / CONSUMER BINDING NOT PROVEN  
**Branch:** `review/taskflow-group-1-kimityr-clean`  
**Purpose:** Distinguish semantic resolution and value preservation from actual architectural/code-generation consumption. This is a static source audit, not a runtime test.

## Executive finding

The gate-enabled Cap-C intent path now refuses to continue without a resolver, a structurally valid resolution record, and an explicit projector. It checks all 15 required semantic paths, exact field coverage, equality between resolved values and projected values, and binding to the active requirement-graph ID/hash.

That is a meaningful fail-closed boundary, but **it does not yet prove that the values affect the typed architecture or emitted behavior**. The current projection envelope verifies that `SystemModel.extensions["taskflow_semantic_values"]` equals the projector's `projected_values`. This proves mirroring, not consumption. The generic derivation path shown below does not read that extension.

Therefore this audit leaves the semantic-consumption gate **BLOCKED** and TaskFlow generation **NOT AUTHORIZED**.

## Inspected source path

| Stage | Source | What the code establishes | What it does not establish |
|---|---|---|---|
| Initial resolution | `tiannara/application/intent/compiler.py`, `compile_full` | Builds the mandatory resolution record; uses a configured resolver if present; rejects a wrong return type or unresolved mandatory semantics. | That the chosen values are reviewer-trusted or domain-correct. |
| Structural contract | `tiannara/domain/models/taskflow_semantic_contract.py` | Rejects missing/placeholder fields, wrong top-level object/array types, and extra unreviewed keys. | Nested role/action correctness, actual workflow validity, timeout values, API schema correctness, or equivalent domain constraints. |
| Projection invocation | `tiannara/application/intent/compiler.py`, gate-enabled synthesis stage | Fails if no projector is configured; requires a `TaskFlowSemanticProjection`; checks exact mandatory path coverage, exact value equality, and requirement-graph ID/hash binding. | That values influence native fields or generated handlers rather than being carried as metadata. |
| Projection envelope | `tiannara/application/intent/schemas.py`, `TaskFlowSemanticProjection` | Requires nonblank path keys and exact equality between `projected_values` and `system_model.extensions["taskflow_semantic_values"]`. | No semantic interpretation or native-consumer check is performed by this model validator. |
| Cap-C compile | `tiannara/application/compiler/project_compiler.py`, `compile_intent` | Reads the typed `SystemModel`, derives generic compilation requirements, plans backends, executes and verifies their bundles. | The shown path does not directly inspect TaskFlow semantic extension values or prove every decision affects generated behavior. |
| Requirement derivation | `tiannara/application/compiler/derivation.py` | Selects broad artifact requirements based on model services, capabilities, APIs, data models, and system name. | It does not read `extensions["taskflow_semantic_values"]`; generic service/frontend/database requirements are not a TaskFlow domain model. |
| Constitutional pipeline | `constitutional_architecture/compiler/pipeline.py` | Provides a distinct multi-pass ISR compilation pipeline and backend registry. | A TaskFlow-specific canonical-input adapter, typed semantic parity, and consumption proof for all 15 paths are not established by the inspected code. |

## Required next implementation gate

Do not mark a field consumed merely because it is copied to an extension or included in a hash. For each semantic path:

1. **Typed destination:** define the field's reviewed, domain-specific type and validation rules. Keep unresolved policy choices blocked; do not invent defaults.
2. **Native consumer:** identify the exact architecture object, compiler pass, generated artifact, or runtime policy that reads the field.
3. **Causal test:** change one semantic value while holding the rest of the canonical input fixed; assert the intended architecture/artifact behavior changes, or that the input is rejected if the change violates a constraint.
4. **Omission/weakening test:** remove the field, weaken its rule, or substitute a contradictory value and prove compilation fails closed or the acceptance test fails. A test that only inspects extension equality is insufficient.
5. **Cross-compiler parity:** run the same field-level cases through both candidate adapters and compare normalized semantic obligations, not just output language or backend identity.
6. **Artifact traceability:** record requirement ID, semantic path, native consumer, generated artifact/hash, test ID/command, result, and evidence digest.
7. **Independent runtime proof:** test the generated application's externally observable behavior, including the canonical negative cases. Static or mocked evidence cannot certify runtime behavior.

## Machine-readable consumer trace

The field-level fail-closed register is maintained at [`docs/evidence/taskflow_review/SEMANTIC_CONSUMER_TRACE.v1.json`](taskflow_review/SEMANTIC_CONSUMER_TRACE.v1.json). It has one record per mandatory semantic ID. Until a native destination, source consumer, causal mutation/omission test, and runtime acceptance evidence exist, each record remains `BLOCKED`, tests remain `NOT_RUN`, and evidence references remain empty. The decision-ledger validator now checks this register and rejects any unsupported status upgrade.

## Minimum evidence table for future qualification

| Semantic path | Typed destination | Consumer source location | Causal mutation test | Omission/weakening test | Runtime acceptance IDs | Status |
|---|---|---|---|---|---|---|
| All 15 mandatory TaskFlow paths | Not yet proven | Not yet proven | Not run | Not run | Not run | **BLOCKED** |

This summary deliberately does not expand the single row into 15 rows with speculative consumers. Each consumer must be named only after source-level implementation exists and can be inspected.

## Current disposition

- Structural resolution gate: **PRESENT; CI VERIFIED at prior head, latest workflow must re-run after new changes**
- Projection field coverage/value-preservation checks: **PRESENT**
- Native typed consumer binding: **NOT PROVEN**
- Causal semantic mutation/omission tests: **NOT RUN**
- Candidate compiler A/B semantic parity: **BLOCKED**
- Live TaskFlow generation: **NOT AUTHORIZED / NOT RUN**
- TaskFlow runtime certification: **NOT CERTIFIED**
