# ADR: Prompts as Compiled Artifacts (Context Graph, Token Budgeter, Prompt Compiler)

Status: Accepted (Cap-D, stage D4)

## Context
Intelligence tasks across Cap-B assemble prompts by string construction
inside application code. That makes them irreproducible, unbudgeted, and
unauditable — the opposite of the platform's compiler philosophy, where
every artifact is a deterministic compilation of a canonical representation.

## Decision
1. **ContextGraph** is the canonical prompt-input representation (domain
   model): typed `ContextNode` entries, prioritized `MUST`/`SHOULD`/`COULD`,
content-hashed and ordered. Nodes have no identity outside the graph; their
   provenance is the graph + node id.
2. **TokenBudget** partitions the context window into `output_reserve`,
   `instruction_reserve`, `schema_reserve`, and a `context_pool`. Budget
   *selection* is pure and deterministic: `MUST` nodes fit whole or
   compilation fails; `SHOULD` then `COULD` nodes degrade in declared order
   and every drop is recorded — budget pressure is evolutionary evidence.
3. **Tokenization** goes through the `TokenEstimator` port; deterministic
   reference estimators ship in-core; model-specific tokenizers are deploy-
   ment plugins that never touch the compiler.
4. **PromptCompiler** weaves the instruction block, the selected context
   nodes, and the output schema into a `CompiledPrompt` carrying full
   provenance: graph hash, prompt hash, included/dropped node ids,
   per-section token counts, and the tokenizer identity.
5. **Evidence** enters through the `EvidenceSource` port. `StaticEvidenceSource`
   serves committed fragment libraries now; the Constitutional Knowledge Base
   (Phase 23) will implement the same port later.
6. `LanguageModelBridge` gains `complete_with_context` additively. The graph's
   `task_kind` is authoritative; the incoming request supplies model/task/
   schema/decoding identity only, and its `prompt` field is replaced by the
   compiled artifact. `complete_structured` and all Cap-B flows are unchanged.

## Alternatives considered
- *Vendor tokenizers in-core*: rejected — technology coupling (Constitution §2).
- *Silent truncation of over-budget MUST context*: rejected — this is
  fabrication by omission; loud failure is honest.
- *LLM-driven context selection*: rejected for now — nondeterministic and
  unauditable. A learned selector is a future audited evolution stage, not
  the starting point (mirrors the AIR router's own stance).
- *Reclaiming unused reserve slack into the context pool*: rejected for v1 —
  conservative budgeting is safe and visible; slack reclamation is future
  work observable by D5.

## Trade-offs
- Reserve slack is deliberately wasted for safety and budget transparency.
- Char-ratio estimation approximates real tokenizers; the `TokenEstimator`
  port closes the gap at deployment without core changes.
- Nodes fit whole or drop; per-node opt-in truncation is future work.

## Risks
- On small-budget targets, chronic `SHOULD` drops are visible in
  `dropped_node_ids` and will be surfaced by D5's autonomy audit as a
  model-capability signal, not a silent defect.

## Future evolution
- CKB-backed `EvidenceSource` (Phase 23).
- Learned context selection as an audited evolution stage (Phase 38).
- Per-node truncation policies with explicit opt-in.
- Compiled prompts recorded in the evidence ledger alongside `ModelCallRecord`s.
