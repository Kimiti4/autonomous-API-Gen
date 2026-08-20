"""R2.10.32.9 — Metric analyzers: deterministic structural analyses of the
artifact, closing the spec's metric list as emergent-property evidence.

The seven analyzers are each a structural analysis of the artifact —
deterministic, dependency-free, and content-addressed so every
measurement is ledger-replayable. They measure what the artifact
EXHIBITS, never what it ought to be: a MetricMeasurement carries no
obligation_id (emergent-property mode under the 32.7 contract), and
whether a measurement meets a bound is a gate's judgment, never the
analyzer's. Metrics are never obligations — the metric list of the
original Phase 32 specification (cyclomatic complexity, code
duplication, dead code, unused dependencies, naming consistency,
documentation coverage, public API consistency) closes here as evidence
producers, not as authors.
"""
from dataclasses import dataclass
from typing import Protocol

from tiannara.application.quality.tool_adapters import content_address

__all__ = [
    "CodeDuplicationAnalyzer",
    "CyclomaticComplexityAnalyzer",
    "DeadCodeAnalyzer",
    "DocumentationCoverageAnalyzer",
    "MetricAnalyzer",
    "MetricMeasurement",
    "NamingConsistencyAnalyzer",
    "PublicAPIConsistencyAnalyzer",
    "UnusedDependenciesAnalyzer",
    "measurement_evidence_ref",
]


def measurement_evidence_ref(artifact, metric_id: str) -> str:
    """A content-addressed evidence reference for one metric measurement:
    the address changes iff the artifact changes, so every measurement is
    ledger-replayable against its exact input."""
    return f"{metric_id}-{content_address(artifact)[:16]}"


@dataclass(frozen=True)
class MetricMeasurement:
    """One metric's measurement of the artifact. Emergent-property
    evidence: it describes what the artifact exhibits, never what it
    ought to be."""

    metric_id: str
    analyzer_id: str
    analyzer_version: str
    artifact_identity: str
    value: float
    evidence_refs: tuple[str, ...]


class MetricAnalyzer(Protocol):
    """A deterministic structural metric analyzer. Implements the 32.7
    Analyzer contract's evidence-producing surface; produces
    measurements, never obligations and never verdicts."""

    metric_id: str

    def measure(self, artifact) -> MetricMeasurement: ...


class _StructuralMetricAnalyzer:
    """Base for the structural metric analyzers: shared identity plumbing
    and the content-addressed evidence reference."""

    metric_id: str = ""
    analyzer_version: str = "1.0.0"

    def _measure(self, artifact, value: float) -> MetricMeasurement:
        return MetricMeasurement(
            metric_id=self.metric_id,
            analyzer_id=self.metric_id,
            analyzer_version=self.analyzer_version,
            artifact_identity=artifact["provenance"]["artifact_hash"],
            value=value,
            evidence_refs=(measurement_evidence_ref(artifact, self.metric_id),),
        )


class CyclomaticComplexityAnalyzer(_StructuralMetricAnalyzer):
    """Decision-point density per unit: total decision points over total
    lines. A structural density measure — never a line-count verdict."""

    metric_id = "cyclomatic_complexity"

    def measure(self, artifact) -> MetricMeasurement:
        units = artifact["units"]
        decision_points = sum(u.get("decision_points", 0) for u in units)
        lines = sum(u.get("lines", 0) for u in units)
        value = decision_points / lines if lines else 0.0
        return self._measure(artifact, value)


class CodeDuplicationAnalyzer(_StructuralMetricAnalyzer):
    """Structurally duplicated regions: units whose body fingerprint
    appears more than once."""

    metric_id = "code_duplication"

    def measure(self, artifact) -> MetricMeasurement:
        fingerprints = {}
        for unit in artifact["units"]:
            fingerprint = unit["body_fingerprint"]
            fingerprints[fingerprint] = fingerprints.get(fingerprint, 0) + 1
        duplicated = sum(
            count for count in fingerprints.values() if count > 1
        )
        return self._measure(artifact, float(duplicated))


class DeadCodeAnalyzer(_StructuralMetricAnalyzer):
    """Unreachable / unreferenced units: units no other unit references
    and that are not declared entry points."""

    metric_id = "dead_code"

    def measure(self, artifact) -> MetricMeasurement:
        entry_points = set(artifact.get("entry_points", ()))
        dead = 0
        for unit in artifact["units"]:
            if unit["unit_id"] in entry_points:
                continue
            if not unit.get("referenced_by"):
                dead += 1
        return self._measure(artifact, float(dead))


class UnusedDependenciesAnalyzer(_StructuralMetricAnalyzer):
    """Declared-but-unreferenced dependencies: dependencies the artifact
    declares that no module's dependency list uses."""

    metric_id = "unused_dependencies"

    def measure(self, artifact) -> MetricMeasurement:
        used = set()
        for module in artifact["modules"]:
            used.update(module.get("dependencies", ()))
        unused = sum(
            1
            for dep in artifact.get("declared_dependencies", ())
            if dep not in used
        )
        return self._measure(artifact, float(unused))


class NamingConsistencyAnalyzer(_StructuralMetricAnalyzer):
    """Identifier convention coherence: the fraction of unit names
    conforming to the dominant declared convention."""

    metric_id = "naming_consistency"

    def measure(self, artifact) -> MetricMeasurement:
        names = [u["name"] for u in artifact["units"]]
        snake_case = sum(
            1
            for name in names
            if name and "_" in name and name.lower() == name
        )
        camel_case = sum(
            1
            for name in names
            if name and "_" not in name and name[0].islower()
        )
        mixed = len(names) - snake_case - camel_case
        dominant = max(snake_case, camel_case, mixed)
        value = dominant / len(names) if names else 1.0
        return self._measure(artifact, value)


class DocumentationCoverageAnalyzer(_StructuralMetricAnalyzer):
    """Documented surface over total public surface, per the artifact's
    declared module surface counts."""

    metric_id = "documentation_coverage"

    def measure(self, artifact) -> MetricMeasurement:
        public = sum(m.get("public_surface", 0) for m in artifact["modules"])
        documented = sum(
            m.get("documented_surface", 0) for m in artifact["modules"]
        )
        value = documented / public if public else 1.0
        return self._measure(artifact, value)


class PublicAPIConsistencyAnalyzer(_StructuralMetricAnalyzer):
    """Declared API vs realized API coherence: the fraction of the
    declared public API that the artifact's units actually realize."""

    metric_id = "public_api_consistency"

    def measure(self, artifact) -> MetricMeasurement:
        declared = set(artifact.get("declared_api", ()))
        realized = {u["name"] for u in artifact["units"]}
        value = (
            len(declared & realized) / len(declared) if declared else 1.0
        )
        return self._measure(artifact, value)