# ADR-010 — Identity, Authentication, and MFA

## Status

Proposed (pending certification)

## Context

The platform requires a secure identity boundary that never enters the ISR or Evolution Engine. Every autonomous action must be attributable to an authenticated principal with least-privilege grants, and the audit trail must project into the v1.1 evidence format for accountability.

## Decision

Implement a standalone `identity/` package with:

- **Core types:** `Principal`, `AutonomousActionRecord`
- **Ports:** `UserStore`, `SessionStore`, `TokenVerifier`, `FactorVerifier`
- **Auth mechanisms:** email/password (PBKDF2-SHA256), TOTP MFA, recovery codes, session manager
- **Federation plugin seams:** GitHub OAuth/OIDC, WebAuthn, OIDC JWKS
- **Capabilities:** `Capability` enum, `CapabilityGrant`, `AuthorizationPort`, `AuthorizationService`
- **Evidence:** `ActionEvidence` projection from `AutonomousActionRecord` to v1.1 format
- **Reference adapters:** in-memory stores, PBKDF2 hasher, TOTP generator

### Independence constraint

The `identity/` package must **never** import from `isr/`, `evolution/`, or `genesis/`. Identity is infrastructure/security, not domain. This is enforced by a static scan gate (I7).

## Consequences

- Every autonomous action carries an `AutonomousActionRecord` that projects into v1.1 evidence.
- The ISR and Evolution Engine remain identity-free; no authentication data leaks into domain models.
- Federation (GitHub, OIDC, WebAuthn) is fully pluggable via protocol seams.
- The `IdentityStack` composition root wires reference adapters for tests and gate verification.

## Gate suite (I0–I9)

| Gate | Description |
|------|-------------|
| I0 | Inventory — all manifest artifacts present |
| I1 | Email register + login functional |
| I2 | Independence leak — identity does not import domain packages |
| I3 | MFA step-up cycle — enroll → confirm → login triggers challenge → complete_mfa → session |
| I4 | Least privilege — grants scoped; unauthorized principal denied; scope mismatch denied |
| I5 | Action → v1.1 evidence — AutonomousActionRecord produces ActionEvidence with 64-char hash |
| I6 | Session rotation + revocation — old session invalid after rotation; revoked session invalid |
| I7 | Independence — static scan confirms no ISR/evolution/genesis imports |
| I8 | Password hashing — PBKDF2-SHA256 with per-user salt; correct/incorrect verification |
| I9 | Recovery codes — single-use: first use succeeds, second use fails |
