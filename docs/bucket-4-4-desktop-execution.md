# Bucket 4.4 — Desktop Build Execution Contract

## Purpose

Bucket 4.4 now extends the Windows/macOS desktop target boundary into a governed
build-execution contract. The contract is platform-neutral: it does not select
Electron, Tauri, native SDKs, installers, signing tools, or any other framework.

## Contract

A desktop build request binds:

- workspace;
- Windows or macOS target;
- target-compatible artifact;
- build/verify/package phase;
- bounded command tuple;
- expected artifact path.

The request has a deterministic digest. Build evidence must bind to that exact
request digest, target, and artifact.

## Governance

- Cross-target artifacts are rejected.
- Missing identifiers, commands, or artifact paths fail closed.
- Build execution is not release publication.
- Signing, notarization, deployment, distribution, credentials, and marketplace
  publication are outside this contract.
- Human authorization remains required for desktop release.
- Runtime or build findings cannot mutate the ISR or create new requirements.
- Existing bounded execution and verification controls remain the authority for
  actually running commands.

## Platform verification

The focused workflow executes the contract tests on Linux, Windows, and macOS,
using Python 3.11 and 3.13. This verifies the governance layer across host
platforms without pretending that a generic CI runner is evidence of a
project-specific desktop application build.

## Completion rule

For an authorized desktop request:

1. select the target;
2. construct a target-compatible build request;
3. execute through the existing bounded execution/verification path;
4. bind evidence to the exact request;
5. certify the requested scope;
6. stop.

Actual framework/toolchain selection remains an implementation decision inside
the authorized project work; it must not be silently promoted into ISR.
