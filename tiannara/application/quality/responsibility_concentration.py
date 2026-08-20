"""R2.10.32.5 — ResponsibilityConcentrationAnalyzer: the emergent-property dimension.

R2.10.32.1–32.4 established WHAT MUST BE TRUE -> HOW WE PROVE IT: the ISR
declares obligations (decisions, threats) and the traceability engines prove
realization. 32.5 evaluates an EMERGENT architectural property: does the
implementation's responsibility structure violate the architectural quality
contract? That is a genuinely different kind of certification dimension, and
it is deliberately NOT forced into the obligation-carrier pattern:

    * there is NO ResponsibilityObligation carrier. Symmetry with 32.1/32.3
      is sacrificed on purpose — inventing the carrier would be the
      certifier authoring an obligation it then judges against, the same
      contamination in a new costume. Responsibility concentration is not
      something the ISR DECLARES; it is something the implementation
      EXHIBITS. The analyzer derives evidence from the existing ISR
      architecture, module/boundary identity, decision scope, and the
      implementation graph.
    * the output is a FINDING — evidence about the generated artifact. It
      carries evidence refs and concentration signals; it has no
      obligation_id, creates no obligation, and never redefines what the
      architecture was supposed to be.

The anti-gaming rule is the epistemic heart of 32.5: LARGE MODULE != BAD. A
large, coherent module (OrderService: create order, validate order,
calculate totals, apply order rules) is well-engineered; a small module that
owns billing, authentication, email, persistence, analytics, and shipping
is a god-module regardless of line count. The analyzer measures
CONCENTRATION — a structural property of the responsibility graph, never a
metric of volume. The four signals:

    1. multiple_unrelated_responsibility_clusters — responsibilities that
       share no interface and no dependency (structural relatedness, never
       keyword heuristics);
    2. high_dependency_diversity — the module touches more distinct
       dependency groups than DEPENDENCY_DIVERSITY_BOUND;
    3. cross_boundary_ownership — the module is a member of more than one
       E boundary (its responsibilities span ownership domains);
    4. decision_scope_conflict — the module falls in the architectural
       scope of more than one 32.1 decision.

Severity never self-escalates: a finding is CRITICAL only when the ISR
EXPLICITLY prohibits the concentration (the module is named in an E
boundary's forbidden_dependency_refs) — otherwise ADVISORY / WARNING.
Escalating on the analyzer's own judgment would be authoring an obligation
again. The standard boundary pattern applies: the analyzer has no
carrier-module import and no constructor binding — it reads the ISR and
the artifact, and it authors neither.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from typing import Any, Mapping

from tiannara.application.quality.decision_traceability import (
    _verification_event_ref,
)

# a module touching more distinct dependency groups than this is diverse
DEPENDENCY_DIVERSITY_BOUND = 4
# more unrelated responsibility clusters than this escalates to WARNING
SEVERITY_WARNING_BOUND = 3


class ConcentrationSeverity(str, Enum):
    ADVISORY = "ADVISORY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"  # only when the ISR explicitly prohibits the concentration


@dataclass(frozen=True)
class ResponsibilityCluster:
    """A cluster of related responsibilities. Relatedness is derived from
    the module's interface, dependency, and decision-scope structure — not
    from a keyword heuristic."""

    cluster_id: str
    responsibilities: tuple[str, ...]


@dataclass(frozen=True)
class ResponsibilityProfile:
    """The responsibility profile of one module, derived from the existing
    ISR architecture + module/boundary identity + decision scope +
    implementation graph."""

    module_id: str
    responsibility_clusters: tuple[ResponsibilityCluster, ...]
    dependency_clusters: tuple[str, ...]
    scope_refs: tuple[str, ...]  # architectural scopes/decisions applying here


@dataclass(frozen=True)
class ResponsibilityConcentrationFinding:
    """A FINDING — evidence about the generated artifact's responsibility
    structure. It does not redefine what the architecture was supposed to
    be and creates no obligation; it measures what the implementation
    exhibits."""

    module_id: str
    responsibility_clusters: tuple[str, ...]
    dependency_clusters: tuple[str, ...]
    scope_refs: tuple[str, ...]
    concentration_signals: tuple[str, ...]  # which signals fired
    severity: ConcentrationSeverity
    evidence_refs: tuple[str, ...]


# -- the implementation graph (from the artifact's R2.10.7 projection seam) -----

@dataclass(frozen=True)
class ModuleGraphNode:
    """One module as the artifact exhibits it: its interfaces, the
    dependency groups it touches, and its responsibilities — each with the
    interfaces/dependencies that give it affinity (structural relatedness)."""

    module_id: str
    interfaces: tuple[str, ...]
    dependencies: tuple[str, ...]
    responsibilities: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...]


def extract_module_graph(artifact: Mapping[str, Any]) -> tuple[ModuleGraphNode, ...]:
    """Derive the module/dependency structure from the artifact's
    ``modules`` section (the R2.10.7 projection seam): each entry declares
    ``module_id``, ``interfaces``, ``dependencies``, and ``responsibilities``
    (each ``(id, interfaces, dependencies)``). Empty artifact -> empty graph.
    """
    nodes: list[ModuleGraphNode] = []
    for entry in artifact.get("modules") or ():
        nodes.append(
            ModuleGraphNode(
                module_id=entry["module_id"],
                interfaces=tuple(entry.get("interfaces") or ()),
                dependencies=tuple(entry.get("dependencies") or ()),
                responsibilities=tuple(
                    (
                        resp[0],
                        tuple(resp[1] or ()),
                        tuple(resp[2] or ()),
                    )
                    for resp in (entry.get("responsibilities") or ())
                ),
            )
        )
    return tuple(nodes)


def _relatedness_clusters(
    node: ModuleGraphNode,
) -> tuple[ResponsibilityCluster, ...]:
    """Cluster the module's responsibilities by structural affinity:
    two responsibilities belong to the same cluster when they share an
    interface or a dependency. Connected components of that affinity
    graph — deterministic, never a keyword heuristic."""
    if not node.responsibilities:
        return ()
    remaining = list(node.responsibilities)
    clusters: list[list[tuple[str, tuple[str, ...], tuple[str, ...]]]] = []
    while remaining:
        seed = remaining.pop(0)
        current = [seed]
        seed_affinity = set(seed[1]) | set(seed[2])
        changed = True
        while changed:
            changed = False
            for other in list(remaining):
                other_affinity = set(other[1]) | set(other[2])
                if seed_affinity & other_affinity:
                    current.append(other)
                    seed_affinity |= other_affinity
                    remaining.remove(other)
                    changed = True
        clusters.append(current)
    return tuple(
        ResponsibilityCluster(
            cluster_id=f"{node.module_id}:cluster-{i + 1}",
            responsibilities=tuple(
                resp[0] for resp in sorted(cluster)
            ),
        )
        for i, cluster in enumerate(clusters)
    )


def isr_explicitly_prohibits_concentration(profile: ResponsibilityProfile, isr: Any) -> bool:
    """Does the ISR EXPLICITLY prohibit the module's concentration? Reads E
    boundaries: the module named in a boundary's forbidden_dependency_refs
    is an ISR-declared prohibition. The CRITICAL escalation is genuinely
    ISR-authored — the analyzer never self-escalates."""
    system = isr.system
    return any(
        profile.module_id in boundary.forbidden_dependency_refs
        for boundary in system.architectural_boundaries
    )


class ResponsibilityConcentrationAnalyzer:
    """32.5 — Responsibility Concentration.

    Evaluates an emergent architectural property: does the implementation's
    responsibility structure violate the architectural quality contract?
    Measures CONCENTRATION (multiple unrelated responsibility clusters +
    high dependency diversity + cross-boundary ownership + decision-scope
    conflict), never line count. The finding is evidence; it creates no
    obligation.
    """

    def analyze(
        self,
        isr: Any,
        artifact: Mapping[str, Any],
        *,
        ledger: Any = None,
    ) -> tuple[ResponsibilityConcentrationFinding, ...]:
        module_graph = extract_module_graph(artifact)
        findings: list[ResponsibilityConcentrationFinding] = []
        for node in module_graph:
            profile = self._derive_profile(node, isr)
            signals = self._concentration_signals(profile, isr)
            if signals:
                findings.append(
                    self._finding(node, profile, signals, isr, artifact, ledger)
                )
        return tuple(findings)

    def _derive_profile(
        self, node: ModuleGraphNode, isr: Any
    ) -> ResponsibilityProfile:
        """The profile of one artifact module: responsibility clusters from
        its structural affinity, dependency clusters from the dependency
        groups it touches, scope refs from the 32.1 decisions whose
        architectural_scope includes the module."""
        system = isr.system
        return ResponsibilityProfile(
            module_id=node.module_id,
            responsibility_clusters=_relatedness_clusters(node),
            dependency_clusters=tuple(sorted(set(node.dependencies))),
            scope_refs=tuple(
                sorted(
                    d.decision_id
                    for d in system.architectural_decisions
                    if node.module_id in d.architectural_scope
                )
            ),
        )

    def _concentration_signals(
        self, profile: ResponsibilityProfile, isr: Any
    ) -> tuple[str, ...]:
        """The four signals. A finding fires on unrelated-cluster
        concentration, not on size."""
        signals: list[str] = []
        if len(profile.responsibility_clusters) > 1:
            signals.append("multiple_unrelated_responsibility_clusters")
        if len(profile.dependency_clusters) > DEPENDENCY_DIVERSITY_BOUND:
            signals.append("high_dependency_diversity")
        if self._cross_boundary_ownership(profile, isr):
            signals.append("cross_boundary_ownership")
        if self._decision_scope_conflict(profile, isr):
            signals.append("decision_scope_conflict")
        return tuple(signals)

    def _cross_boundary_ownership(
        self, profile: ResponsibilityProfile, isr: Any
    ) -> bool:
        """The module is a member of more than one E boundary — its
        responsibilities span ownership domains."""
        system = isr.system
        owners = [
            boundary.boundary_id
            for boundary in system.architectural_boundaries
            if profile.module_id in boundary.member_refs
        ]
        return len(owners) > 1

    def _decision_scope_conflict(
        self, profile: ResponsibilityProfile, isr: Any
    ) -> bool:
        """The module falls in the architectural scope of more than one
        32.1 decision — multiple decisions claim ownership of it."""
        return len(profile.scope_refs) > 1

    def _finding(
        self,
        node: ModuleGraphNode,
        profile: ResponsibilityProfile,
        signals: tuple[str, ...],
        isr: Any,
        artifact: Mapping[str, Any],
        ledger: Any,
    ) -> ResponsibilityConcentrationFinding:
        severity = self._severity(profile, isr)
        evidence_refs = self._record_evidence(artifact, ledger)
        return ResponsibilityConcentrationFinding(
            module_id=node.module_id,
            responsibility_clusters=tuple(
                c.cluster_id for c in profile.responsibility_clusters
            ),
            dependency_clusters=profile.dependency_clusters,
            scope_refs=profile.scope_refs,
            concentration_signals=signals,
            severity=severity,
            evidence_refs=evidence_refs,
        )

    def _severity(
        self, profile: ResponsibilityProfile, isr: Any
    ) -> ConcentrationSeverity:
        """ADVISORY/WARNING unless the ISR explicitly prohibits the
        concentration. A god-module is only CRITICAL when the ISR's
        boundaries say it must not exist — otherwise the analyzer would be
        authoring an obligation."""
        if isr_explicitly_prohibits_concentration(profile, isr):
            return ConcentrationSeverity.CRITICAL
        if len(profile.responsibility_clusters) > SEVERITY_WARNING_BOUND:
            return ConcentrationSeverity.WARNING
        return ConcentrationSeverity.ADVISORY

    def _record_evidence(
        self, artifact: Mapping[str, Any], ledger: Any
    ) -> tuple[str, ...]:
        """The finding's chain-anchored evidence: the artifact's verification
        event ref, set ONLY when the event actually resolves on the
        supplied ledger. A finding is evidence about the artifact; the
        artifact's verification is its chain anchor."""
        ref = _verification_event_ref(artifact)
        if ref is not None and ledger is not None:
            if ledger.event_by_ref(ref) is None:
                return ()
            return (ref,)
        return ()