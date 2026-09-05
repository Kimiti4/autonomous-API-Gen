# POST_R1_D_LINEAGE_RECONCILIATION (R1-RG-05)

**Status:** R1-RG-05. Forward/reverse/evolution lineage, provenance, identity correlation. Spec: `folder/postr1d.md` §§11–12.

---

## 1. Forward lineage

Requirement → rg node (TEST) → ISR node (RUNTIME, `requirement_refs`) → Candidate (RUNTIME, constructor) → CompilerIR (RUNTIME mediated) → ArtifactSet (RUNTIME, repo) → Verification (RUNTIME, conformance + stages) → RuntimeObservation (CONTRACT, C-17). Full detail in R1-RG-04 §1.

## 2. Reverse lineage

RuntimeObservation → ArtifactSet → CompilerIR → ArchitectureCandidate → EvolutionRecord → EvolutionOperation → Parent (D3-07 graphs). Runtime edges CONTRACT (D12 fields pinned by rg test); evolution-internal edges TEST (R1-D.3). No guessing, mutable names, timestamps-alone, paths-alone, or positional references anywhere in the chain: every link is a content hash or UUIDv5 identity.

## 3. Evolution lineage

Linear / branching / crossover graphs per D3-07, all TEST-proven. `transformations=[]` constitutional defect does not touch canonical lineage (canonical records sources explicitly; pinned by test).

## 4. Provenance

Per-contract provenance (operator, seed, run id, actor, timestamps) + certification ledger + `PlanArtifacts` 4-hash correlation. Single provenance authority per layer (RG-02); no second store introduced.

## 5. Identity correlation

| Object | Identity | Correlatable without guessing? |
|---|---|---|
| ISR revision | SHA-256 `content_hash` | YES |
| Genome | SHA-256 `genome_content_hash` | YES |
| CompilationPlan | derived `plan_id` + `plan_hash` | YES (via PlanArtifacts; canonical hash R1-D.5) |
| Operation | UUIDv5 over type+params+timestamp | YES |
| Record/event | content hash / event hash | YES |
| Verification | UUIDv5 subject+verifier+timestamp | YES |
| Certification evidence | UUIDv5 + ledger hash chain | YES |
| Artifact | paths + content (manifest hash R1-D.5) | YES (via repo + plan hash) |

Correlation sufficient for future evolutionary feedback (G29: YES).

## 6. Hash reconciliation (§12)

| Object | Scheme |
|---|---|
| ISR | content hashed (SHA-256) |
| CompilerIR | semantic/derived hybrid today (plan_id + plan_hash); canonical content hash contract (R1-D.5) |
| Artifact | per-file content + manifest (hash formalization R1-D.5) |
| Evolution identity | content-derived (genome hash; UUIDv5 operations) |
| EvolutionRecord identity | content/event hashed |
| Provenance identity | per-record hashes + ledger chain |
| Ledger identity | hash-chained (B3-v2 intact) |

No incompatible identity notions cross-compared. Historical chains untouched.

---

*End of R1-RG-05.*
