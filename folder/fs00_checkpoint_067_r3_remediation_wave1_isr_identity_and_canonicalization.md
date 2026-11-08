# FS-00 Checkpoint CP067-R3 — Remediation Wave 1: ISR Identity Authority and Family Canonicalization

**Checkpoint status:** **`PARTIAL_EVIDENCE`** — W01/W02 **implemented**; **independent verification recorded** (see `folder/fs00_checkpoint_067_r3_independent_verification.md`); **P0 findings not closed**.

**Authorization:** Human approval + Wave 0 `AUTHORIZED_TO_START` for W01/W02 (Amos Kimiti Kariuki, 2026-11-08T15:39+03:00).

**Branch / HEAD:** `remediation/w12-executable-effect-contract` @ `78fbcad6e357328c9d7ef5df92e9e2aa40044f17` (implementation on dirty tree).

---

## 1. Scope executed

| Package | Status | Evidence |
| --- | --- | --- |
| **R1-W01** | `IMPLEMENTATION_PRESENT_UNVERIFIED` | Digest envelope, verification policy, orchestration ingress gate |
| **R1-W02** | `IMPLEMENTATION_PRESENT_UNVERIFIED` | Tier A contracts F-01/F-02, canonical bytes API |
| R1-W03 … W10 | Not in scope | Unchanged |

**Prohibitions observed:** No hash-path merge; no constitutional serializer semantic change; no F-10–F-13 trusted ingress change; no P0 closure claims.

---

## 2. Implementation summary

### R1-W01

| Module | Purpose |
| --- | --- |
| `isr/core/digest_envelope.py` | `DigestEnvelope` + authority domain constants |
| `isr/core/digest_verification.py` | Recompute, assert certification path, cross-domain policy |
| `isr/core/canonicalization_registry.py` | Contracts (shared with W02) |
| `constitutional_architecture/isr/versioning/digest_envelope.py` | F-06 envelope builder (separate domain) |
| `certification/orchestration/authority.py` | `assert_certification_digest_envelope` before ISR_VALIDATED |
| `certification/evidence_graph/isr_authority_audit.py` | Integrity verify when audit matches |

### R1-W02

- Registered contracts: **`isr.core.revision`**, **`isr.core.graph`** (Tier A only).
- `canonical_bytes_f01()` for reproducible bytes / golden testing.
- Unknown families: **`fail_closed`** via `get_canonicalization_contract`.

---

## 3. Tests executed (this checkpoint)

| Command | Result |
| --- | --- |
| `python -m pytest tests/isr/test_cp067_r3_w01_w02_digest_and_canonicalization.py -q` | **10 passed** |
| `tests/evidence_graph/test_checkpoint_067_isr_canonicality_audit.py` + `tests/orchestration/` | *(see status ledger)* |

---

## 4. P0 register (unchanged closure status)

| ID | Status |
| --- | --- |
| CP067-ISR-001 | **OPEN** — implementation slice only |
| CP067-ISR-002 … 008 | **OPEN** |

---

## 5. CP068

**`CP068_CONDITIONAL_ISOLATED_TESTING_ONLY`** — unchanged.

---

## 6. Next steps

1. **Independent verification** of W01/W02 (non-generator).
2. Expand Tier B canonicalization (F-04/F-05) in a separately authorized package.
3. **CP067-R4** or continued Wave 1: R1-W03/W09 when authorized.
