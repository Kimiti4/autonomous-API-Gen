# TIAKNARA Phase Ledger (rev. 3)

> Certification numbers are reserved for audits with measurable gates.
> Build-out work is labeled with capability (Cap-*) identifiers. A phase is
> only "complete" when its exit gate has been measured; substrate work is
> labeled calibrated, never certified.

```
S1        Calibration Harness Substrate                 CALIBRATED
          (rig + ports + evidence chain proven against reference adapters
           and hand-authored fixtures. NOT a certification.)

Cap-A     Typed ISR Schema + RequirementGraph           COMPLETE
          (system_model.v1 payload, abstract vocabulary, tech-coupling guard,
           RequirementGraph, graph_analysis, dual-path envelope.
           content_hash invariant preserved byte-for-byte. 26 tests.)

Guard-B1  Legacy Coupling Containment                   COMPLETE
          (LEGACY_COUPLING_REGISTRY + bidirectional scanner/guard test.
           Boundary frozen: cannot grow, must be explicitly shrunk.
           "docker" promoted from monitored ambiguity to banned token.)

Cap-B     Requirements Front-End                        IN PROGRESS
          B1 taxonomy + seeded sampler + RequirementSketch    COMPLETE (18 tests)
          B2 LLM port + RecordedModelProvider + recording       COMPLETE (15 tests)
          B3 Intent Compiler stages 1-6 + repair loop            COMPLETE (5 tests)
          B4 StatementRenderer + personas + defect injection     COMPLETE (6 tests)
          B5 Fidelity scoring + CalibrationEvidence hook          NEXT
          B6 First live calibration slice (provider decision)     BLOCKED

Cap-C     Real Compiler Backend(s)                      PENDING (gated by Cap-A)
          (>=1 production-language backend consuming SystemModel.)

Audit 31  Compiler Correctness Certification            BLOCKED (pending Cap-A, Cap-B, Cap-C)
Audit 32  Autonomous Code Quality Certification         BLOCKED (pending Audit 31)
Audit 33  Security Certification                        BLOCKED (pending Audit 31)
Audit 34  Architecture Evolution Certification          BLOCKED (pending Cap-C)
Audits 35-40                                          BLOCKED (pending predecessors)
```

## Notes
- Current suite: 1119 passed = 1060 floor + 26 Cap-A + 18 B1/guard + 15 B2.
  Zero regressions; legacy hash chains untouched.
- `docker` promoted from documented ambiguity to a banned token so the
  legacy coupling scanner can catch the `DeploymentSpec.container_runtime`
  default and the registry boundary is bidirectionally enforced.
- B2 ships NO live vendor adapter (that is B6). The contract is:
  record-once-live (B6) -> commit transcript -> replay-forever (B1-B5 tests).
  `RecordedModelProvider` is hermetic and zero-network by construction.
- Provenance wiring: `ModelCallRecord.provenance_tag()` yields
  `<model_id>:<signature_hash>`, the exact token fed into
  `RequirementGraph.provenance.model_versions` by B3.
