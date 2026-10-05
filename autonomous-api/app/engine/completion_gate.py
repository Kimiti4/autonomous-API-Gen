"""Completion gate preventing scope drift and unsupported feature expansion."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class FeatureSuggestion:
    feature_id: str
    title: str
    reason: str
    evidence_ids: tuple[str, ...]
    optional: bool = True


@dataclass(frozen=True)
class CompletionAssessment:
    required_ids: tuple[str, ...]
    completed_ids: tuple[str, ...]
    verified_ids: tuple[str, ...]
    certified: bool
    suggestions: tuple[FeatureSuggestion, ...] = ()

    @property
    def project_complete(self) -> bool:
        return self.certified and set(self.required_ids) <= set(self.verified_ids)


def assess_completion(
    required_ids: tuple[str, ...],
    verification_results: Mapping[str, Mapping[str, object]],
    certification_passed: bool,
    suggestions: tuple[FeatureSuggestion, ...] = (),
) -> CompletionAssessment:
    required = tuple(sorted(set(required_ids)))
    verified = tuple(sorted(
        rid for rid in required
        if verification_results.get(rid, {}).get("passed") is True
        and bool(verification_results.get(rid, {}).get("evidence_ids"))
    ))
    completed = tuple(sorted(
        rid for rid in required if rid in verification_results
        and verification_results[rid].get("implemented") is True
    ))

    # Optional suggestions are deliberately suppressed until the requested
    # scope is completely verified and certified.
    complete = certification_passed and set(required) <= set(verified)
    return CompletionAssessment(
        required, completed, verified, complete,
        suggestions if complete else (),
    )


def require_project_completion(assessment: CompletionAssessment) -> None:
    if not assessment.project_complete:
        raise ValueError("required-scope-not-e2e-certified")


def require_suggestion_evidence(suggestion: FeatureSuggestion) -> None:
    if not suggestion.title.strip() or not suggestion.reason.strip():
        raise ValueError("suggestion-requires-reason")
    if not suggestion.evidence_ids:
        raise ValueError("suggestion-requires-evidence")
