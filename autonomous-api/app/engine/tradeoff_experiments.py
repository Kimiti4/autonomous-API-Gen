"""Evidence-backed trade-off experiments for conflicting invariants."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class TradeoffAlternative:
    alternative_id: str
    conflict_id: str
    description: str
    changes: tuple[str, ...]
    preserved_properties: tuple[str, ...]
    at_risk_properties: tuple[str, ...]


@dataclass(frozen=True)
class TradeoffObservation:
    alternative_id: str
    measurements: Mapping[str, float | bool | str]
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class TradeoffAssessment:
    alternative_id: str
    preserved_properties: tuple[str, ...]
    at_risk_properties: tuple[str, ...]
    measurements: Mapping[str, float | bool | str]
    evidence: tuple[str, ...]
    status: str


def create_alternative(
    alternative_id: str,
    conflict_id: str,
    description: str,
    changes: tuple[str, ...],
    preserved_properties: tuple[str, ...],
    at_risk_properties: tuple[str, ...],
) -> TradeoffAlternative:
    if not changes:
        raise ValueError("tradeoff-requires-changes")
    if not preserved_properties and not at_risk_properties:
        raise ValueError("tradeoff-requires-property-impact")
    return TradeoffAlternative(
        alternative_id, conflict_id, description, changes,
        preserved_properties, at_risk_properties,
    )


def observe(
    alternative: TradeoffAlternative,
    measurements: Mapping[str, float | bool | str],
    evidence: tuple[str, ...],
) -> TradeoffObservation:
    if not measurements:
        raise ValueError("tradeoff-requires-measurements")
    if not evidence:
        raise ValueError("tradeoff-observation-requires-evidence")
    return TradeoffObservation(alternative.alternative_id, measurements, evidence)


def assess(
    alternative: TradeoffAlternative,
    observation: TradeoffObservation,
) -> TradeoffAssessment:
    if observation.alternative_id != alternative.alternative_id:
        raise ValueError("tradeoff-alternative-mismatch")
    status = "bounded" if observation.evidence else "unknown"
    return TradeoffAssessment(
        alternative.alternative_id,
        alternative.preserved_properties,
        alternative.at_risk_properties,
        observation.measurements,
        observation.evidence,
        status,
    )
