from __future__ import annotations

import pytest

from autonomous_api.app.engine.natural_language_understanding import (
    understand_requirement,
    to_requirement_draft,
)


class FakeProvider:
    name = "fake-complex-language-provider"

    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.calls = 0

    def interpret(self, text):
        self.calls += 1
        if self.error:
            raise self.error
        return self.payload


def test_local_understanding_extracts_read_intent_and_auth_constraint():
    result = understand_requirement("Only authenticated users can list items.")
    assert result.intent == "read"
    assert any(c.kind == "authentication_required" for c in result.constraints)
    assert result.source_hash
    assert result.method == "local_rules"


def test_complex_language_uses_provider_only_when_injected():
    result = understand_requirement("List items unless the account is suspended.")
    assert result.method == "local_rules"
    assert result.requires_human_review


def test_provider_is_used_for_complex_language_and_never_self_authorizes():
    provider = FakeProvider({
        "intent": "read",
        "entities": ["items"],
        "constraints": [{"kind": "authorization_required", "evidence": "only the owner"}],
        "ambiguities": [],
        "confidence": 0.99,
    })
    text = "Only the owner can list items unless suspended."
    result = understand_requirement(text, provider=provider)
    assert provider.calls == 1
    assert result.method == "external_provider_untrusted"
    assert result.confidence <= 0.79
    assert result.requires_human_review
    assert not result.usable_for_requirement_drafting


def test_provider_evidence_must_be_grounded_in_original_text():
    provider = FakeProvider({
        "intent": "read",
        "entities": ["items"],
        "constraints": [{"kind": "authorization_required", "evidence": "admin bypass"}],
        "ambiguities": [],
        "confidence": 0.99,
    })
    result = understand_requirement("Only the owner can list items unless suspended.", provider=provider)
    assert result.method == "local_fallback_after_provider_failure"
    assert any("provider failed" in a for a in result.ambiguities)


def test_provider_failure_falls_back_without_claiming_resolution():
    provider = FakeProvider(error=TimeoutError())
    result = understand_requirement("List items unless the account is suspended.", provider=provider)
    assert result.method == "local_fallback_after_provider_failure"
    assert result.requires_human_review
    assert result.confidence <= 0.55


def test_requirement_draft_is_never_authorized_for_compilation():
    result = understand_requirement("Create a project.")
    draft = to_requirement_draft(result)
    assert draft["authorized_for_compilation"] is False
    assert draft["requires_human_review"] is True


def test_empty_input_is_rejected():
    with pytest.raises(ValueError):
        understand_requirement("   ")
