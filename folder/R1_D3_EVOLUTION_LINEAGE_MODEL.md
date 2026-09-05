# R1_D3_EVOLUTION_LINEAGE_MODEL (R1-D.3 D3-07)

**Status:** R1-D.3 Deliverable D3-07. Canonical evolution lineage model. Index: `folder/R1_D3_EVOLUTION_INVENTORY.md` (D3-01), `folder/CONTRACT_EvolutionRecord_EIR.md` (D06 R1-B), `folder/CONTRACT_ArchitectureCandidate.md` (D04 R1-B).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; R1-C C01–C12; R1-D.1 D1–D9; R1-D.2 D2-D1–D2-D10; the R1-D.3 master prompt.

---

## 1. Purpose

Define the canonical evolution lineage graph. The lineage must remain reconstructable: given any candidate, the full evolution history (parent → operation → child) must be recoverable.

---

## 2. Lineage graph types

The canonical lineage supports three graph types:

### 2.1 Linear lineage (sequential)

```text
Candidate A
   │
   ├── operation O1
   │
   ▼
Candidate B
   │
   ├── operation O2
   │
   ▼
Candidate C
```

A single chain of evolution. Each candidate has one parent and one child (except the root, which has no parent, and the leaf, which has no child).

### 2.2 Branching lineage (selection)

```text
             Candidate A
              /       \
             /         \
           O1           O2
           ↓             ↓
       Candidate B   Candidate C
```

A candidate has one parent but multiple children. This is the typical pattern after a mutation or crossover: one parent produces multiple children, and selection picks one or more.

### 2.3 Crossover lineage (recombination)

```text
Candidate A ─────┐
                  ├── Crossover O ──→ Candidate C
Candidate B ─────┘
```

A candidate has two (or more) parents and one child. This is the crossover pattern. Both parents contribute to the child.

---

## 3. Canonical lineage fields

Each lineage edge is an `EvolutionRecord` (D06) with the following required fields (per the D06 contract + D3-04/D3-05 refinements):

| Field | Source | Description |
|---|---|---|
| `record_id` | D06 §3 | Content hash of the record |
| `operation_id` | D05 §4 | UUIDv5 over operator type + parameters + timestamp |
| `parent_architecture` | D04 §4 | Parent candidate content hash |
| `child_architecture` | D04 §4 | Child candidate content hash (when produced) |
| `parent_candidate_ids` | D05 §4 | Input candidate IDs (for crossover: multiple) |
| `resulting_candidate_ids` | D05 §4 | Output candidate IDs |
| `operator` | D05 §4 | Operator type (mutation, crossover, etc.) |
| `parameters` | D05 §4 | Operator-specific parameters |
| `seed` | D05 §4 | Randomness seed (when stochastic) |
| `transformations` | D06 §3 | **Non-empty** for `OPERATION_OK` (R1-D.3 fix for the `transformations=[]` defect) |
| `source_isr` | D06 §3 | Source ISR content hash |
| `target_isr` | D06 §3 | Target ISR content hash (when changed) |
| `status` | D06 §3 | OPERATION_OK / FAILED / BLOCKED / INDETERMINATE |
| `timestamp` | D06 §3 | ISO8601 |
| `evolution_run_id` | D06 §3 | Evolution run identifier |
| `evidence_refs` | D06 §3 | References to verification/certification evidence |

---

## 4. Reconstructability

Given any candidate `C`, the full lineage is reconstructed by:

1. **Find the candidate's content hash** (the candidate's identity).
2. **Find the EvolutionRecord(s) where `child_architecture == C.content_hash`** — these are the records that produced `C`.
3. **For each record, find the parent_candidate_ids** — these are the parents.
4. **Recursively** reconstruct each parent's lineage.
5. **Stop** when a parent has no parent (seed candidate) or when a parent is no longer in the lineage (e.g., pruned).

The reconstruction is:

- **Deterministic** (same content → same lineage).
- **Verifiable** (each parent's content hash is verified against the parent's serialized content).
- **Tamper-evident** (any modification to a parent invalidates its content hash, which breaks the lineage).

---

## 5. In-memory vs durable lineage

| Aspect | In-memory (current; canonical) | Durable (future; R1-E.6) |
|---|---|---|
| Storage | `evolution/core/construction.py` + `history.py` | Hash-chained ledger (similar to `certification/evidence/ledger.py`) |
| Identity | (none; object identity) | Content hash (SHA-256) |
| Immutability | (per operation; frozen objects) | Append-only ledger |
| Provenance | (metadata only) | Hash-chained records |
| Cross-contract | (not consumed) | Consumable by VerificationResult, CertificationEvidence |
| Location | `evolution/core/construction.py` | `release/evidence/lineage/{wave}.jsonl` (mirror certification ledger) |

**Observation:** The current in-memory lineage is canonical for the evolution runtime. Durable lineage is R1-E.6 work (per the R1-C C10 and R1-D.2 contracts).

---

## 6. Branching and crossover patterns

### 6.1 Branching (mutation + selection)

A mutation produces one child. Selection picks one or more children. The branching pattern:

```text
                     A
                     │
              ┌──────┴──────┐
              │             │
         mutation O1   mutation O2
              │             │
              B             C
              │             │
         selection       selection
              │             │
              ↓             ↓
         selected B   not selected
```

- `A → B` via `mutation O1` (record 1).
- `A → C` via `mutation O2` (record 2).
- Selection picks `B`; `C` is not selected.

Both records (1 and 2) are immutable. The lineage graph contains both edges.

### 6.2 Crossover (recombination)

A crossover produces one child from two parents:

```text
        A               B
        │               │
        └───────┬───────┘
                │
           crossover O
                │
                ↓
                C
```

- `A → C` via `crossover O` (record 1; parent_candidate_ids = [A, B]).
- `B → C` via `crossover O` (record 2; same operation, second parent).
- Or: one record with `parent_candidate_ids = [A, B]`.

The canonical model uses **one record per operation** with `parent_candidate_ids` as a list.

---

## 7. Lineage edge classification

Each lineage edge is one of:

| Edge type | Description | Example |
|---|---|---|
| `parent → child` (single parent) | One parent, one child | mutation, evaluation |
| `parent1 + parent2 → child` (crossover) | Two parents, one child | crossover, recombination |
| `child (no parent)` | Seed candidate | initial population |
| `parent → none` (selection failure) | Candidate was not selected | evaluation-only, no selection |

---

## 8. Cross-references

- D3-01: `folder/R1_D3_EVOLUTION_INVENTORY.md`
- D06 (R1-B): `folder/CONTRACT_EvolutionRecord_EIR.md`
- D04 (R1-B): `folder/CONTRACT_ArchitectureCandidate.md`
- D05 (R1-B Part I + D3-04 Part II): `folder/CONTRACT_EvolutionOperation.md`
- D3-08: `folder/R1_D3_EVOLUTION_MIGRATION_MAP.md` (next)

---

*End of D3-07. The canonical evolution lineage model is complete. 3 graph types (linear, branching, crossover). Reconstructability is deterministic and verifiable. In-memory lineage is canonical; durable lineage is R1-E.6. D3-08 (migration map) follows.*
