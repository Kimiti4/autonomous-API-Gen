# Controlled TOR ingestion and requirement-to-ISR projection

## Contract

The ingestion path is deliberately staged:

1. Preserve the source text and calculate its SHA-256 digest.
2. Extract deterministic requirement candidates with stable IDs, source line references, proposed kind/priority, and ambiguity reasons.
3. Keep every candidate in NEEDS_REVIEW state.
4. Require an explicit human approval record, acceptance criteria, and a recorded ambiguity resolution when the ambiguity score exceeds the threshold.
5. Validate the resulting RequirementGraph against existing invariants.
6. Project only approved requirement references and their explicit dependency/conflict/refinement/ownership edges into the ISR.

The adapter does not invent capabilities or SATISFIES edges. A requirement reference records an obligation; it does not prove implementation.

## Limits

The extractor is a deterministic candidate finder, not a semantic authority. It uses section and obligation heuristics and can miss or misclassify requirements. Reviewers must correct proposed kind/priority, split compound obligations, add measurable acceptance criteria, resolve ambiguity, and approve the final graph. No prose is sent directly to a compiler.

## Provenance

Candidate IDs are content- and source-line-bound. The draft stores the source digest and source references; approved graph nodes preserve reviewer identity, approval reference, acceptance criteria, and source location. A changed source produces a new digest and candidate identities, invalidating old approval mappings.

## Payroll proving case

World Concern's payroll TOR can be ingested through this generic path. Kenya statutory rates, formulas, rounding rules, effective dates, and legal interpretations remain explicit requirements/data with authoritative sources and human sign-off. The extractor must not infer or certify PAYE/NSSF/SHIF calculations from prose alone.
