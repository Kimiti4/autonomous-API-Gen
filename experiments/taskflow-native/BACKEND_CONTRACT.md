# TaskFlow multi-backend compiler contract

The TaskFlow multi-backend trial is a compiler experiment, not a template-conversion experiment.

## Authority
The generated technology-neutral ISR is the only shared implementation authority. A compiler backend may lower that authority into its target language/runtime, but must not rewrite requirements to fit the target.

## Required target pair
1. Python + FastAPI — baseline target.
2. Elixir + Phoenix — materially different language/runtime target.

The second target must be generated independently from the same ISR. Its generator input must not include source code, architecture templates, tests, or runtime evidence produced for the first target.

## Backend boundary
A backend must expose explicit phases:
- capabilities — declare which ISR semantics the backend can lower.
- validate — reject unsupported or ambiguous semantics before generation.
- lower — translate semantic intent into target-specific implementation.
- materialize — write the generated artifact.
- verify — return target-specific verification results and evidence references.

Backend selection is data, not an instruction embedded in the ISR.

## Evidence
Every generated target must retain:
- source ISR hash;
- selected backend identity and version;
- live/replay execution mode;
- generation provenance;
- files produced;
- verification results;
- runtime observations;
- repairs, if any;
- final certification decision.

A replay/recorded provider may exercise compiler plumbing but cannot satisfy the live-generation requirement.

## Equivalence
The generated applications need not have the same source structure, framework patterns, database library, process model, or deployment packaging.

They must satisfy the same required semantic obligations, including:
- authentication;
- workspace tenancy;
- role authorization;
- project/task lifecycle;
- comments/activity history;
- search/filter;
- dashboard;
- audit/effect evidence;
- operational health;
- negative security cases;
- required-scope-only completion.

This is the actual test of whether ESAP is compiling semantic intent rather than copying a technology-specific solution.