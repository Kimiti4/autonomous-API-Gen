"""R2.10.32 — engineering certification: measurement, never mutation.

The certification harness evaluates one artifact against the ISR that
produced it under the declared R2.10.32 contract:

  * ISR Conformance is DISPOSITIVE and checked FIRST — an artifact whose
    mandatory obligations are not enforced is NOT_CERTIFIED before any
    gradable dimension runs, and the violations are named.
  * The seven gradable dimensions (implementation, architecture, design,
    failure engineering, security, evolvability, operations) are analyzed
    over the artifact's real evidence by plug-in analyzers (the built-ins
    are deterministic over the artifact's declared coverage, projection,
    and bundle content — no external tools).
  * Every dimension result and every certificate is chain-anchored on the
    evolution ledger; the certificate's content hash commits to its
    evidence refs.
  * The certifier never mutates the ISR or the artifact. Remediation is
    the EvolutionaryQualityLoop's job: generate -> certify -> diagnose ->
    mutate_architecture -> regenerate -> re-certify, mutating ONLY the ISR
    through the declared mutation operators.

Weakness-to-mutation planning is declared, never invented: a weakness is
actionable only when a mutation mapping is declared for it; weaknesses
without a mapping (e.g. a backend's declared-unsupported semantics) are
carried in the diagnosis, never papered over.
"""
from __future__ import annotations

import dataclasses
import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from constitutional_architecture.isr.model import (
    AnchorAuthority,
    DegradationPolicy,
    DeploymentIntent,
    FailureMode,
    ProtectionPolicy,
    RecoveryBehavior,
    RecoveryObjective,
    ReliabilityRequirement,
    RolloutStrategy,
    TestingAnchor,
)
from constitutional_architecture.isr.semantics.projection import (
    canonical_form,
    canonicalize,
    semantic_content_hash,
)

from ..evolution.ledger import EventType, EvolutionEvent, EvolutionLedger
from .engineering_contract import (
    GRADABLE_DIMENSIONS,
    EngineeringDimension,
    EngineeringQualityContract,
    EngineeringVerdict,
    FindingSeverity,
    default_engineering_contract,
)

# ---------------------------------------------------------------------------
# finding / result shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """One named finding. CRITICAL is structurally dispositive; MAJOR fails
    its dimension's gate; MINOR and ADVISORY are carried and named."""

    severity: FindingSeverity
    description: str


def _meets_from_findings(findings: Sequence[Finding]) -> bool:
    return not any(
        f.severity in (FindingSeverity.CRITICAL, FindingSeverity.MAJOR)
        for f in findings
    )


@dataclass(frozen=True)
class ISRObligation:
    """One obligation extracted from an existing ISR carrier (E boundaries,
    D/F/G constraints, J protected-region decisions, requirements, testing
    anchors, …). Obligations are extracted, never invented."""

    obligation_id: str
    kind: str
    semantic_group: str
    canonical_form: Any
    mandatory: bool
    description: str


@dataclass(frozen=True)
class ConformanceFinding:
    """One conformance finding: a mandatory obligation that is not enforced
    (CRITICAL) or an advisory obligation with a declared limitation
    (ADVISORY). ``evidence`` carries the ledger-addressable enforcement
    evidence the finding was judged against."""

    obligation_id: str
    severity: FindingSeverity
    description: str
    evidence: tuple[Any, ...]


@dataclass(frozen=True)
class ISRConformanceResult:
    """The dispositive conformance result."""

    obligations: tuple[ISRObligation, ...]
    enforced: tuple[str, ...]
    violations: tuple[ConformanceFinding, ...]
    source_bound: bool
    all_mandatory_enforced: bool
    advisory_notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ArchitectureGraph:
    """The deterministic module graph of the artifact's bundle."""

    modules: tuple[str, ...]
    files: tuple[str, ...]
    edges: tuple[tuple[str, str, str], ...]  # (module, file, target_module)
    cycles: tuple[tuple[str, ...], ...]
    isolated: tuple[str, ...]


@dataclass(frozen=True)
class FailureScenario:
    """One failure scenario declared by the ISR (reliability recovery
    objective, migration rollback, deployment rollback) and its artifact
    enforcement disposition."""

    scenario_id: str
    source_kind: str
    description: str
    handled: bool
    tested: bool


@dataclass(frozen=True)
class FailureCoverage:
    """The scenario-based failure coverage of one artifact."""

    scenarios: tuple[FailureScenario, ...]
    identified: int
    handled: int
    tested: int

    @property
    def coverage(self) -> float:
        return self.handled / self.identified if self.identified else 0.0


@dataclass(frozen=True)
class EvolvabilityResult:
    """Evolvability under controlled semantic mutation.

    ``evolution_cost`` is the mean fraction of the semantic surface a
    single-gene mutation touches (the simulated controlled mutation);
    ``abstraction_justified`` is the complexity-side gate that conjoins the
    cost gate — an abstraction expressing semantics the artifact does not
    realize fails even when the simulated mutation is cheap.
    """

    evolution_cost: float
    complexity: Mapping[str, Any]
    abstraction_justified: bool
    justified_ratio: float
    evolvable_under: bool


@dataclass(frozen=True)
class DimensionResult:
    """One gradable dimension's result, bound to its chain evidence."""

    dimension: EngineeringDimension
    meets: bool
    findings: tuple[Finding, ...]
    evidence_refs: tuple[str, ...] = ()
    insufficient_evidence: bool = False
    summary: str = ""
    coverage: Any = None


@dataclass(frozen=True)
class CriticalViolation:
    """A CRITICAL violation. Any one is structurally dispositive.
    ``obligation_id`` names the conformance obligation when the violation
    comes from the dispositive conformance check."""

    dimension: EngineeringDimension
    severity: FindingSeverity
    description: str
    obligation_id: str | None = None


@dataclass(frozen=True)
class EngineeringCertificate:
    """The immutable, evidence-bound certificate.

    ``content_hash`` commits to every content field except itself and the
    chain event ref; ``evidence_refs`` are the dimension event refs and
    ``certificate_event_ref`` is the certificate's own chain anchor.
    """

    certificate_id: str
    system_id: str
    generation_id: str
    isr_ref: str
    architecture_ref: str
    verdict: EngineeringVerdict
    isr_conformance: ISRConformanceResult
    dimensions: tuple[DimensionResult, ...]
    critical_violations: tuple[CriticalViolation, ...]
    evidence_refs: tuple[str, ...]
    content_hash: str
    certificate_event_ref: str

    def content(self) -> dict[str, Any]:
        data = {
            "certificate_id": self.certificate_id,
            "system_id": self.system_id,
            "generation_id": self.generation_id,
            "isr_ref": self.isr_ref,
            "architecture_ref": self.architecture_ref,
            "verdict": self.verdict.value,
            "isr_conformance": {
                "obligations": [o.obligation_id for o in self.isr_conformance.obligations],
                "enforced": list(self.isr_conformance.enforced),
                "violations": [
                    {"obligation_id": v.obligation_id, "severity": v.severity.value, "description": v.description}
                    for v in self.isr_conformance.violations
                ],
                "source_bound": self.isr_conformance.source_bound,
                "all_mandatory_enforced": self.isr_conformance.all_mandatory_enforced,
                "advisory_notes": list(self.isr_conformance.advisory_notes),
            },
            "dimensions": [
                {
                    "dimension": d.dimension.value,
                    "meets": d.meets,
                    "findings": [{"severity": f.severity.value, "description": f.description} for f in d.findings],
                    "insufficient_evidence": d.insufficient_evidence,
                }
                for d in self.dimensions
            ],
            "critical_violations": [
                {"dimension": v.dimension.value, "severity": v.severity.value, "description": v.description}
                for v in self.critical_violations
            ],
            "evidence_refs": list(self.evidence_refs),
        }
        return data


@dataclass(frozen=True)
class Weakness:
    """One diagnosed weakness. ``mutation_kind`` is the declared mutation
    mapping; None means no declared mapping exists (carried, never
    papered over)."""

    weakness_id: str
    dimension: EngineeringDimension
    description: str
    mutation_kind: str | None


@dataclass(frozen=True)
class QualityEvolutionResult:
    """The evolutionary quality loop's outcome."""

    current_isr: Any
    certificate: EngineeringCertificate
    generation: int
    improved: bool
    lineage: tuple[tuple[int, EngineeringCertificate], ...] = ()


# ---------------------------------------------------------------------------
# ISR obligation extraction (from EXISTING carriers — never invented)
# ---------------------------------------------------------------------------

# carrier kind -> the 12-semantic capability id the carrier belongs to
_KIND_SEMANTIC_GROUP: Mapping[str, str] = {
    "requirement": "requirements_acceptance_traceability",
    "acceptance_criterion": "requirements_acceptance_traceability",
    "boundary": "architecture_boundaries",
    "reliability": "reliability_resilience",
    "deployment": "deployment_rollout_rollback",
    "migration": "data_migrations",
    "temporal": "temporal_semantics",
    "testing_anchor": "testing_anchoring",
    "documentation": "documentation",
    "evolution_objective": "evolution_objectives_protected_regions",
    "evolution_policy": "evolution_objectives_protected_regions",
    "protected_region": "evolution_objectives_protected_regions",
}

_ADVISORY_KINDS: frozenset[str] = frozenset(
    {"documentation", "evolution_objective", "evolution_policy"}
)


def _obligation(kind: str, carrier_id: str, carrier: Any, description: str) -> ISRObligation:
    return ISRObligation(
        obligation_id=f"{kind}:{carrier_id}",
        kind=kind,
        semantic_group=_KIND_SEMANTIC_GROUP[kind],
        canonical_form=canonical_form(carrier),
        mandatory=kind not in _ADVISORY_KINDS,
        description=description,
    )


def extract_isr_obligations(isr: Any) -> tuple[ISRObligation, ...]:
    """Extract every obligation the ISR declares, from its existing
    carriers: requirements + acceptance criteria, architectural boundaries
    (with their crossing/preservation invariants), reliability requirements
    (failure modes, recovery objectives, preservation invariants), data
    migrations (rollback invariants, postconditions), deployment intents
    (rollout strategy, rollback invariants), temporal constraints, testing
    anchors, protected regions (the J decisions), and the advisory
    documentation / evolution objective / evolution policy carriers."""
    system = isr.system
    obligations: list[ISRObligation] = []

    for req in system.requirements:
        obligations.append(
            _obligation(
                "requirement",
                req.requirement_id,
                req,
                f"requirement {req.requirement_id}: {req.statement}",
            )
        )
    for criterion in system.acceptance_criteria:
        obligations.append(
            _obligation(
                "acceptance_criterion",
                criterion.criterion_id,
                criterion,
                f"acceptance criterion {criterion.criterion_id}: {criterion.obligation}",
            )
        )
    for boundary in system.architectural_boundaries:
        obligations.append(
            _obligation(
                "boundary",
                boundary.boundary_id,
                boundary,
                f"architectural boundary {boundary.boundary_id}: "
                f"crossing invariants {boundary.crossing_invariants}",
            )
        )
    for rr in system.reliability_requirements:
        obligations.append(
            _obligation(
                "reliability",
                rr.requirement_id,
                rr,
                f"reliability requirement {rr.requirement_id}: failure modes "
                f"{[f.value for f in rr.failure_modes]}, preservation "
                f"invariants {rr.preservation_invariants}",
            )
        )
    for dep in system.deployment_intents:
        obligations.append(
            _obligation(
                "deployment",
                dep.deployment_id,
                dep,
                f"deployment intent {dep.deployment_id}: rollout "
                f"{dep.rollout_strategy.value}, rollback invariants "
                f"{dep.rollback_invariants}",
            )
        )
    for region in system.protected_regions:
        obligations.append(
            _obligation(
                "protected_region",
                region.region_id,
                region,
                f"protected region {region.region_id}: protection "
                f"{region.protection_kind.value} over {region.subject_refs}",
            )
        )
    for anchor in system.testing_anchors:
        obligations.append(
            _obligation(
                "testing_anchor",
                anchor.anchor_id,
                anchor,
                f"testing anchor {anchor.anchor_id}: obligation refs "
                f"{anchor.obligation_refs}",
            )
        )
    for doc in system.documentation_intents:
        obligations.append(
            _obligation(
                "documentation",
                doc.documentation_id,
                doc,
                f"documentation intent {doc.documentation_id}: obligations "
                f"{doc.obligations}",
            )
        )
    for objective in system.evolution_objectives:
        obligations.append(
            _obligation(
                "evolution_objective",
                objective.objective_id,
                objective,
                f"evolution objective {objective.objective_id}: "
                f"{objective.dimension.value} {objective.direction.value}",
            )
        )
    for policy in system.evolution_policies:
        obligations.append(
            _obligation(
                "evolution_policy",
                policy.policy_id,
                policy,
                f"evolution policy {policy.policy_id}: objective refs "
                f"{policy.objective_refs}",
            )
        )
    for module in system.modules:
        for migration in module.data_migrations:
            obligations.append(
                _obligation(
                    "migration",
                    migration.migration_id,
                    migration,
                    f"data migration {migration.migration_id}: rollback "
                    f"invariants {migration.rollback_invariants}, "
                    f"postconditions {migration.postconditions}",
                )
            )
        for constraint in module.temporal_constraints:
            obligations.append(
                _obligation(
                    "temporal",
                    f"{constraint.kind.value}:{constraint.target_ref}",
                    constraint,
                    f"temporal constraint {constraint.kind.value} on "
                    f"{constraint.target_ref} (duration_ms="
                    f"{constraint.duration_ms})",
                )
            )
    return tuple(sorted(obligations, key=lambda o: (o.kind, o.obligation_id)))


def locate_enforcement_evidence(
    obligation: ISRObligation, artifact: Mapping[str, Any]
) -> tuple[Any, ...]:
    """The ledger-addressable enforcement evidence for one obligation:
    the declared coverage item, the projection content address, the source
    binding, and every bundle file whose content references the carrier's
    identity."""
    evidence: list[Any] = []
    coverage = artifact.get("coverage") or ()
    for item in coverage:
        if item.get("capability_id") == obligation.kind:
            evidence.append(("coverage", obligation.kind, item.get("support")))
    projection = artifact.get("projection")
    if projection is not None:
        if obligation.kind == "protected_region":
            evidence.append(("projection.protected_regions", obligation.obligation_id))
        else:
            evidence.append(("projection.constraints", obligation.kind, obligation.obligation_id))
    semantic_source = artifact.get("semantic_source") or {}
    if semantic_source.get("isr_hash"):
        evidence.append(("semantic_source.isr_hash", semantic_source["isr_hash"][:12]))
    for path, content in _bundle_files(artifact):
        if obligation.obligation_id.split(":", 1)[-1] in content:
            evidence.append(("bundle", path))
    return tuple(evidence)


# ---------------------------------------------------------------------------
# bundle introspection (deterministic, no external tools)
# ---------------------------------------------------------------------------


def _bundle_files(artifact: Mapping[str, Any]) -> list[tuple[str, str]]:
    bundle = artifact.get("bundle") or {}
    files: list[tuple[str, str]] = []
    for manifest in bundle.get("manifests") or ():
        for path, content in (manifest.get("files") or {}).items():
            files.append((str(path), str(content)))
    return files


_IMPORT_RE = re.compile(
    r"^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_.]*)", re.MULTILINE
)


def _import_targets(content: str) -> list[str]:
    return [m.group(1) for m in _IMPORT_RE.finditer(content)]


def _module_of(path: str) -> str:
    parts = path.split("/")
    if len(parts) >= 2 and parts[0] in ("app", "tests", "generated"):
        return f"{parts[0]}/{parts[1]}"
    return parts[0]


def _strip_docstrings(content: str) -> str:
    return re.sub(r'""".*?"""', "", content, flags=re.S)


def _is_stub_file(content: str) -> bool:
    """A file is a stub when every one of its def/class blocks has only
    empty bodies (pass / ellipsis / bare or empty returns)."""
    body = _strip_docstrings(content)
    blocks = re.split(r"^\s*(?:class|def)\s+", body, flags=re.M)
    if len(blocks) < 2:
        return False
    block_bodies = blocks[1:]
    stub_blocks = 0
    for block in block_bodies:
        statements = [
            line.strip()
            for line in block.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if not statements:
            continue
        if any(s in ("pass", "...") for s in statements):
            stub_blocks += 1
        elif all(s in ("pass", "...", "return", "return []", "return None") for s in statements):
            stub_blocks += 1
    return stub_blocks == len(block_bodies) and stub_blocks >= 1


def _module_graph(files: Sequence[tuple[str, str]]) -> ArchitectureGraph:
    nodes = sorted({_module_of(path) for path, _ in files})
    edges: list[tuple[str, str, str]] = []
    for path, content in files:
        src = _module_of(path)
        for dotted in _import_targets(content):
            segments = dotted.split(".")
            if len(segments) >= 2 and segments[0] in ("app", "tests", "generated"):
                target = f"{segments[0]}/{segments[1]}"
                if target != src and target in nodes:
                    edges.append((src, path, target))
    adjacency: dict[str, set[str]] = {node: set() for node in nodes}
    for src, _, target in edges:
        adjacency[src].add(target)
    cycles: list[tuple[str, ...]] = []
    for node in nodes:
        path_stack: list[str] = []
        seen: set[str] = set()

        def _visit(current: str) -> None:
            if current in path_stack:
                loop = path_stack[path_stack.index(current):]
                if loop and loop[0] == current and tuple(loop) not in cycles:
                    cycles.append(tuple(loop))
                return
            if current in seen:
                return
            seen.add(current)
            path_stack.append(current)
            for next_node in sorted(adjacency[current]):
                _visit(next_node)
            path_stack.pop()

        _visit(node)
    inbound: dict[str, int] = {node: 0 for node in nodes}
    for _, _, target in edges:
        inbound[target] += 1
    isolated = tuple(
        sorted(node for node in nodes if inbound[node] == 0 and node != "tests")
    )
    return ArchitectureGraph(
        modules=tuple(nodes),
        files=tuple(sorted(path for path, _ in files)),
        edges=tuple(sorted(edges)),
        cycles=tuple(sorted(cycles)),
        isolated=isolated,
    )


# the hexagonal layering rule the ARCHITECTURE gate enforces: the api layer
# may consume application + core; application and infrastructure may consume
# domain + core; nothing internal may consume api or infrastructure.
_FORBIDDEN_EDGES: frozenset[tuple[str, str]] = frozenset(
    {
        ("app/domain", "app/api"),
        ("app/domain", "app/application"),
        ("app/domain", "app/infrastructure"),
        ("app/domain", "app/core"),
        ("app/application", "app/api"),
        ("app/application", "app/infrastructure"),
        ("app/infrastructure", "app/api"),
        ("app/infrastructure", "app/application"),
        ("app/infrastructure", "app/core"),
        ("app/core", "app/api"),
        ("app/core", "app/application"),
        ("app/core", "app/infrastructure"),
        ("app/core", "app/domain"),
        ("app/api", "app/infrastructure"),
    }
)


# ---------------------------------------------------------------------------
# ISR conformance (dispositive)
# ---------------------------------------------------------------------------


class ISRConformanceCheck:
    """Check the artifact against the ISR: source binding first, then every
    obligation's declared coverage and content-level enforcement."""

    def check(self, artifact: Mapping[str, Any], isr: Any) -> ISRConformanceResult:
        obligations = extract_isr_obligations(isr)
        expected = semantic_content_hash(isr)
        bound = (
            (artifact.get("semantic_source") or {}).get("isr_hash") == expected
        )
        coverage: Mapping[str, str] = {
            item.get("capability_id"): item.get("support")
            for item in (artifact.get("coverage") or ())
        }
        projection = artifact.get("projection")
        projection_constraints: dict[str, set[str]] = {}
        projection_regions: set[str] = set()
        if projection is not None:
            for constraint in projection.get("constraints") or ():
                projection_constraints.setdefault(
                    constraint.get("kind"), set()
                ).add(canonicalize(constraint.get("content")))
            projection_regions = {
                canonicalize(region)
                for region in projection.get("protected_regions") or ()
            }

        enforced: list[str] = []
        findings: list[ConformanceFinding] = []
        for obligation in obligations:
            evidence = locate_enforcement_evidence(obligation, artifact)
            severity = (
                FindingSeverity.CRITICAL
                if obligation.mandatory
                else FindingSeverity.ADVISORY
            )
            if not bound:
                findings.append(
                    ConformanceFinding(
                        obligation.obligation_id,
                        severity,
                        "artifact source diverges from the certified ISR — "
                        "the artifact was not produced by this ISR",
                        evidence,
                    )
                )
                continue
            support = coverage.get(obligation.kind, "UNSUPPORTED")
            if support == "SUPPORTED":
                if projection is not None:
                    if obligation.kind == "protected_region":
                        present = canonicalize(obligation.canonical_form) in projection_regions
                    else:
                        present = canonicalize(
                            obligation.canonical_form
                        ) in projection_constraints.get(obligation.kind, set())
                    if present:
                        enforced.append(obligation.obligation_id)
                    else:
                        findings.append(
                            ConformanceFinding(
                                obligation.obligation_id,
                                severity,
                                "declared supported but the obligation's "
                                "content is absent from the artifact's "
                                "projection",
                                evidence,
                            )
                        )
                else:
                    enforced.append(obligation.obligation_id)
            elif support == "PARTIALLY_SUPPORTED":
                findings.append(
                    ConformanceFinding(
                        obligation.obligation_id,
                        severity,
                        "declared partial — enforcement of a mandatory "
                        "obligation is incomplete",
                        evidence,
                    )
                )
            else:
                findings.append(
                    ConformanceFinding(
                        obligation.obligation_id,
                        severity,
                        "declared unsupported — the artifact claims no "
                        "enforcement for this obligation",
                        evidence,
                    )
                )
        advisory_notes: list[str] = []
        if not obligations:
            advisory_notes.append(
                "the certified ISR declares no obligations — conformance "
                "passes vacuously and the certificate names that vacuity"
            )
        elif bound and not any(
            f.severity is FindingSeverity.CRITICAL for f in findings
        ):
            advisory_notes.append("every mandatory obligation is enforced")
        return ISRConformanceResult(
            obligations=obligations,
            enforced=tuple(enforced),
            violations=tuple(findings),
            source_bound=bound,
            all_mandatory_enforced=all(
                obligation.obligation_id in enforced
                for obligation in obligations
                if obligation.mandatory
            ),
            advisory_notes=tuple(advisory_notes),
        )


# ---------------------------------------------------------------------------
# the built-in dimension analyzers (deterministic, plug-in shaped)
# ---------------------------------------------------------------------------


def _insufficient(
    dimension: EngineeringDimension, note: str
) -> DimensionResult:
    return DimensionResult(
        dimension=dimension,
        meets=True,
        findings=(
            Finding(
                FindingSeverity.ADVISORY,
                "insufficient evidence: " + note,
            ),
        ),
        insufficient_evidence=True,
        summary="no executable surface carried — evidence limited to the "
        "declared semantic projection and coverage",
    )


class ImplementationAnalyzer:
    """IMPLEMENTATION: the bundle's real wired surface."""

    dimension = EngineeringDimension.IMPLEMENTATION

    def analyze(self, artifact: Mapping[str, Any], isr: Any) -> DimensionResult:
        files = _bundle_files(artifact)
        if not files:
            return _insufficient(
                self.dimension,
                "the artifact carries no executable surface (bundle files)",
            )
        findings: list[Finding] = []
        stub_files = [
            path for path, content in files if _is_stub_file(content)
        ]
        dead_files = [
            path
            for path, _ in files
            if path.endswith(".py") and not path.startswith("tests/")
            and not any(
                _module_of(path) in _import_targets(content)
                or path.split("/")[-1].replace(".py", "") in _import_targets(content)
                for _, content in files
            )
        ]
        registry = [
            path
            for path, _ in files
            if path.endswith("routers.py") and "api" in path
        ]
        router_files = [
            path for path, _ in files if re.search(r"routers/[^/]+\.py$", path)
        ]
        if registry and router_files:
            registry_content = dict(files).get(registry[0], "")
            if "pass" in registry_content and not re.search(
                r"from app\.api\.routers", registry_content
            ):
                findings.append(
                    Finding(
                        FindingSeverity.MAJOR,
                        f"generated API surface not wired: the router "
                        f"registry {registry[0]} is a stub while "
                        f"{len(router_files)} router file(s) exist",
                    )
                )
        stub_ratio = len(stub_files) / len(files) if files else 0.0
        if stub_ratio >= 0.5:
            findings.append(
                Finding(
                    FindingSeverity.MAJOR,
                    f"stub-majority surface: {len(stub_files)} of "
                    f"{len(files)} units are empty bodies",
                )
            )
        elif stub_files:
            findings.append(
                Finding(
                    FindingSeverity.MINOR,
                    f"{len(stub_files)} of {len(files)} units are stub "
                    f"bodies",
                )
            )
        dead_ratio = len(dead_files) / len(files) if files else 0.0
        if dead_ratio >= 0.3:
            findings.append(
                Finding(
                    FindingSeverity.MAJOR,
                    f"dead-code ratio {dead_ratio:.2f}: {len(dead_files)} "
                    f"of {len(files)} units are never referenced",
                )
            )
        elif dead_files:
            findings.append(
                Finding(
                    FindingSeverity.MINOR,
                    f"unreferenced units: {sorted(dead_files)}",
                )
            )
        test_files = [
            path
            for path, content in files
            if path.startswith("tests/") and path.endswith(".py")
        ]
        if test_files and not any(
            "assert" in content for path, content in files if path in test_files
        ):
            findings.append(
                Finding(
                    FindingSeverity.MINOR,
                    "test surface carries no assertions",
                )
            )
        summary = (
            f"{len(files)} units analyzed; {len(stub_files)} stub, "
            f"{len(dead_files)} unreferenced"
        )
        return DimensionResult(
            dimension=self.dimension,
            meets=_meets_from_findings(findings),
            findings=tuple(findings),
            summary=summary,
        )


class ArchitectureAnalyzer:
    """ARCHITECTURE: the bundle's module graph against the declared
    hexagonal layering, plus the ISR's declared boundaries."""

    dimension = EngineeringDimension.ARCHITECTURE

    def analyze(self, artifact: Mapping[str, Any], isr: Any) -> DimensionResult:
        files = _bundle_files(artifact)
        if not files:
            return _insufficient(
                self.dimension,
                "the artifact carries no module surface",
            )
        graph = _module_graph(files)
        findings: list[Finding] = []
        if graph.cycles:
            findings.append(
                Finding(
                    FindingSeverity.CRITICAL,
                    f"circular module dependencies: {list(graph.cycles)}",
                )
            )
        violations = [
            (src, target)
            for src, _, target in graph.edges
            if (src, target) in _FORBIDDEN_EDGES
        ]
        if violations:
            findings.append(
                Finding(
                    FindingSeverity.MAJOR,
                    f"layer violations: {sorted(violations)}",
                )
            )
        for module in graph.isolated:
            findings.append(
                Finding(
                    FindingSeverity.MINOR,
                    f"isolated layer: {module} has no inbound references",
                )
            )
        for boundary in isr.system.architectural_boundaries:
            if boundary.forbidden_dependency_refs:
                forbidden = set(boundary.forbidden_dependency_refs)
                crossed = [
                    target
                    for _, _, target in graph.edges
                    if any(ref in target for ref in forbidden)
                ]
                if crossed:
                    findings.append(
                        Finding(
                            FindingSeverity.MAJOR,
                            f"ISR boundary {boundary.boundary_id} crossed: "
                            f"{sorted(crossed)}",
                        )
                    )
        if not graph.cycles and not violations and not graph.isolated:
            findings.append(
                Finding(
                    FindingSeverity.ADVISORY,
                    "module graph is acyclic and respects the declared "
                    "hexagonal layering",
                )
            )
        summary = (
            f"{len(graph.modules)} modules, {len(graph.edges)} edges; "
            f"cycles={len(graph.cycles)}, violations={len(violations)}"
        )
        return DimensionResult(
            dimension=self.dimension,
            meets=_meets_from_findings(findings),
            findings=tuple(findings),
            summary=summary,
            coverage=graph,
        )


class DesignAnalyzer:
    """DESIGN: dead-code ratio, stub ratio, and naming over the bundle."""

    dimension = EngineeringDimension.DESIGN

    def analyze(self, artifact: Mapping[str, Any], isr: Any) -> DimensionResult:
        files = _bundle_files(artifact)
        if not files:
            return _insufficient(
                self.dimension,
                "the artifact carries no executable surface",
            )
        findings: list[Finding] = []
        stub_files = [
            path for path, content in files if _is_stub_file(content)
        ]
        stub_ratio = len(stub_files) / len(files) if files else 0.0
        if stub_ratio >= 0.5:
            findings.append(
                Finding(
                    FindingSeverity.MAJOR,
                    f"stub-majority design: {len(stub_files)} of "
                    f"{len(files)} units are empty bodies",
                )
            )
        elif stub_files:
            findings.append(
                Finding(
                    FindingSeverity.MINOR,
                    f"stub units: {sorted(stub_files)}",
                )
            )
        dead = [
            path
            for path, _ in files
            if path.endswith(".py") and not path.startswith("tests/")
            and not any(
                _module_of(path) in _import_targets(content)
                or path.split("/")[-1].replace(".py", "") in _import_targets(content)
                for _, content in files
            )
        ]
        dead_ratio = len(dead) / len(files) if files else 0.0
        if dead_ratio >= 0.3:
            findings.append(
                Finding(
                    FindingSeverity.MAJOR,
                    f"dead-code ratio {dead_ratio:.2f}: {sorted(dead)}",
                )
            )
        elif dead:
            findings.append(
                Finding(
                    FindingSeverity.MINOR,
                    f"unreferenced units: {sorted(dead)}",
                )
            )
        non_snake = [
            path
            for path, _ in files
            if path.endswith(".py")
            and any(ch.isupper() for ch in path.split("/")[-1])
        ]
        if non_snake:
            findings.append(
                Finding(
                    FindingSeverity.MINOR,
                    f"non-snake_case unit names: {sorted(non_snake)}",
                )
            )
        if not findings:
            findings.append(
                Finding(
                    FindingSeverity.ADVISORY,
                    "no design findings on the carried surface",
                )
            )
        summary = (
            f"stub ratio {stub_ratio:.2f}, dead-code ratio {dead_ratio:.2f}"
        )
        return DimensionResult(
            dimension=self.dimension,
            meets=_meets_from_findings(findings),
            findings=tuple(findings),
            summary=summary,
        )


_RECOVERY_MARKER_RE = re.compile(
    r"(retry|backoff|circuit|rollback|downgrade|health|recover)",
    re.IGNORECASE,
)


class FailureEngineeringAnalyzer:
    """FAILURE_ENGINEERING: scenario-based coverage of the ISR's declared
    failure semantics (reliability recovery objectives, migration and
    deployment rollback invariants)."""

    dimension = EngineeringDimension.FAILURE_ENGINEERING

    def analyze(self, artifact: Mapping[str, Any], isr: Any) -> DimensionResult:
        system = isr.system
        scenarios: list[FailureScenario] = []
        for rr in system.reliability_requirements:
            for objective in rr.recovery_objectives:
                scenarios.append(
                    FailureScenario(
                        scenario_id=f"{rr.requirement_id}:{objective.failure_mode.value}",
                        source_kind="reliability",
                        description=(
                            f"{rr.requirement_id}: {objective.failure_mode.value} "
                            f"recovers via {objective.required_behavior.value} "
                            f"within {objective.max_recovery_duration_ms}ms"
                        ),
                        handled=self._handled(
                            artifact, "reliability"
                        ),
                        tested=self._tested(
                            system, (rr.requirement_id,)
                        ),
                    )
                )
        for module in system.modules:
            for migration in module.data_migrations:
                scenarios.append(
                    FailureScenario(
                        scenario_id=migration.migration_id,
                        source_kind="migration",
                        description=(
                            f"migration {migration.migration_id}: rollback "
                            f"invariants {migration.rollback_invariants}"
                        ),
                        handled=self._handled(
                            artifact, "migration"
                        ),
                        tested=self._tested(
                            system, (migration.migration_id,)
                        ),
                    )
                )
        for dep in system.deployment_intents:
            scenarios.append(
                FailureScenario(
                    scenario_id=dep.deployment_id,
                    source_kind="deployment",
                    description=(
                        f"deployment {dep.deployment_id}: rollback invariants "
                        f"{dep.rollback_invariants}"
                    ),
handled=self._handled(
                            artifact, "deployment"
                        ),
                    tested=self._tested(system, (dep.deployment_id,)),
                )
            )
        findings: list[Finding] = []
        for scenario in scenarios:
            if not scenario.handled:
                findings.append(
                    Finding(
                        FindingSeverity.CRITICAL,
                        f"mandatory failure scenario unhandled: "
                        f"{scenario.description}",
                    )
                )
            elif not scenario.tested:
                findings.append(
                    Finding(
                        FindingSeverity.ADVISORY,
                        f"scenario not directly test-anchored: "
                        f"{scenario.description}",
                    )
                )
        if not scenarios:
            findings.append(
                Finding(
                    FindingSeverity.MAJOR,
                    "no failure scenarios declared — certification demands "
                    "declared failure semantics, never a vacuous pass",
                )
            )
        coverage = FailureCoverage(
            scenarios=tuple(scenarios),
            identified=len(scenarios),
            handled=sum(1 for s in scenarios if s.handled),
            tested=sum(1 for s in scenarios if s.tested),
        )
        summary = (
            f"{coverage.identified} scenario(s); {coverage.handled} handled, "
            f"{coverage.tested} test-anchored"
        )
        return DimensionResult(
            dimension=self.dimension,
            meets=_meets_from_findings(findings),
            findings=tuple(findings),
            summary=summary,
            coverage=coverage,
        )

    @staticmethod
    def _handled(
        artifact: Mapping[str, Any], kind: str
    ) -> bool:
        projection = artifact.get("projection")
        if projection is not None:
            return any(
                constraint.get("kind") == kind
                for constraint in projection.get("constraints") or ()
            )
        coverage = {
            item.get("capability_id"): item.get("support")
            for item in (artifact.get("coverage") or ())
        }
        if coverage.get(kind) != "SUPPORTED":
            return False
        bundle_text = "\n".join(
            content for _, content in _bundle_files(artifact)
        )
        return bool(_RECOVERY_MARKER_RE.search(bundle_text))

    @staticmethod
    def _tested(system: Any, carrier_ids: tuple[str, ...]) -> bool:
        for anchor in system.testing_anchors:
            refs = set(anchor.obligation_refs) | set(anchor.subject_refs)
            if refs & set(carrier_ids):
                return True
        return False


_SECRET_PATTERN = re.compile(
    r"""([A-Za-z0-9_]*?(?:secret|password|api[_-]?key|token|private[_-]?key|credential))\s*[:=]\s*["']([^"']{6,})["']""",
    re.IGNORECASE,
)


class SecurityAnalyzer:
    """SECURITY: credential literals, CORS posture, auth surface, and
    container hardening over the bundle's real content."""

    dimension = EngineeringDimension.SECURITY

    def analyze(self, artifact: Mapping[str, Any], isr: Any) -> DimensionResult:
        files = _bundle_files(artifact)
        if not files:
            return _insufficient(
                self.dimension,
                "no executable surface carried — no credential or CORS "
                "surface to analyze"
            )
        findings: list[Finding] = []
        bundle_text = "\n".join(content for _, content in files)
        leaked: list[str] = []
        for match in _SECRET_PATTERN.finditer(bundle_text):
            value = match.group(2)
            if any(
                marker in value
                for marker in ("os.environ", "getenv", "${", "changeme", "your-", "example")
            ):
                continue
            leaked.append(f"{match.group(1)}={value[:6]}…")
        if leaked:
            findings.append(
                Finding(
                    FindingSeverity.CRITICAL,
                    f"hardcoded credential(s) in source: {sorted(set(leaked))}",
                )
            )
        cors_wildcard = bool(
            re.search(r"allow_origins\s*=\s*\[\s*\"\*\"\s*\]", bundle_text)
        )
        credentials_flagged = bool(
            re.search(r"allow_credentials\s*=\s*True", bundle_text)
        )
        auth_surface = "OAuth2PasswordBearer" in bundle_text
        if cors_wildcard and credentials_flagged:
            if auth_surface:
                findings.append(
                    Finding(
                        FindingSeverity.CRITICAL,
                        "wildcard CORS combined with allow_credentials and "
                        "an OAuth bearer surface — credentialed cross-origin "
                        "exposure",
                    )
                )
            else:
                findings.append(
                    Finding(
                        FindingSeverity.MAJOR,
                        "wildcard CORS combined with allow_credentials — "
                        "hardening debt",
                    )
                )
        if auth_surface:
            findings.append(
                Finding(
                    FindingSeverity.ADVISORY,
                    "auth surface present (OAuth2 bearer)",
                )
            )
        dockerfile = dict(files).get("Dockerfile", "")
        if dockerfile and not re.search(r"^\s*USER\s", dockerfile, re.MULTILINE):
            findings.append(
                Finding(
                    FindingSeverity.MINOR,
                    "container image runs as root (no USER directive)",
                )
            )
        if not findings:
            findings.append(
                Finding(
                    FindingSeverity.ADVISORY,
                    "no security findings on the carried surface",
                )
            )
        summary = (
            "credential literals: "
            f"{len(leaked)}; wildcard CORS: {cors_wildcard}; "
            f"credentialed: {cors_wildcard and credentials_flagged}"
        )
        return DimensionResult(
            dimension=self.dimension,
            meets=_meets_from_findings(findings),
            findings=tuple(findings),
            summary=summary,
        )


def _token_set(content: Any) -> set[str]:
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", canonicalize(content)))


def _entanglement_cost(constraints: Sequence[tuple[str, Any]]) -> float:
    """The mean fraction of the semantic surface a single-gene controlled
    mutation touches: for each constraint, the share of OTHER constraints
    whose canonical content references its IDENTITY tokens. Tokens shared
    across most of the surface are vocabulary, not coupling, and are
    removed before measuring."""
    if not constraints:
        return 0.0
    token_sets = [_token_set(form) for _, form in constraints]
    counts: dict[str, int] = {}
    for tokens in token_sets:
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
    shared = {
        token
        for token, frequency in counts.items()
        if frequency >= len(constraints) * 0.8
    }
    identity_sets = [tokens - shared for tokens in token_sets]
    total = len(constraints)
    impacts: list[float] = []
    for i, tokens in enumerate(identity_sets):
        if not tokens:
            impacts.append(0.0)
            continue
        affected = sum(
            1
            for j, other in enumerate(identity_sets)
            if j != i and (tokens & other)
        )
        impacts.append(affected / total)
    return sum(impacts) / total


class EvolvabilityAnalyzer:
    """EVOLVABILITY: the simulated controlled mutation (cost), the
    complexity gate, and the abstraction-justified gate — the complexity
    gate CONJOINS the cost gate so over-abstraction cannot game a cheap
    simulation."""

    dimension = EngineeringDimension.EVOLVABILITY

    def analyze(self, artifact: Mapping[str, Any], isr: Any) -> DimensionResult:
        files = _bundle_files(artifact)
        projection = artifact.get("projection")
        findings: list[Finding] = []
        if projection is not None:
            constraints = [
                (c.get("kind"), c.get("content"))
                for c in projection.get("constraints") or ()
            ]
            cost = _entanglement_cost(constraints)
        else:
            cost = self._coupling_cost(files)
        complexity: dict[str, Any] = {}
        if files:
            max_lines = max(len(content.splitlines()) for _, content in files)
            branch_density = max(
                len(re.findall(r"\b(?:if|for|while)\b", content))
                / max(len(content.splitlines()), 1)
                for _, content in files
            )
            complexity = {"max_lines": max_lines, "max_branch_density": round(branch_density, 3)}
            complexity_ok = max_lines <= 250 and branch_density <= 0.6
            if not complexity_ok:
                findings.append(
                    Finding(
                        FindingSeverity.MAJOR,
                        f"complexity out of calibration: {complexity}",
                    )
                )
        else:
            complexity = {"note": "no executable surface — complexity trivial by absence, named"}
            complexity_ok = True
            findings.append(
                Finding(
                    FindingSeverity.ADVISORY,
                    "no executable surface — complexity evaluated by absence "
                    "of code, named never blurred",
                )
            )
        coverage_items = list(artifact.get("coverage") or ())
        expressed = len(coverage_items)
        supported = sum(
            1
            for item in coverage_items
            if item.get("support") == "SUPPORTED"
        )
        justified_ratio = supported / expressed if expressed else 1.0
        abstraction_justified = justified_ratio >= 0.5
        if expressed and not abstraction_justified:
            findings.append(
                Finding(
                    FindingSeverity.MAJOR,
                    f"abstraction not justified: {supported} of {expressed} "
                    f"expressed semantics realized by this artifact surface — "
                    f"a cheap evolution cost does not certify an unjustified "
                    f"abstraction",
                )
            )
        if cost > 0.5:
            findings.append(
                Finding(
                    FindingSeverity.MAJOR,
                    f"high coupling: a single-gene controlled mutation "
                    f"touches {cost:.2f} of the surface",
                )
            )
        evolvable = cost <= 0.5 and complexity_ok and abstraction_justified
        if not findings:
            findings.append(
                Finding(
                    FindingSeverity.ADVISORY,
                    "evolvable under controlled mutation",
                )
            )
        result = EvolvabilityResult(
            evolution_cost=round(cost, 3),
            complexity=complexity,
            abstraction_justified=abstraction_justified,
            justified_ratio=round(justified_ratio, 3),
            evolvable_under=evolvable,
        )
        summary = (
            f"evolution cost {cost:.3f}; abstraction justified "
            f"{justified_ratio:.2f}"
        )
        return DimensionResult(
            dimension=self.dimension,
            meets=_meets_from_findings(findings),
            findings=tuple(findings),
            summary=summary,
            coverage=result,
        )

    @staticmethod
    def _coupling_cost(files: Sequence[tuple[str, str]]) -> float:
        if not files:
            return 0.0
        edge_counts: list[int] = []
        for path, content in files:
            targets = [
                dotted
                for dotted in _import_targets(content)
                if dotted.split(".")[0] in ("app", "tests", "generated")
            ]
            edge_counts.append(len(targets))
        total = len(files)
        return sum(edge_counts) / (total * total)


class OperationsAnalyzer:
    """OPERATIONS: the declared deployment posture (rollout/rollback) and
    the bundle's operational surface (health, image, logging)."""

    dimension = EngineeringDimension.OPERATIONS

    def analyze(self, artifact: Mapping[str, Any], isr: Any) -> DimensionResult:
        system = isr.system
        files = _bundle_files(artifact)
        findings: list[Finding] = []
        projection = artifact.get("projection")
        deployment_carried = bool(system.deployment_intents) and (
            projection is not None
            or any(
                item.get("support") == "SUPPORTED"
                for item in (artifact.get("coverage") or ())
                if item.get("capability_id") == "deployment"
            )
        )
        if not system.deployment_intents:
            findings.append(
                Finding(
                    FindingSeverity.MAJOR,
                    "no deployment semantics declared — certification "
                    "demands a declared rollout/rollback posture",
                )
            )
        elif not deployment_carried:
            findings.append(
                Finding(
                    FindingSeverity.MAJOR,
                    "declared deployment semantics not realized by the "
                    "artifact surface",
                )
            )
        if files:
            bundle_text = "\n".join(content for _, content in files)
            if "/health" not in bundle_text:
                findings.append(
                    Finding(
                        FindingSeverity.MINOR,
                        "no health endpoint on the carried surface",
                    )
                )
            if "Dockerfile" not in dict(files):
                findings.append(
                    Finding(
                        FindingSeverity.MINOR,
                        "no container image on the carried surface",
                    )
                )
            if "structlog" not in bundle_text and "logging" not in bundle_text:
                findings.append(
                    Finding(
                        FindingSeverity.MINOR,
                        "no structured logging on the carried surface",
                    )
                )
        if not findings:
            findings.append(
                Finding(
                    FindingSeverity.ADVISORY,
                    "deployment posture declared and carried",
                )
            )
        summary = (
            f"deployment intents: {len(system.deployment_intents)}; "
            f"carried: {deployment_carried}"
        )
        return DimensionResult(
            dimension=self.dimension,
            meets=_meets_from_findings(findings),
            findings=tuple(findings),
            summary=summary,
        )


class DimensionAnalyzerRegistry:
    """The plug-in registry: any object with ``for_dimension(dimension)``
    returning an analyzer with ``analyze(artifact, isr)`` is accepted — the
    certifier has no core dependency on the built-ins."""

    def __init__(self, analyzers: Mapping[EngineeringDimension, Any]) -> None:
        self._analyzers = dict(analyzers)

    def for_dimension(self, dimension: EngineeringDimension) -> Any:
        return self._analyzers[dimension]


def default_dimension_analyzers() -> DimensionAnalyzerRegistry:
    analyzers = {
        analyzer.dimension: analyzer()
        for analyzer in (
            ImplementationAnalyzer,
            ArchitectureAnalyzer,
            DesignAnalyzer,
            FailureEngineeringAnalyzer,
            SecurityAnalyzer,
            EvolvabilityAnalyzer,
            OperationsAnalyzer,
        )
    }
    return DimensionAnalyzerRegistry(analyzers)


# ---------------------------------------------------------------------------
# the certification harness (measurement only)
# ---------------------------------------------------------------------------


class EngineeringCertificationHarness:
    """Certifies one artifact against the ISR that produced it, under the
    declared contract.

    Conformance is dispositive and FIRST: a certificate whose mandatory
    obligations are not enforced is NOT_CERTIFIED before any gradable
    dimension runs. Otherwise the seven gradable dimensions are analyzed
    through the plug-in analyzers and every result is chain-anchored.
    The harness never mutates the ISR or the artifact.
    """

    def __init__(
        self,
        contract: EngineeringQualityContract | None = None,
        analyzers: Any = None,
        ledger: EvolutionLedger | None = None,
        *,
        certificate_prefix: str = "eng-cert",
        evolution_id: str = "r2.10.32",
    ) -> None:
        self.contract = contract or default_engineering_contract()
        self.analyzers = analyzers or default_dimension_analyzers()
        self.ledger = ledger or EvolutionLedger()
        self._certificate_prefix = certificate_prefix
        self._evolution_id = evolution_id
        self._conformance = ISRConformanceCheck()

    # -- the certificate -----------------------------------------------------

    def certify(
        self, artifact: Mapping[str, Any], isr: Any, *, generation_id: str = "gen-0"
    ) -> EngineeringCertificate:
        conformance = self._conformance.check(artifact, isr)
        isr_ref = semantic_content_hash(isr)
        architecture_ref = (
            artifact.get("architecture_ref")
            or artifact.get("artifact_hash")
            or hashlib.sha256(canonicalize(artifact).encode("utf-8")).hexdigest()
        )
        system_id = isr.system.id
        if not conformance.all_mandatory_enforced:
            critical_violations = tuple(
                CriticalViolation(
                    EngineeringDimension.ISR_CONFORMANCE,
                    finding.severity,
                    finding.description,
                    finding.obligation_id,
                )
                for finding in conformance.violations
                if finding.severity is FindingSeverity.CRITICAL
            )
            certificate = EngineeringCertificate(
                certificate_id="",
                system_id=system_id,
                generation_id=generation_id,
                isr_ref=isr_ref,
                architecture_ref=architecture_ref,
                verdict=EngineeringVerdict.NOT_CERTIFIED,
                isr_conformance=conformance,
                dimensions=(),
                critical_violations=critical_violations,
                evidence_refs=(),
                content_hash="",
                certificate_event_ref="",
            )
            return self._finalize(certificate)
        dimensions: list[DimensionResult] = []
        for dimension in GRADABLE_DIMENSIONS:
            result = self.analyzers.for_dimension(dimension).analyze(artifact, isr)
            event_ref = self.ledger.record_dimension(
                _DimensionEvidence(
                    dimension=result.dimension,
                    meets=result.meets,
                    findings=result.findings,
                    insufficient_evidence=result.insufficient_evidence,
                    summary=result.summary,
                    isr_ref=isr_ref,
                    architecture_ref=architecture_ref,
                ),
                evolution_id=self._evolution_id,
            )
            dimensions.append(
                dataclasses.replace(result, evidence_refs=(event_ref,))
            )
        verdict = self._render_verdict(dimensions)
        critical_violations = tuple(
            CriticalViolation(
                violation.dimension,
                violation.severity,
                violation.description,
                violation.obligation_id,
            )
            for violation in conformance.violations
            if violation.severity is FindingSeverity.CRITICAL
        ) + tuple(
            CriticalViolation(
                result.dimension, finding.severity, finding.description
            )
            for result in dimensions
            for finding in result.findings
            if finding.severity is FindingSeverity.CRITICAL
        )
        certificate = EngineeringCertificate(
            certificate_id="",
            system_id=system_id,
            generation_id=generation_id,
            isr_ref=isr_ref,
            architecture_ref=architecture_ref,
            verdict=verdict,
            isr_conformance=conformance,
            dimensions=tuple(dimensions),
            critical_violations=critical_violations,
            evidence_refs=tuple(
                ref
                for result in dimensions
                for ref in result.evidence_refs
            ),
            content_hash="",
            certificate_event_ref="",
        )
        return self._finalize(certificate)

    # -- verdict rendering ---------------------------------------------------

    @staticmethod
    def _render_verdict(
        dimensions: Sequence[DimensionResult],
    ) -> EngineeringVerdict:
        if any(
            finding.severity is FindingSeverity.CRITICAL
            for result in dimensions
            for finding in result.findings
        ):
            return EngineeringVerdict.NOT_CERTIFIED
        if all(result.meets for result in dimensions):
            return EngineeringVerdict.CERTIFIED
        return EngineeringVerdict.QUALIFIED_PARTIAL

    # -- finalize: content hash + chain anchor -------------------------------

    def _finalize(self, certificate: EngineeringCertificate) -> EngineeringCertificate:
        certificate_id = (
            f"{self._certificate_prefix}-{certificate.generation_id}-"
            f"{certificate.isr_ref[:8]}-{certificate.architecture_ref[:8]}"
        )
        staged_id = dataclasses.replace(
            certificate, certificate_id=certificate_id
        )
        content_hash = hashlib.sha256(
            canonicalize(staged_id.content()).encode("utf-8")
        ).hexdigest()
        staged = dataclasses.replace(staged_id, content_hash=content_hash)
        event_ref = self.ledger.record_engineering_certification(
            staged, evolution_id=self._evolution_id
        )
        return dataclasses.replace(staged, certificate_event_ref=event_ref)


@dataclass(frozen=True)
class _DimensionEvidence:
    """The duck-typed evidence record the ledger's record_dimension
    consumes (kept here so the ledger never imports this module)."""

    dimension: EngineeringDimension
    meets: bool
    findings: tuple[Finding, ...]
    insufficient_evidence: bool
    summary: str
    isr_ref: str
    architecture_ref: str


# ---------------------------------------------------------------------------
# the evolutionary quality loop (the only remediation surface: ISR mutation)
# ---------------------------------------------------------------------------


class EvolutionaryQualityLoop:
    """generate -> certify -> diagnose -> mutate_architecture -> regenerate
    -> re-certify.

    The loop mutates ONLY the ISR, through the declared mutation operators
    (reliability / deployment / testing-anchor), driven by the diagnosed
    weaknesses with a declared mutation mapping. Weaknesses without a
    mapping (e.g. a backend's declared-unsupported semantics) are carried
    in the diagnosis — the loop never invents remediation. Every
    generation's certificate is chain-anchored.
    """

    # weakness -> declared mutation mapping (the only remediation seam)
    _MUTATION_PLAN: Mapping[str, str] = {
        "failure_scenarios_absent": "add_reliability",
        "deployment_semantics_absent": "add_deployment",
        "scenario_untested": "add_testing_anchor",
    }

    def __init__(
        self,
        certification: EngineeringCertificationHarness,
        compile_artifact: Callable[[Any], Mapping[str, Any]],
        ledger: EvolutionLedger | None = None,
    ) -> None:
        self._certification = certification
        self._compile_artifact = compile_artifact
        self._ledger = ledger or certification.ledger

    def evolve_for_quality(
        self, isr: Any, *, max_generations: int = 5
    ) -> QualityEvolutionResult:
        current = isr
        initial = self._certify_and_record(current, 0)
        lineage: list[tuple[int, EngineeringCertificate]] = [(0, initial)]
        best = initial
        frontier = initial
        if best.verdict is EngineeringVerdict.CERTIFIED:
            return QualityEvolutionResult(
                current_isr=current,
                certificate=best,
                generation=0,
                improved=False,
                lineage=tuple(lineage),
            )
        for generation in range(1, max_generations + 1):
            weaknesses = self._diagnose(frontier)
            actionable = [w for w in weaknesses if w.mutation_kind]
            if not actionable:
                break
            candidate = current
            for weakness in actionable:
                mutated = self._apply(current, weakness)
                if mutated is not None and mutated is not current:
                    candidate = mutated
                    break
            if candidate is current:
                break
            current = candidate
            certificate = self._certify_and_record(current, generation)
            lineage.append((generation, certificate))
            frontier = certificate
            if self._better(certificate, best):
                best = certificate
            if certificate.verdict is EngineeringVerdict.CERTIFIED:
                break
        return QualityEvolutionResult(
            current_isr=current,
            certificate=best,
            generation=len(lineage) - 1,
            improved=self._better(best, initial),
            lineage=tuple(lineage),
        )

    # -- per-generation certify ----------------------------------------------

    def _certify_and_record(self, isr: Any, generation: int) -> EngineeringCertificate:
        artifact = self._compile_artifact(isr)
        return self._certification.certify(
            artifact, isr, generation_id=f"gen-{generation}"
        )

    # -- diagnosis ------------------------------------------------------------

    def _diagnose(self, certificate: EngineeringCertificate) -> tuple[Weakness, ...]:
        weaknesses: list[Weakness] = []
        for result in certificate.dimensions:
            for finding in result.findings:
                weakness_id = self._weakness_id(result, finding)
                mutation_kind = self._MUTATION_PLAN.get(weakness_id)
                weaknesses.append(
                    Weakness(
                        weakness_id=weakness_id,
                        dimension=result.dimension,
                        description=finding.description,
                        mutation_kind=mutation_kind,
                    )
                )
        for violation in certificate.isr_conformance.violations:
            weaknesses.append(
                Weakness(
                    weakness_id=f"conformance:{violation.obligation_id}",
                    dimension=EngineeringDimension.ISR_CONFORMANCE,
                    description=violation.description,
                    mutation_kind=None,
                )
            )
        return tuple(weaknesses)

    @staticmethod
    def _weakness_id(result: DimensionResult, finding: Finding) -> str:
        if (
            result.dimension is EngineeringDimension.FAILURE_ENGINEERING
            and "no failure scenarios declared" in finding.description
        ):
            return "failure_scenarios_absent"
        if (
            result.dimension is EngineeringDimension.FAILURE_ENGINEERING
            and "not directly test-anchored" in finding.description
        ):
            return "scenario_untested"
        if (
            result.dimension is EngineeringDimension.OPERATIONS
            and "no deployment semantics declared" in finding.description
        ):
            return "deployment_semantics_absent"
        return f"{result.dimension.value}:{finding.severity.value}"

    # -- the declared mutation seam -------------------------------------------

    def _apply(self, isr: Any, weakness: Weakness) -> Any | None:
        from ..evolution.deployment_mutation import DeploymentOperator
        from ..evolution.reliability_mutation import ReliabilityOperator
        from ..evolution.testing_anchor_mutation import TestingAnchorOperator

        capability = isr.system.business_capabilities[0]
        try:
            if weakness.mutation_kind == "add_reliability":
                requirement_id = f"{capability.capability_id}-rr-quality"
                if any(
                    requirement.requirement_id == requirement_id
                    for requirement in isr.system.reliability_requirements
                ):
                    return None
                requirement = ReliabilityRequirement(
                    requirement_id=requirement_id,
                    target_refs=(capability.capability_id,),
                    failure_modes=(FailureMode.TRANSIENT_DEPENDENCY_FAILURE,),
                    recovery_objectives=(
                        RecoveryObjective(
                            failure_mode=FailureMode.TRANSIENT_DEPENDENCY_FAILURE,
                            required_behavior=RecoveryBehavior.EVENTUAL_RECOVERY,
                            max_recovery_duration_ms=5000,
                        ),
                    ),
                    degradation_policy=DegradationPolicy.NO_DEGRADATION,
                    preservation_invariants=(
                        f"{capability.capability_id} coherent",
                    ),
                )
                return ReliabilityOperator(self._ledger).add_requirement(
                    isr, requirement
                ).candidate_isr
            if weakness.mutation_kind == "add_deployment":
                deployment_id = f"{capability.capability_id}-dep-quality"
                if any(
                    intent.deployment_id == deployment_id
                    for intent in isr.system.deployment_intents
                ):
                    return None
                intent = DeploymentIntent(
                    deployment_id=deployment_id,
                    target_refs=(capability.capability_id,),
                    rollout_strategy=RolloutStrategy.CANARY,
                    rollback_required=True,
                    rollback_target_ref=capability.capability_id,
                    rollback_invariants=(
                        "the capability's state is preserved",
                    ),
                )
                return DeploymentOperator(self._ledger).add_intent(
                    isr, intent
                ).candidate_isr
            if weakness.mutation_kind == "add_testing_anchor":
                workflow_id = next(
                    (
                        workflow.id
                        for module in isr.system.modules
                        for workflow in module.workflows
                    ),
                    "w1",
                )
                obligation_ref = next(
                    (
                        requirement.requirement_id
                        for requirement in isr.system.reliability_requirements
                    ),
                    capability.capability_id,
                )
                anchor_id = f"{workflow_id}-anchor-quality"
                if any(
                    anchor.anchor_id == anchor_id
                    for anchor in isr.system.testing_anchors
                ):
                    return None
                anchor = TestingAnchor(
                    anchor_id=anchor_id,
                    subject_refs=(workflow_id,),
                    obligation_refs=(obligation_ref,),
                    evidence_requirements=(
                        "the declared obligation must be demonstrable",
                    ),
                    protection_policy=ProtectionPolicy.EVOLVABLE,
                    authority=AnchorAuthority.DERIVED,
                )
                return TestingAnchorOperator(self._ledger).add_anchor(
                    isr, anchor
                ).candidate_isr
        except Exception:
            return None
        return None

    # -- ranking (gates, never scores) -----------------------------------------

    @staticmethod
    def _rank(certificate: EngineeringCertificate) -> tuple[int, int, int, int]:
        verdict_order = {
            EngineeringVerdict.CERTIFIED: 2,
            EngineeringVerdict.QUALIFIED_PARTIAL: 1,
            EngineeringVerdict.NOT_CERTIFIED: 0,
        }
        majors = sum(
            1
            for result in certificate.dimensions
            for finding in result.findings
            if finding.severity is FindingSeverity.MAJOR
        )
        gates_met = sum(1 for result in certificate.dimensions if result.meets)
        return (
            verdict_order[certificate.verdict],
            -len(certificate.critical_violations),
            -majors,
            gates_met,
        )

    def _better(
        self, candidate: EngineeringCertificate, reference: EngineeringCertificate
    ) -> bool:
        return self._rank(candidate) > self._rank(reference)