# CAPABILITY CONSTITUTION — Phase 0

Tiannara's canonical senior-engineering capability vocabulary and proof contract.

## Taxonomy

| ID | Capability |
|---|---|
| C01 | Requirements engineering |
| C02 | Architecture |
| C03 | Backend engineering |
| C04 | API engineering |
| C05 | Data engineering |
| C06 | Distributed systems |
| C07 | Event-driven systems |
| C08 | Financial/transaction systems |
| C09 | Frontend engineering |
| C10 | Security |
| C11 | Testing |
| C12 | Observability |
| C13 | DevOps / CI/CD |
| C14 | Cloud infrastructure |
| C15 | Performance engineering |
| C16 | Reliability engineering |
| C17 | Production debugging |
| C18 | Documentation |
| C19 | System evolution |
| C20 | Engineering governance |

## Proof contract

Every capability requires explicit evidence for requirements, architecture, implementation, verification, security, operations, and provenance. Missing evidence is non-certifying. The contract never infers certification from generated code, configuration, or a boolean claim.

## Boundary

The constitution is technology-neutral. FastAPI, React, PostgreSQL, AWS, Docker and other concrete technologies remain downstream compiler or deployment targets. Downstream implementation cannot silently redefine upstream architectural authority.

## Gate

**CAP-000 — Senior Engineering Capability Constitution**

The implementation defines C01–C20 and a fail-closed certification evaluator. It does not claim any capability is certified; later phases must provide the evidence required by each contract.
