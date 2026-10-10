# Bucket 4.2 — Deployed-app observation and governed maintenance

Bucket 4.2 extends existing-codebase maintenance to applications that already
have a deployment/runtime surface. It closes the boundary between “the code
exists” and “the deployed system is behaving as expected” without granting
autonomous production authority.

## Contract

The deployed-app path must:

1. identify the deployed revision and environment fingerprint;
2. collect runtime health and verification evidence;
3. compare the observation with the declared deployment baseline;
4. record drift as evidence, separating advisory findings from authoritative
   obligations;
5. admit maintenance/enhancement work only when the work is explicitly
   authorized and within the existing obligation set;
6. require deployment access in addition to explicit authorization for any
   production write;
7. retain an observation digest so later repair/verification work can reference
   exactly what was observed.

## Anti-hallucination rule

A runtime observation, scanner finding, metric regression, or drift finding does
**not** create a new requirement.

An unbound finding is advisory. A finding may drive executable work only when it
is mapped to an already-authorized obligation. This prevents the deployed-app
loop from turning telemetry into endless autonomous feature creation.

## Evidence boundary

deployed system -> runtime observation -> drift classification

- advisory drift -> report only;
- authorized obligation -> governed repair and verification;
- production write -> requires deployment access and human authorization.

A changed source revision or environment fingerprint is a baseline mismatch,
not proof of a defect. It blocks autonomous maintenance admission until the
baseline is re-established or the change is explicitly handled by the governed
workflow.

## Surface compatibility

The Bucket 4.1 surface modes remain authoritative:

- frontend-only;
- backend-only;
- API-contract-only;
- whole application.

Bucket 4.2 adds runtime evidence; it does not create a new surface authority.

## Stop condition

The system stops when the authorized obligation set is complete and the
required verification/deployment-readiness evidence exists. Additional
observations remain advisory unless separately authorized.

Production deployment remains a human-authorized action.


## Maintenance-record input hardening

The maintenance evidence validator rejects whitespace-only observation, obligation,
patch, and authorization identifiers. Verification evidence entries must be non-empty
strings; malformed entries fail closed rather than raising an incidental attribute
error. Focused regression tests cover these invalid inputs.
