# VS1_RUNTIME_OBSERVATION_D27 (VS-D27)

**Status:** VS-1 Deliverable VS-D27. Runtime observation of the D26
deployment artifact (`vs1-deploy-obj001-4ca3d24c…`) on an explicitly
authorized loopback fixture.
**Governance:** OBSERVATION ONLY. Raw mechanical facts; no interpretation,
authorization, mutation, or evolution. Nothing here claims correctness,
readiness, superiority, or production fitness.

---

## 1. What was observed

`vs1-impl-obj001-v1` serving on loopback (identity-gated to the D26
manifest hash, v1/v2 entrypoints excluded by process assertion):
registration, login, invalid-credential 401, admin grant, authenticated
reads, priority create ×3 (LOW/MEDIUM/HIGH each echoed), priority filter
HIGH/LOW with per-item verification, invalid create/filter 422, priority
update + read-after-update, outsider filter 403, member-role 403, delete +
read-after-delete 422, lifecycle events, restart persistence, clean
shutdown. 23/23 PASS, 0 FAIL/UNDETERMINED/BLOCKED.

## 2. Strongest mechanical facts

- Filter responses verified per-item (every returned task matches), not
  just status-checked.
- Restart persistence proven in both directions at once: the pre-restart
  LOW→HIGH update survived AND the pre-restart MEDIUM deletion stayed
  deleted.
- The permitted-operation record derives from a real performed response,
  never a stub (a stub was caught and removed during construction).
- Secrets exist only as call-local test arguments; the evidence blob is
  verified free of secret shapes and raw credential strings.

## 3. Determinism & integrity

Normalized form drops timestamps/variable measurements; D01–D26 + ISR
recomputed unchanged; D22/D23/D24/D25 byte-stable; B3-v2 chain intact.
`tests/vs1/test_runtime_observation_d27.py`: 19/19. Evidence
`731ee7a264906f44…`, timestamp-independent. Uncommitted.

---

*End of VS-D27 artifact. Interpretation belongs to D28 (not authorized).*
