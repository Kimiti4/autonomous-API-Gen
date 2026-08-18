"""R2.10.6 — ISR -> Compiler Backend consumption contract.

The compiler backend is a CONSUMER of the ISR, never a participant: it may
read the semantic projection and realize it, but it may never mutate the ISR,
add meaning, infer requirements, inject technology concepts, rewrite
evolution decisions, or weaken constitutional constraints. This package
owns the read-only ``CompilerBackend`` protocol, the deterministic
``BackendSemanticModel`` projection, the three-layer ContaminationGuard, and
the eight-gate CompilationIntegrityGate that certifies a compilation.
"""