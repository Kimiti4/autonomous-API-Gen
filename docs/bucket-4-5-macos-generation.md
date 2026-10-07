# Bucket 4.5 — macOS Software Generation

Bucket 4.5 adds governed macOS generation on top of the desktop target and build contracts from Bucket 4.4.

## Scope
A macOS generation request must explicitly target macOS, use a macOS-compatible artifact (.app or DMG), execute on a macOS host, and bind the generated result to the exact authorized request.

The project-specific build command remains part of authorized work. ESAP does not silently select a desktop framework or packaging toolchain.

## Governance
- Windows targets cannot enter the macOS generation path.
- Non-macOS hosts are rejected.
- Missing or mismatched result evidence fails closed.
- Generation does not grant signing, notarization, deployment, distribution, or marketplace authority.
- Implementation findings cannot mutate ISR or create requirements.
- Existing bounded execution and verification controls remain authoritative.

## Verification
The focused gate runs the macOS generation contract on macOS runners with Python 3.11 and 3.13.

## Completion
Select macOS explicitly, create the target-compatible build request, execute through bounded controls, verify the generated artifact and evidence, certify the authorized scope, then stop.
