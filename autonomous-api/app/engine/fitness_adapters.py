"""Adapters that derive fitness metrics from verification evidence."""
from __future__ import annotations
from typing import Mapping, Any
from .evidence_fitness import EvidenceFitness, metric


def derive_fitness(observations: Mapping[str, Any]) -> EvidenceFitness:
    metrics = {}
    sources = {
        "correctness": ("correctness_score", "correctness_evidence"),
        "security": ("security_score", "security_evidence"),
        "performance": ("performance_score", "performance_evidence"),
        "resilience": ("resilience_score", "resilience_evidence"),
        "accessibility": ("accessibility_score", "accessibility_evidence"),
        "maintainability": ("maintainability_score", "maintainability_evidence"),
    }
    for name, (score_key, evidence_key) in sources.items():
        score = observations.get(score_key)
        evidence = tuple(observations.get(evidence_key, ()))
        if score is not None and evidence:
            metrics[name] = metric(name, float(score), evidence)
    return EvidenceFitness(metrics)


def correctness_from_workflow(report: Mapping[str, Any]) -> dict[str, Any]:
    results = tuple(report.get("property_results", ()))
    if not results:
        return {}
    passed = sum(bool(r.get("passed", False)) for r in results)
    score = passed / len(results)
    return {"correctness_score": score, "correctness_evidence": tuple(report.get("evidence", ()))}


def security_from_adversarial(report: Mapping[str, Any]) -> dict[str, Any]:
    tests = tuple(report.get("tests", ()))
    if not tests:
        return {}
    passed = sum(bool(t.get("passed", False)) for t in tests)
    return {"security_score": passed / len(tests),
            "security_evidence": tuple(report.get("evidence", ()))}


def performance_from_measurements(report: Mapping[str, Any]) -> dict[str, Any]:
    score = report.get("normalized_score")
    evidence = tuple(report.get("evidence", ()))
    if score is None or not evidence:
        return {}
    return {"performance_score": float(score), "performance_evidence": evidence}


def resilience_from_recovery(report: Mapping[str, Any]) -> dict[str, Any]:
    score = report.get("normalized_score")
    evidence = tuple(report.get("evidence", ()))
    if score is None or not evidence:
        return {}
    return {"resilience_score": float(score), "resilience_evidence": evidence}


def accessibility_from_audit(report: Mapping[str, Any]) -> dict[str, Any]:
    score = report.get("normalized_score")
    evidence = tuple(report.get("evidence", ()))
    if score is None or not evidence:
        return {}
    return {"accessibility_score": float(score), "accessibility_evidence": evidence}


def maintainability_from_analysis(report: Mapping[str, Any]) -> dict[str, Any]:
    score = report.get("normalized_score")
    evidence = tuple(report.get("evidence", ()))
    if score is None or not evidence:
        return {}
    return {"maintainability_score": float(score), "maintainability_evidence": evidence}


def collect_dimension_reports(
    workflow: Mapping[str, Any],
    security: Mapping[str, Any],
    performance: Mapping[str, Any],
    resilience: Mapping[str, Any],
    accessibility: Mapping[str, Any],
    maintainability: Mapping[str, Any],
) -> EvidenceFitness:
    observations: dict[str, Any] = {}
    for report in (
        correctness_from_workflow(workflow),
        security_from_adversarial(security),
        performance_from_measurements(performance),
        resilience_from_recovery(resilience),
        accessibility_from_audit(accessibility),
        maintainability_from_analysis(maintainability),
    ):
        observations.update(report)
    return derive_fitness(observations)
