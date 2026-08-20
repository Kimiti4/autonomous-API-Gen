"""R2.10.6 — the ISR -> Compiler Backend consumption contract.

The backend is a CONSUMER, never a PARTICIPANT. This module fixes the
contract surface:

  1. ``CompilationTarget`` is a REALIZATION SELECTION (language, runtime,
     framework, capabilities, version). It is passed TO the backend at
     compile time and is never embedded in the ISR — the ISR stays
     realization-neutral (``isr_has_no_target_genes``).
  2. ``CompilerBackend`` is a read-only protocol: ``semantic_projection``
     (the deterministic, faithful view of the ISR it compiles) and
     ``compile`` (which returns a ``CompilationResult`` whose artifact
     binds its provenance). No mutation surface.
  3. ``BackendSemanticModel`` is the projection boundary: the canonical,
     hash-stable representation of the semantics a backend carries into
     its realization. Capabilities enumerate WHAT the ISR expresses;
     constraints carry the canonical content of every semantic gene by
     KIND; protected_regions carry the constitutional preservation
     declaration. Deterministic and faithful by construction.
  4. Capability mismatch is EXPLICIT (SUPPORTED / PARTIALLY_SUPPORTED /
     UNSUPPORTED), never silent omission — Gate D rejects a backend that
     drops a semantic from its declaration.
  5. The three-layer ContaminationGuard:
       Layer 1 — the backend module is structurally read-only (AST scan
                 rejects mutation-shaped call sites).
       Layer 2 — the ISR stays technology-neutral under compilation (the
                 eight named mechanism lints + the capability free-text
                 scan + the realization lexicon over the semantic payload).
       Layer 3 — no reverse contamination: the artifact's declared source
                 ISR identity equals the compiled ISR's identity.

The module holds no evaluation machinery and no ledger binding — the
evidence substrate (Gate H) is the ledger's job, via duck-typed
``record_compilation``.
"""
from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from enum import Enum, unique
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

from constitutional_architecture.isr.semantics.boundary import (
    BOUNDARY_MECHANISM_TERMS,
    assert_boundary_technology_agnostic,
)
from constitutional_architecture.isr.semantics.deployment import (
    DEPLOYMENT_MECHANISM_TERMS,
    assert_deployment_technology_agnostic,
)
from constitutional_architecture.isr.semantics.documentation import (
    DOCUMENTATION_MECHANISM_TERMS,
    assert_documentation_technology_agnostic,
)
from constitutional_architecture.isr.semantics.decision import (
    assert_decision_technology_agnostic,
)
from constitutional_architecture.isr.semantics.evolution_policy import (
    EVOLUTION_MECHANISM_TERMS,
    assert_evolution_technology_agnostic,
)
from constitutional_architecture.isr.semantics.migration import (
    MIGRATION_MECHANISM_TERMS,
    assert_migration_technology_agnostic,
)
from constitutional_architecture.isr.semantics.projection import (
    canonical_form,
    canonicalize,
    semantic_content_hash,
)
from constitutional_architecture.isr.semantics.reliability import (
    RELIABILITY_MECHANISM_TERMS,
    assert_reliability_technology_agnostic,
)
from constitutional_architecture.isr.semantics.requirement import (
    REQUIREMENT_MECHANISM_TERMS,
    assert_requirement_technology_agnostic,
)
from constitutional_architecture.isr.semantics.testing_anchor import (
    TESTING_MECHANISM_TERMS,
    assert_testing_technology_agnostic,
)

from tiannara.application.evolution.identity_index import DOMAINS, IdentityIndex


# -- capability support --------------------------------------------------------

@unique
class CapabilitySupport(str, Enum):
    """How a backend carries one semantic into its realization.

    SUPPORTED means the semantic is carried; PARTIALLY_SUPPORTED means it is
    carried with a declared degradation; UNSUPPORTED means the backend cannot
    realize it and says so explicitly. The invariant: a mismatch is always
    DECLARED, never silently omitted.
    """

    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class CapabilityCoverage:
    """One semantic's declared support on a backend."""

    capability_id: str
    support: CapabilitySupport
    note: str = ""


# -- the realization selection (never embedded in the ISR) ---------------------

@dataclass(frozen=True)
class CompilationTarget:
    """A realization selection: WHAT the compilation should produce, never
    WHAT the system IS. Passed to the backend at compile time; the ISR never
    carries it (``isr_has_no_target_genes`` is a gate obligation)."""

    target_id: str
    language: str
    runtime: str
    framework: str
    capabilities: frozenset[str] = frozenset()
    version: str = "1.0.0"


# -- the projection boundary ---------------------------------------------------

@dataclass(frozen=True)
class BackendSemanticModel:
    """The deterministic, faithful view of the ISR a backend compiles.

    ``model_hash`` is the content hash over capabilities + constraints +
    protected_regions (stable across runs, sensitive to every semantic
    change); ``source_isr_hash`` binds the model to the exact ISR it was
    derived from. ``constraints`` carries the canonical content of every
    semantic gene as (kind, canonical_form) pairs; ``protected_regions``
    carries the constitutional preservation declaration by content.
    """

    model_hash: str
    source_isr_hash: str
    capabilities: frozenset[str]
    constraints: tuple[tuple[str, Any], ...]
    protected_regions: tuple[Any, ...]


# -- semantic enumeration ------------------------------------------------------

# (semantic id, system carrier attribute); behavior/migration/temporal live
# inside modules, so their carrier check walks every module.
_SEMANTIC_CARRIERS: tuple[tuple[str, str], ...] = (
    ("capability", "business_capabilities"),
    ("requirement", "requirements"),
    ("acceptance_criterion", "acceptance_criteria"),
    ("boundary", "architectural_boundaries"),
    ("testing_anchor", "testing_anchors"),
    ("reliability", "reliability_requirements"),
    ("deployment", "deployment_intents"),
    ("documentation", "documentation_intents"),
    ("evolution_objective", "evolution_objectives"),
    ("protected_region", "protected_regions"),
    ("evolution_policy", "evolution_policies"),
    ("behavior", "workflows"),
    ("migration", "data_migrations"),
    ("temporal", "temporal_constraints"),
    ("decision", "architectural_decisions"),
)

_MODULE_CARRIERS: frozenset[str] = frozenset(
    {"workflows", "data_migrations", "temporal_constraints"}
)


def enumerate_isr_semantics(isr: Any) -> frozenset[str]:
    """The semantic ids an ISR expresses: every carrier with content (empty
    carriers are identity-neutral, Option A). The required-coverage universe
    for Gate D."""
    system = isr.system
    present: set[str] = set()
    for domain, carrier in _SEMANTIC_CARRIERS:
        if carrier in _MODULE_CARRIERS:
            if any(getattr(module, carrier) for module in system.modules):
                present.add(domain)
        elif getattr(system, carrier):
            present.add(domain)
    return frozenset(present)


# -- deterministic model derivation -------------------------------------------

# the identity-index gene domains (the single identity namespace) followed by
# the two policy carriers that live directly on System.
_MODEL_KIND_ORDER: tuple[str, ...] = DOMAINS + (
    "evolution_objective",
    "evolution_policy",
)


def derive_backend_semantic_model(
    isr: Any, identity_index: Any = None
) -> BackendSemanticModel:
    """Derive the projection boundary from one ISR, deterministically.

    Constraints are walked through the identity index (the single identity
    namespace — genes are addressed by (domain, gene_id), never by raw
    projection paths), then the two policy carriers are appended, and the
    whole tuple is sorted by (kind, canonical content) so the model is
    backend-independent and stable across runs. Protected regions travel in
    their own field (the constitutional preservation declaration).
    """
    index = (identity_index or IdentityIndex).derive(isr)
    constraints: list[tuple[str, Any]] = []
    by_domain = index.genes_by_domain()
    for kind in _MODEL_KIND_ORDER:
        for _, gene in by_domain.get(kind, ()):
            constraints.append((kind, canonical_form(gene)))
    system = isr.system
    for kind, carrier in (
        ("evolution_objective", "evolution_objectives"),
        ("evolution_policy", "evolution_policies"),
    ):
        for gene in getattr(system, carrier):
            constraints.append((kind, canonical_form(gene)))
    constraints.sort(key=lambda pair: (pair[0], canonicalize(pair[1])))
    regions = tuple(
        sorted(
            (canonical_form(region) for region in system.protected_regions),
            key=canonicalize,
        )
    )
    capabilities = enumerate_isr_semantics(isr)
    model_hash = hashlib.sha256(
        canonicalize(
            {
                "capabilities": sorted(capabilities),
                "constraints": constraints,
                "protected_regions": regions,
            }
        ).encode("utf-8")
    ).hexdigest()
    return BackendSemanticModel(
        model_hash=model_hash,
        source_isr_hash=semantic_content_hash(isr),
        capabilities=frozenset(capabilities),
        constraints=tuple(constraints),
        protected_regions=regions,
    )


# -- the constitutional surface (Gate G) --------------------------------------

_CONSTITUTIONAL_KINDS: tuple[tuple[str, str], ...] = (
    ("requirement", "requirements"),
    ("acceptance_criterion", "acceptance_criteria"),
    ("reliability", "reliability_requirements"),
    ("deployment", "deployment_intents"),
    ("boundary", "architectural_boundaries"),
    ("testing_anchor", "testing_anchors"),
)


def _model_forms_of_kind(model: BackendSemanticModel, kind: str) -> frozenset[str]:
    return frozenset(
        canonicalize(form) for (k, form) in model.constraints if k == kind
    )


def _isr_forms(isr: Any, carrier: str) -> frozenset[str]:
    return frozenset(
        canonicalize(canonical_form(gene))
        for gene in getattr(isr.system, carrier, ())
    )


def constitutional_surface_intact(
    isr: Any, model: BackendSemanticModel
) -> tuple[str, ...]:
    """The constitutional preservation comparison: every constitutional
    carrier the ISR declares must be carried, content-identical, in the
    backend's projection — requirements, acceptance criteria, reliability,
    deployment, boundaries, testing anchors, and protected regions.

    Returns a tuple of mismatch descriptions (empty = intact), so the gate
    can produce evidence naming exactly what a backend weakened.
    """
    mismatches: list[str] = []
    for kind, carrier in _CONSTITUTIONAL_KINDS:
        isr_forms = _isr_forms(isr, carrier)
        model_forms = _model_forms_of_kind(model, kind)
        if isr_forms != model_forms:
            mismatches.append(
                f"{kind}: ISR declares {len(isr_forms)}, "
                f"backend projects {len(model_forms)}"
            )
    isr_regions = _isr_forms(isr, "protected_regions")
    model_regions = frozenset(canonicalize(region) for region in model.protected_regions)
    if isr_regions != model_regions:
        mismatches.append(
            f"protected_region: ISR declares {len(isr_regions)}, "
            f"backend projects {len(model_regions)}"
        )
    return tuple(mismatches)


# -- realization lexicon (the technology-neutrality backstop) ------------------

# Terms whose presence in the ISR's semantic payload means a realization
# technology leaked INTO the declaration. All eight existing mechanism-term
# sets already reject their members; this lexicon adds the realization
# technologies no existing lint covers (react/fastapi/postgres) and re-asserts
# the deployment/boundary guard terms at the whole-ISR level.
REALIZATION_TECHNOLOGY_LEXICON: frozenset[str] = frozenset({
    "react", "fastapi", "postgres", "postgresql",
    "terraform", "kubernetes", "docker", "azure", "aws", "gcp",
})


def realization_lexicon_hits(isr: Any) -> tuple[str, ...]:
    """Which realization technologies (if any) leaked into the ISR's semantic
    payload. The scan covers the canonical system projection (every carrier,
    including evolution objectives / policies / protected regions)."""
    lowered = canonicalize(isr.system).lower()
    return tuple(
        term for term in sorted(REALIZATION_TECHNOLOGY_LEXICON) if term in lowered
    )


def isr_has_no_target_genes(isr: Any) -> bool:
    """The gate obligation: the ISR carries no compilation target.

    Two structural checks: (1) no semantic carrier is named target /
    compilation_target (the realization selection has no home in the ISR),
    and (2) no realization-technology term appears in the canonical semantic
    payload. True = the ISR stays realization-neutral.
    """
    if any(domain in ("target", "compilation_target") for domain, _ in _SEMANTIC_CARRIERS):
        return False
    return not realization_lexicon_hits(isr)


# -- provenance binding and the result -----------------------------------------

@dataclass(frozen=True)
class CompilationProvenance:
    """The binding between an artifact and its source: the ISR identity, the
    realization selection, and the backend that produced it. The artifact
    itself must re-declare the same isr_hash (Gate F round-trip)."""

    isr_hash: str
    target_id: str
    backend_id: str
    backend_version: str
    model_hash: str


@dataclass(frozen=True)
class CompilationResult:
    """One compilation: the artifact plus its provenance binding and its
    explicit capability coverage. ``artifact_hash`` is the content hash of
    the artifact — the realization's own identity."""

    artifact: dict[str, Any]
    isr_hash: str
    target_id: str
    backend_id: str
    backend_version: str
    artifact_hash: str
    provenance: CompilationProvenance
    capability_coverage: tuple[CapabilityCoverage, ...]


def reconstruct_semantic_source(result: CompilationResult) -> str:
    """The semantic source as re-declared inside the compiled artifact
    (Gate F round-trip reads it back from the realization, never from the
    result object)."""
    return str(result.artifact["semantic_source"]["isr_hash"])


# -- the read-only backend protocol --------------------------------------------

@runtime_checkable
class CompilerBackend(Protocol):
    """The consumption contract. A backend:

      * declares its identity (backend_id, backend_version);
      * projects the ISR it would compile (semantic_projection — the
        deterministic, faithful view);
      * compiles a target realization (compile) WITHOUT mutating the ISR,
        WITHOUT adding or inferring semantics, and WITHOUT weakening the
        constitutional surface.

    There is no mutation surface: the ISR is passed by value and the result
    carries its own artifact. The protocol is runtime-checkable so a gate can
    reject a non-conforming backend structurally.
    """

    backend_id: str
    backend_version: str

    def semantic_projection(self, isr: Any) -> BackendSemanticModel: ...

    def compile(
        self, isr: Any, target: CompilationTarget
    ) -> CompilationResult: ...


# -- the three-layer contamination guard --------------------------------------

_BANNED_CALL_FRAGMENTS: tuple[str, ...] = (
    "replace_gene", "mutate", "set_", "add_", "remove_", "delattr", "setattr",
)


def backend_read_only_violations(source: Any) -> tuple[str, ...]:
    """Layer 1: structural scan of a backend module's source for mutation-
    shaped call sites (replace_gene / mutate / set_ / add_ / remove_ /
    delattr / setattr name fragments). Returns violation descriptions
    (empty = the module is structurally read-only)."""
    if isinstance(source, (str, Path)):
        tree = ast.parse(Path(source).read_text(encoding="utf-8"))
    else:
        tree = source
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute):
            name = func.attr
        elif isinstance(func, ast.Name):
            name = func.id
        else:
            continue
        for fragment in _BANNED_CALL_FRAGMENTS:
            if fragment in name:
                violations.append(
                    f"call '{name}' carries banned mutation fragment "
                    f"'{fragment}' (line {getattr(node, 'lineno', '?')})"
                )
    return tuple(dict.fromkeys(violations))


_ALL_MECHANISM_TERMS: frozenset[str] = (
    BOUNDARY_MECHANISM_TERMS
    | DEPLOYMENT_MECHANISM_TERMS
    | DOCUMENTATION_MECHANISM_TERMS
    | EVOLUTION_MECHANISM_TERMS
    | MIGRATION_MECHANISM_TERMS
    | RELIABILITY_MECHANISM_TERMS
    | REQUIREMENT_MECHANISM_TERMS
    | TESTING_MECHANISM_TERMS
)


def isr_technology_neutral_hits(isr: Any) -> tuple[str, ...]:
    """Layer 2: every technology-coupling the ISR carries. The eight named
    mechanism lints (migration / reliability / boundary / deployment /
    requirement / testing_anchor / documentation / evolution), the capability
    free-text scan against the union of all eight term sets, and the
    realization lexicon over the canonical semantic payload (including each
    identity-index gene — the single identity namespace)."""
    hits: list[str] = []
    system = isr.system
    for capability in system.business_capabilities:
        leaked = tuple(
            term for term in _ALL_MECHANISM_TERMS if term in capability.intent.lower()
        )
        if leaked:
            hits.append(
                f"capability '{capability.capability_id}' intent couples "
                f"to mechanism(s): {leaked}"
            )
    migration_carriers = tuple(
        migration
        for module in system.modules
        for migration in module.data_migrations
    )
    linted = (
        ("migration", migration_carriers, assert_migration_technology_agnostic),
        ("reliability", system.reliability_requirements,
         assert_reliability_technology_agnostic),
        ("boundary", system.architectural_boundaries,
         assert_boundary_technology_agnostic),
        ("deployment", system.deployment_intents,
         assert_deployment_technology_agnostic),
        ("requirement", system.requirements,
         assert_requirement_technology_agnostic),
        ("testing_anchor", system.testing_anchors,
         assert_testing_technology_agnostic),
        ("documentation", system.documentation_intents,
         assert_documentation_technology_agnostic),
        ("evolution", system.evolution_policies,
         assert_evolution_technology_agnostic),
        ("decision", system.architectural_decisions,
         assert_decision_technology_agnostic),
    )
    for name, carriers, lint in linted:
        for gene in carriers:
            try:
                lint(gene)
            except ValueError as exc:
                hits.append(f"{name}: {exc}")
    lexicon = realization_lexicon_hits(isr)
    if lexicon:
        hits.append(f"realization technology leaked into the ISR: {lexicon}")
    return tuple(dict.fromkeys(hits))


def reverse_contamination_violations(result: CompilationResult) -> tuple[str, ...]:
    """Layer 3: identity-flow integrity of one compilation. The provenance's
    declared source ISR identity, the result's own ISR identity, and the
    artifact's re-declared semantic source must all agree — no content may
    have flowed from the artifact back into the ISR (the ISR's identity is
    unchanged, so the compiled realization never rewrites its source)."""
    violations: list[str] = []
    if result.provenance.isr_hash != result.isr_hash:
        violations.append(
            f"provenance source isr_hash {result.provenance.isr_hash[:12]}… "
            f"!= result isr_hash {result.isr_hash[:12]}…"
        )
    try:
        reconstructed = result.artifact["semantic_source"]["isr_hash"]
    except (KeyError, TypeError):
        reconstructed = ""
    if str(reconstructed) != result.isr_hash:
        violations.append(
            f"artifact semantic_source {reconstructed!r} "
            f"!= result isr_hash {result.isr_hash[:12]}…"
        )
    return tuple(violations)


class ContaminationGuard:
    """The three-layer contamination guard (user-locked invariants 3-5):

      Layer 1 — assert_backend_module_is_read_only: the backend's own source
                is structurally read-only (no mutation-shaped call sites).
      Layer 2 — assert_isr_technology_neutral: the ISR carries no mechanism
                or realization technology, before or after compilation.
      Layer 3 — assert_no_reverse_contamination: the artifact's declared
                source ISR identity equals the compiled ISR's identity.

    Raises AssertionError on violation with evidence naming the exact leak.
    """

    def __init__(self, identity_index: Any = None) -> None:
        self._identity_index = identity_index or IdentityIndex

    def assert_backend_module_is_read_only(self, source: Any) -> None:
        violations = backend_read_only_violations(source)
        if violations:
            raise AssertionError(
                "backend module is NOT read-only: " + "; ".join(violations)
            )

    def assert_isr_technology_neutral(self, isr: Any) -> None:
        index = self._identity_index.derive(isr)
        hits = list(isr_technology_neutral_hits(isr))
        for (domain, _), gene in index.genes.items():
            leaked = tuple(
                term
                for term in sorted(REALIZATION_TECHNOLOGY_LEXICON)
                if term in canonicalize(gene).lower()
            )
            if leaked:
                hits.append(
                    f"{domain} gene couples to realization(s): {leaked}"
                )
        if hits:
            raise AssertionError(
                "ISR is NOT technology-neutral: " + "; ".join(hits)
            )

    def assert_no_reverse_contamination(self, result: CompilationResult) -> None:
        violations = reverse_contamination_violations(result)
        if violations:
            raise AssertionError(
                "reverse contamination: " + "; ".join(violations)
            )