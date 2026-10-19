# Controlled TOR extraction v1

## Contract

The extractor is a deterministic segmentation and candidate-generation step. It
preserves the exact source SHA-256, source identifier, section, line range,
source excerpt, extraction version, and rule used. Candidate identifiers are
stable for the same source bytes and segmentation.

It does not infer tax rates, payroll formulas, API routes, authorization
policies, database fields, or acceptance results. Candidate records begin in
`pending_review`. Context paragraphs are recorded as ignored context with a
reason; unclassified list items are retained as unresolved candidates rather
than discarded.

## Human approval boundary

A `RequirementReview` must name an authorized reviewer and supply the chosen
requirement kind, priority, and acceptance criteria. Functional requirements
cannot enter the authoritative graph without acceptance criteria. Ambiguity
above the configured threshold requires a resolution reference. Unknown
candidate IDs are rejected.

The resulting RequirementGraph is validated by the canonical invariant
checker. Mapping then follows the existing path:

`TOR text → reviewed RequirementGraph → ReferenceDeterministicMapper → ISRRevision`

The ISR retains first-class requirement references and the revision provenance
lists the reviewed requirement IDs. No direct TOR-to-source-code path is
introduced.

## Limits

This v1 uses deterministic textual rules only. It is not a semantic
understanding system and does not claim complete extraction from arbitrary
PDFs, tables, scanned images, or complex legal language. Such input must first
be converted to faithful text with page/line provenance. Low-confidence or
unclassified candidates remain review work. This is deliberately preferable
to silently inventing requirements or treating generated text as authoritative.
