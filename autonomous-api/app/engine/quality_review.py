"""Quality-aware engineering decision gate."""
from __future__ import annotations
from dataclasses import dataclass
from .quality_profiles import EngineeringQualityProfile
from .engineering_deliberation import EngineeringDeliberation

@dataclass(frozen=True)
class QualityReview:
    approved: bool
    missing_obligations: tuple[str, ...]
    findings: tuple[str, ...]

def review_quality(profile: EngineeringQualityProfile, deliberation: EngineeringDeliberation) -> QualityReview:
    text = " ".join([
        deliberation.problem,
        *(c.statement for c in deliberation.constraints),
        *(a.summary + " " + " ".join(a.assumptions + a.benefits + a.costs + a.risks) for a in deliberation.alternatives),
        *(t.consequence for t in deliberation.tradeoffs),
        *(c.objection + " " + c.falsification_test for c in deliberation.challenges),
    ]).lower()
    missing = tuple(o.obligation_id for o in profile.obligations if not any(
        token in text for token in {
            "correctness": ("correct","invariant","coherent"),
            "accessibility": ("accessib","a11y"),
            "performance": ("performance","latency","throughput"),
            "security": ("security","authorization","authentication","trust"),
            "resilience": ("resilien","failure","retry","recovery"),
            "testability": ("test","verification"),
            "maintainability": ("maintain","modular","refactor"),
            "usability": ("user","usability","ux","interaction"),
            "domain": ("domain","business","invariant"),
            "data": ("data","database","transaction","integrity"),
            "api": ("api","contract"),
            "reliability": ("reliab","failure","recovery"),
            "observability": ("observ","trace","metric","log"),
            "operability": ("operat","health","configuration"),
            "system flow": ("flow","end-to-end","e2e"),
            "contracts": ("contract","api"),
            "data integrity": ("data","integrity","effect"),
            "delivery": ("deploy","delivery","build"),
            "evolution": ("evolut","regression","change"),
        }.get(o.domain, (o.domain,)) 
    ))
    findings = tuple(f"quality obligation not evidenced in deliberation: {x}" for x in missing)
    return QualityReview(not findings, missing, findings)
