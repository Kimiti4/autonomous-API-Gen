import json

import pytest
from pydantic import BaseModel

from tiannara.domain.models.model_call import (
    LanguageModelError,
    ModelCallStatus,
    StructuredCompletionRequest,
)
from tiannara.infrastructure.llm.ollama_provider import OllamaModelProvider


class ExampleOutput(BaseModel):
    capability: str


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def request():
    return StructuredCompletionRequest(
        model_id="ollama:qwen2.5:3b",
        task="intent.elicitation",
        prompt="Identify capabilities from this specification.",
        output_schema_id="example.v1",
    )


def test_ollama_provider_returns_schema_validated_live_provenance(monkeypatch):
    def fake_urlopen(_request, timeout):
        assert timeout == 7
        return FakeResponse({
            "message": {"content": json.dumps({"capability": "cataloguing"})}
        })

    monkeypatch.setattr(
        "tiannara.infrastructure.llm.ollama_provider.urllib.request.urlopen",
        fake_urlopen,
    )
    result = OllamaModelProvider(timeout_seconds=7).complete_structured(
        request(), ExampleOutput
    )

    assert result.output.capability == "cataloguing"
    assert result.record.status == ModelCallStatus.LIVE
    assert result.record.model_id == "ollama:qwen2.5:3b"
    assert result.record.output_payload == {"capability": "cataloguing"}
    assert result.record.response_hash


def test_ollama_provider_fails_closed_on_invalid_structured_output(monkeypatch):
    monkeypatch.setattr(
        "tiannara.infrastructure.llm.ollama_provider.urllib.request.urlopen",
        lambda *_args, **_kwargs: FakeResponse({
            "message": {"content": '{"unexpected":"field"}'}
        }),
    )
    with pytest.raises(LanguageModelError, match="ollama-structured-response-invalid"):
        OllamaModelProvider().complete_structured(request(), ExampleOutput)


def test_ollama_provider_rejects_nonlocal_endpoint():
    with pytest.raises(ValueError, match="taskflow-ollama-endpoint-must-be-local"):
        OllamaModelProvider(base_url="https://example.com")
