# Framework-Neutral Authorization Policy Engine

## Purpose

`tiannara.application.enterprise.authorization` now contains a real policy evaluator instead of a tenant-comparison-only stub. It is domain- and framework-neutral, so it can support generated applications without coupling the ISR to a web framework.

## Semantics

- **Default deny:** no matching allow policy means access is denied.
- **Deny overrides:** any matching explicit deny policy overrides matching allows.
- **RBAC:** policies can require one or more roles; at least one required role must be present.
- **ABAC:** policies can require predicates over subject, resource, and environment attributes, including nested attribute paths.
- **Missing attributes fail closed:** missing values do not satisfy equality, inequality, membership, or containment predicates.
- **Tenant isolation:** when explicitly required by a request, the resource must carry the same tenant identity as the request; missing or mismatched tenant identity denies access before policy evaluation.
- **Decision evidence:** results include the decision reason and sorted matching policy IDs.

## Trust boundary

The engine assumes the caller supplies authenticated subject identity, roles, resource attributes, and environment attributes from trusted sources. It does not authenticate users, load policies from storage, resolve roles from an identity provider, or generate framework-specific middleware. Those are separate integration responsibilities and must not be represented as implemented by this module.

## Certification requirements before production use

1. Derive policy obligations from authoritative ISR requirements, not from generated source code.
2. Generate and bind framework-specific enforcement points to each protected API operation and data access path.
3. Verify deny-by-default behavior, deny precedence, tenant isolation, privilege escalation resistance, and policy-to-route coverage with independent tests.
4. Confirm that every relevant read, write, background task, and alternate entry point enforces the same policy.
5. Run integration and end-to-end authorization tests against the actual generated application.

This engine is a general capability primitive; it does not itself certify authorization for any generated system.
