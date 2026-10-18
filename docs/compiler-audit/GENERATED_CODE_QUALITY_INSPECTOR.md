# Generated Code Quality Inspector

## Purpose

The quality inspector is a deterministic, backend-neutral static evidence layer for generated repositories. It is intended to be reusable across frontend, API, backend, data, and infrastructure compiler outputs. It does not infer quality from the compiler's self-assessment and does not claim that a static score alone proves "senior-level" or production-ready software.

## Current checks

- Bind each report to a canonical SHA-256 hash of the exact file mapping.
- Reject missing or inconsistent hashes when a `GeneratedRepository` is supplied; optionally compare a compiler-declared hash for other compiler outputs.
- Reject unsafe/escaping artifact paths and case-insensitive path collisions.
- Reject empty source artifacts and Python syntax errors.
- Scan all artifacts (including configuration/workflow files) for known high-confidence credential patterns and private-key material.
- Flag unresolved implementation markers, including `NotImplementedError`.
- Flag non-behavioral `assert True` tests.
- Inspect Python AST for dynamic `eval`/`exec`, shell/process calls, bare exception handlers, silently swallowed exceptions, mutable default arguments, excessive function length, and high estimated cyclomatic complexity.
- Flag source lines longer than 120 characters as a maintainability warning.
- Report which source languages were inspected and which were not parsed.

## Gate semantics

- `ERROR` and `BLOCKER` findings fail the report.
- `WARNING` findings remain explicit and require policy decisions; they are never described as passed checks.
- Callers may set `require_complete_language_analysis=True` to fail closed when a source language has no registered parser.
- Findings are sorted deterministically by path, line, rule, and message.
- The report's `repository_hash` identifies the exact content inspected. If a later stage changes the files, it must run inspection again against the changed artifact set.

## Important limitations

This is an initial cross-language *common* check set, not a replacement for each language's compiler, formatter, type checker, linter, dependency audit, SAST/DAST, accessibility analyzer, or runtime tests. At present, Python receives AST-based checks; other languages are scanned for common artifact/path/secret/placeholder issues and are explicitly listed as unparsed. A strict complete-language gate therefore remains blocked for those languages until real parsers/analyzers are connected.

A quality report must not be interpreted as proof of ISR semantic correspondence, authorization correctness, data isolation, performance, accessibility, resilience, deployment success, or production readiness. Those require independent, requirement-bound checks in their own certification stages.

## Integration contract

The intended certification order is:

1. Generate candidate artifacts from an authoritative ISR snapshot.
2. Freeze the candidate file set and compute its canonical content hash.
3. Run this inspector on that exact candidate.
4. Block later certification stages on any blocking finding.
5. Run language-specific build, lint/type, security, contract, E2E, and runtime checks.
6. Re-bind all evidence to the same candidate hash; if an artifact changes, invalidate downstream evidence and rerun affected stages.
7. Preserve findings and analyzer coverage in the evidence ledger.

The inspector is domain-agnostic. Payroll is one proving case, not a special path.
