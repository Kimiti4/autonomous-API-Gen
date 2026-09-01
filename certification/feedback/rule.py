"""Failure feedback — classifies stage failures into causal domain + repair
eligibility for the governed evolution loop.

CRITICAL RULE: Never let Campaign B repair generated repositories directly.
If generated code fails → evidence → failure classification → learning →
governed evolution (backend variant) → new candidate → recompile → retest.
NOT: generated code fails → AI edits code → tests pass.

The key epistemic correction: **stage ≠ causal domain.**  A `build` stage can
fail from a Docker registry outage (infrastructure, NOT lowering/compiler) or
from a genuine toolchain/Dockerfile defect.  We therefore classify on the
*detected cause* (the `failure_class` produced by the real-stage classifiers in
`certification/stages/docker_stages.py`), never on the stage name alone.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Causal labels emitted by the real stage classifiers.
CAUSE_INFRASTRUCTURE = "infrastructure"
CAUSE_COMPILER = "compiler"
CAUSE_PRODUCT = "product"
CAUSE_TRANSIENT_BUILD = "transient_build_infrastructure"
CAUSE_UNKNOWN = "unknown"

# Feedback domains (ISR/genome evolution surface).
DOMAIN_INFRASTRUCTURE = "infrastructure"
DOMAIN_LOWERING = "lowering"
DOMAIN_GENOME = "genome"
DOMAIN_ARCHITECTURE = "architecture"
DOMAIN_SECURITY = "security"
DOMAIN_PROVENANCE = "provenance"

ALL_FEEDBACK_DOMAINS: frozenset[str] = frozenset({
    DOMAIN_INFRASTRUCTURE, DOMAIN_LOWERING, DOMAIN_GENOME,
    DOMAIN_ARCHITECTURE, DOMAIN_SECURITY, DOMAIN_PROVENANCE,
})

# Fallback stage→domain map used ONLY when no causal failure_class is present.
_STAGE_TO_DOMAIN: dict[str, str] = {
    "build": DOMAIN_LOWERING,
    "test": DOMAIN_GENOME,
    "deploy": DOMAIN_INFRASTRUCTURE,
    "runtime": DOMAIN_ARCHITECTURE,
    "security": DOMAIN_SECURITY,
    "semantic": DOMAIN_LOWERING,
    "structural": DOMAIN_LOWERING,
    "verify": DOMAIN_PROVENANCE,
}

# Cause → feedback domain.
_CAUSE_TO_DOMAIN: dict[str, str] = {
    CAUSE_INFRASTRUCTURE: DOMAIN_INFRASTRUCTURE,
    CAUSE_TRANSIENT_BUILD: DOMAIN_INFRASTRUCTURE,
    CAUSE_COMPILER: DOMAIN_LOWERING,
    CAUSE_PRODUCT: DOMAIN_GENOME,
}

# Domains that may trigger an EVOLVE (candidate) — backend/variant selection.
# Infrastructure is LEARN-ONLY: retrying/evolving against external infra noise
# would teach Tiannara a false causal lesson (e.g. "rust is bad" when really
# the rust registry was briefly down).
_EVOLVE_ELIGIBLE_DOMAINS = frozenset({
    DOMAIN_GENOME, DOMAIN_ARCHITECTURE, DOMAIN_LOWERING, DOMAIN_SECURITY,
})


@dataclass(frozen=True)
class FailureClassification:
    """A trial failure, classified by DETECTED CAUSE (not mere stage).

    - `stage`:         the TrialStage that failed
    - `cause`:         the detected causal class (infrastructure/compiler/...)
    - `feedback_domain`: the ISR/genome evolution surface to feed back to
    - `repair_eligible`: whether governed evolution may propose a candidate
    - `cause_mark`:    the specific transient signature matched (evidence), if any
    """
    stage: str
    cause: str = CAUSE_UNKNOWN
    feedback_domain: str = DOMAIN_GENOME
    repair_eligible: bool = False
    cause_mark: str = ""

    def as_record(self) -> dict:
        return {
            "stage": self.stage,
            "cause": self.cause,
            "feedback_domain": self.feedback_domain,
            "repair_eligible": self.repair_eligible,
            "cause_mark": self.cause_mark,
        }


def _known_domain(stage: str) -> str:
    return _STAGE_TO_DOMAIN.get(stage, DOMAIN_GENOME)


def analyze_failure(
    *,
    stage: str,
    failure_class: str = "",
    detail: str = "",
) -> FailureClassification:
    """Classify a failed stage by its causal failure_class.

    `failure_class` carries the output of the real stage classifier (see
    `certification/stages/docker_stages.py`): "infrastructure", "compiler",
    "product", "" (unknown).  When non-empty it is authoritative over the
    stage-name heuristic; when empty we fall back to the coarse stage map.
    """
    cause: str
    if failure_class in ("infrastructure", "compiler", "product"):
        cause = failure_class
    elif failure_class == "":
        # No detected causal class: derive a conservative domain from the
        # stage, but never claim repair-eligibility without a causal signal.
        domain = _known_domain(stage)
        cause = CAUSE_INFRASTRUCTURE if domain == DOMAIN_INFRASTRUCTURE else CAUSE_UNKNOWN
        return FailureClassification(
            stage=stage,
            cause=cause,
            feedback_domain=domain,
            repair_eligible=False,
            cause_mark="",
        )
    else:
        cause = CAUSE_UNKNOWN

    domain = _CAUSE_TO_DOMAIN.get(cause, _known_domain(stage))
    eligible = domain in _EVOLVE_ELIGIBLE_DOMAINS
    return FailureClassification(
        stage=stage,
        cause=cause,
        feedback_domain=domain,
        repair_eligible=eligible,
        cause_mark=_detect_cause_mark(cause, detail),
    )


def _detect_cause_mark(cause: str, detail: str) -> str:
    """Return the specific recognized signature, if any, for evidence linking."""
    if cause != CAUSE_INFRASTRUCTURE:
        return ""
    from certification.stages.docker_stages import _match
    from certification.stages import docker_stages as ds

    for marks in (ds.TRANSIENT_DEPLOY_MARKS, ds.TRANSIENT_BUILD_MARKS,
                  ds.TRANSIENT_RUN_MARKS, ds.TRANSIENT_PROBE_MARKS):
        m = _match(detail, marks)
        if m:
            return m
    return ""


def classify_failure(stage: str) -> str:
    """Legacy stage→feedback-domain mapping, kept for the existing contract.

    NOTE: this is a coarse STAGE heuristic and conflates stage with cause.  For
    governed repair use `analyze_failure(...)` which classifies by DETECTED
    CAUSE (e.g. a build failure caused by a registry outage → infrastructure,
    not lowering).  Unknown stages default to "genome".
    """
    return _STAGE_TO_DOMAIN.get(stage, DOMAIN_GENOME)
