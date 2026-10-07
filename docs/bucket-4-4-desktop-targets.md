# Bucket 4.4 — Windows and macOS software targets

Bucket 4.4 adds explicit Windows and macOS desktop targets within the already
authorized ESAP project scope.

## Target boundary

- Windows: installer and portable artifacts.
- macOS: application bundle and DMG artifacts.

A selected target is authoritative for the desktop build scope. A Windows
request cannot silently emit macOS artifacts, and vice versa.

## Governance

Target selection does not authorize code signing, notarization, production
release, distribution, marketplace publication, credentials, or certificates.
Release remains explicitly human-authorized. Marketplace capability remains
outside this bucket.

Bucket 4.4 does not mutate ISR or create new requirements from implementation
findings.

## Completion

Build only the requested desktop target, verify its artifact and required
behavior, certify the authorized scope, and stop. Cross-platform support is
not silently inferred.

This bucket establishes the platform contract. Platform-specific builders,
packaging toolchains, signing/notarization adapters, and deployment adapters
remain explicit capabilities rather than hidden side effects.
