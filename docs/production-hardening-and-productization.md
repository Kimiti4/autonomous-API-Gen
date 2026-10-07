# Production Hardening, Integration and Productization

## End-to-end execution boundary

The governed pipeline now has an explicit executable lifecycle:

request -> ISR -> scope/mode -> architecture -> implementation -> bounded execution -> verification -> evidence -> certification -> completion/stop.

Each stage must return an authoritative, content-addressed artifact. Verification, evidence and certification stages must carry evidence references. The final closure gate then requires all authoritative obligations, complete verification evidence, deployment readiness where required, and no blocking findings.

The pipeline validates the existing work-capability and mode/surface controls before any stage runs. It does not invent requirements and advisory findings cannot extend scope.

## Windows and macOS production release

Desktop build/package execution remains bounded and target-specific. A separate release-readiness boundary now distinguishes build/verification from consequential release actions:

- signing
- macOS notarization
- distribution

Those actions are never implied by a successful build. If required, they need explicit human authorization bound to the exact target and artifact digest.

## Marketplace/productization

A marketplace product can be prepared only from a completed governed pipeline. Productization binds:

- pipeline digest
- closure/certification digest
- artifact digest
- evidence digest
- documentation digest

A certified product becomes listable only with explicit human listing authorization. A listed product can become sold only with a separate explicit human sale authorization. Authorization is bound to the exact product and evidence digest.

ESAP therefore may autonomously design/build/test/verify/certify and prepare a product, but it cannot autonomously decide to publish or sell it.

## Production-readiness boundary

Production readiness means the system refuses unsupported claims. It does not claim signing, notarization, distribution, payments, or marketplace authority unless the corresponding governed capability and evidence exist.
