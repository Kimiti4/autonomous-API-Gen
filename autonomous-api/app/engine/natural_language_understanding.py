"""Hybrid natural-language understanding for ESAP.

The deterministic local path handles common requirement language without a
network dependency. An optional provider may interpret complex language, but
its output is untrusted semantic input: it is validated, source-bound, and
never authorizes compilation, security policy, or certification by itself.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Protocol


SCHEMA_VERSION = "esap.nl-understanding.v1"
SUPPORTED_INTENTS = {
    "create", "read", "update", "delete", "search", "authenticate",
    "authorize", "notify", "integrate", "report", "unknown",
}
SUPPORTED_CONSTRAINTS = {
    "authentication_required", "authorization_required", "tenant_isolation",
    "audit_required", "idempotent", "ordered_delivery", "retry_required",
    "data_validation", "availability", "performance", "unknown",
}
COMPLEXITY_MARKERS = (
    "unless", "except when", "provided that", "notwithstanding", "whereas",
    "in the event", "only if", "as long as", "respectively", "otherwise",
    "subject to", "at least", "no more than", "eventually consistent",
    "idempotent", "compensating transaction", "cross-tenant",
)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ExtractedConstraint:
    kind: str
    evidence: str
    source_start: int
    source_end: int


@dataclass(frozen=True)
class Understanding:
    schema_version: str
    source_hash: str
    normalized_text: str
    intent: str
    entities: tuple[str, ...]
    constraints: tuple[ExtractedConstraint, ...]
    ambiguities: tuple[str, ...]
    confidence: float
    method: str
    requires_human_review: bool
    provider_name: str | None = None

    @property
    def usable_for_requirement_drafting(self) -> bool:
        return (
            self.intent != "unknown"
            and not self.ambiguities
            and self.confidence >= 0.80
            and not self.requires_human_review
        )


class ComplexLanguageProvider(Protocol):
    """Adapter contract; implementations may call an external LLM."""

    @property
    def name(self) -> str: ...

    def interpret(self, text: str) -> Mapping[str, Any]: ...


def _local_understand(text: str) -> Understanding:
    lowered = " ".join(text.split()).casefold()
    intent = "unknown"
    patterns = (
        ("authenticate", r"\b(log in|log out|sign in|sign out|authenticate|password reset|mfa)\b"),
        ("authorize", r"\b(permission|permissions|role-based|rbac|access control|authorize|authorization)\b"),
        ("create", r"\b(create|add|register|submit|make)\b"),
        ("read", r"\b(read|get|view|display|list|show|retrieve)\b"),
        ("update", r"\b(update|edit|change|modify)\b"),
        ("delete", r"\b(delete|remove|erase|archive)\b"),
        ("search", r"\b(search|filter|find)\b"),
        ("notify", r"\b(notify|notification|alert|email|send a message)\b"),
        ("report", r"\b(report|analytics|dashboard|export)\b"),
        ("integrate", r"\b(integrate|connect|synchronize|sync)\b"),
    )
    matches = [name for name, pattern in patterns if re.search(pattern, lowered)]
    if len(matches) == 1:
        intent = matches[0]
    elif len(matches) > 1:
        intent = "unknown"

    constraints: list[ExtractedConstraint] = []
    constraint_patterns = (
        ("authentication_required", r"\b(must be authenticated|authentication required|must log in|only authenticated)\b"),
        ("authorization_required", r"\b(only (?:the )?(?:owner|admin|administrator|manager)|must have permission|authorized users only|access control)\b"),
        ("tenant_isolation", r"\b(tenant isolation|cross-tenant|other workspaces?|own workspace only|strict isolation)\b"),
        ("audit_required", r"\b(audit(?:ed| trail| log| logging)?|record every change)\b"),
        ("idempotent", r"\b(idempotent|idempotency key|safe to retry without duplicating)\b"),
        ("ordered_delivery", r"\b(in order|ordered delivery|preserve ordering)\b"),
        ("retry_required", r"\b(retry|retries|exponential backoff)\b"),
        ("data_validation", r"\b(validate|validation|must not be empty|valid format)\b"),
        ("availability", r"\b(high availability|available 99\.[0-9]+%|failover)\b"),
        ("performance", r"\b(within [0-9]+ ?ms|under [0-9]+ ?ms|latency|throughput)\b"),
    )
    for kind, pattern in constraint_patterns:
        match = re.search(pattern, lowered)
        if match:
            constraints.append(ExtractedConstraint(kind, text[match.start():match.end()], match.start(), match.end()))

    ambiguities: list[str] = []
    if intent == "unknown":
        ambiguities.append("No single supported intent could be identified deterministically.")
    if len(matches) > 1:
        ambiguities.append("The text appears to express multiple intents; split it into atomic requirements.")
    if any(marker in lowered for marker in COMPLEXITY_MARKERS):
        ambiguities.append("Conditional, comparative, or domain-specific wording needs deeper interpretation.")
    if re.search(r"\b(secure|fast|easy|robust|intelligent|appropriate|etc\.?|and so on)\b", lowered):
        ambiguities.append("A vague term needs an explicit, testable definition.")
    confidence = 0.92 if intent != "unknown" and not ambiguities else (0.55 if intent != "unknown" else 0.20)
    entities = tuple(dict.fromkeys(
        match.group(0) for match in re.finditer(r"\b[A-Za-z][A-Za-z0-9_-]{2,}\b", text)
        if match.group(0).casefold() not in {"must", "should", "could", "would", "the", "and", "for", "with", "from", "only"}
    ))
    return Understanding(
        SCHEMA_VERSION, _digest(text), " ".join(text.split()), intent,
        entities, tuple(constraints), tuple(ambiguities), confidence,
        "local_rules", bool(ambiguities or intent == "unknown"), None,
    )


def _validate_provider_result(text: str, payload: Mapping[str, Any], provider_name: str) -> Understanding:
    """Validate untrusted provider output; never silently coerce invalid fields."""
    allowed_keys = {"intent", "entities", "constraints", "ambiguities", "confidence"}
    if set(payload) - allowed_keys:
        raise ValueError("provider returned unsupported fields")
    intent = payload.get("intent")
    entities = payload.get("entities")
    raw_constraints = payload.get("constraints")
    ambiguities = payload.get("ambiguities")
    confidence = payload.get("confidence")
    if intent not in SUPPORTED_INTENTS:
        raise ValueError("provider intent is outside the supported vocabulary")
    if not isinstance(entities, list) or any(not isinstance(x, str) or not x.strip() for x in entities):
        raise ValueError("provider entities must be a list of non-empty strings")
    if not isinstance(raw_constraints, list) or not isinstance(ambiguities, list):
        raise ValueError("provider constraints and ambiguities must be lists")
    if any(not isinstance(x, str) for x in ambiguities):
        raise ValueError("provider ambiguities must contain strings")
    parsed: list[ExtractedConstraint] = []
    for item in raw_constraints:
        if not isinstance(item, Mapping) or set(item) != {"kind", "evidence"}:
            raise ValueError("each provider constraint must contain exactly kind and evidence")
        kind, evidence = item["kind"], item["evidence"]
        if kind not in SUPPORTED_CONSTRAINTS or not isinstance(evidence, str) or not evidence:
            raise ValueError("provider constraint is unsupported or lacks evidence")
        start = text.find(evidence)
        if start < 0:
            raise ValueError("provider evidence must be an exact substring of the source text")
        parsed.append(ExtractedConstraint(kind, evidence, start, start + len(evidence)))
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise ValueError("provider confidence must be numeric between 0 and 1")
    ambiguity_tuple = tuple(ambiguities)
    # External confidence is never accepted as proof. Require review regardless.
    return Understanding(
        SCHEMA_VERSION, _digest(text), " ".join(text.split()), intent,
        tuple(dict.fromkeys(entities)), tuple(parsed), ambiguity_tuple,
        min(float(confidence), 0.79), "external_provider_untrusted", True,
        provider_name,
    )


def understand_requirement(
    text: str,
    *,
    provider: ComplexLanguageProvider | None = None,
    use_provider_for_complex_language: bool = True,
) -> Understanding:
    """Interpret requirement text with a local-first, optional provider path.

    Provider calls are opt-in through dependency injection. No credentials,
    network clients, or external packages are required by ESAP core. A provider
    failure falls back to the local interpretation and records the uncertainty.
    Results from external providers always require human review and are capped
    below the threshold for autonomous requirement acceptance.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("requirement text must be a non-empty string")
    local = _local_understand(text)
    complex_text = bool(local.ambiguities) or any(
        marker in text.casefold() for marker in COMPLEXITY_MARKERS
    )
    if not (provider and use_provider_for_complex_language and complex_text):
        return local
    try:
        payload = provider.interpret(text)
        if not isinstance(payload, Mapping):
            raise ValueError("provider response must be a mapping")
        external = _validate_provider_result(text, payload, provider.name)
        return external
    except Exception as exc:
        # Do not lose the local result or claim successful semantic resolution.
        return Understanding(
            local.schema_version, local.source_hash, local.normalized_text,
            local.intent, local.entities, local.constraints,
            tuple((*local.ambiguities, f"Complex-language provider failed: {type(exc).__name__}.")),
            min(local.confidence, 0.55), "local_fallback_after_provider_failure",
            True, getattr(provider, "name", None),
        )


def to_requirement_draft(understanding: Understanding) -> dict[str, Any]:
    """Produce a reviewable draft, never an authorized ISR or compiler decision."""
    return {
        "schema_version": understanding.schema_version,
        "source_hash": understanding.source_hash,
        "statement": understanding.normalized_text,
        "intent": understanding.intent,
        "entities": list(understanding.entities),
        "constraints": [
            {"kind": c.kind, "evidence": c.evidence, "source_start": c.source_start, "source_end": c.source_end}
            for c in understanding.constraints
        ],
        "ambiguities": list(understanding.ambiguities),
        "confidence": understanding.confidence,
        "method": understanding.method,
        "requires_human_review": True,
        "authorized_for_compilation": False,
    }
