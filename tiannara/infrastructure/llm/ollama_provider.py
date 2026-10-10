"""Live Ollama adapter for schema-constrained intent compilation.

This provider is used only by explicit generation trials. It fails closed when
Ollama is unreachable or returns malformed structured output; it never falls
back to recorded task-specific answers.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from tiannara.domain.models.model_call import (
    LanguageModelError,
    ModelCallRecord,
    ModelCallStatus,
    StructuredCompletionRequest,
    compute_call_signature,
    hash_payload,
    hash_prompt,
)
from tiannara.domain.ports.language_model import StructuredCompletionResult

OutputT = TypeVar("OutputT", bound=BaseModel)


class OllamaModelProvider:
    """HTTP adapter for Ollama's local /api/chat structured-output API."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen2.5:3b",
        timeout_seconds: float = 180.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        if not self.base_url.startswith(("http://127.0.0.1", "http://localhost", "http://ollama")):
            raise ValueError("taskflow-ollama-endpoint-must-be-local")
        if timeout_seconds <= 0:
            raise ValueError("taskflow-ollama-timeout-must-be-positive")

    def complete_structured(
        self,
        request: StructuredCompletionRequest,
        output_type: type[OutputT],
    ) -> StructuredCompletionResult[OutputT]:
        started = time.perf_counter()
        options: dict[str, object] = {
            "temperature": request.decoding.temperature,
            "top_p": request.decoding.top_p,
        }
        if request.decoding.seed is not None:
            options["seed"] = request.decoding.seed
        if request.decoding.max_tokens is not None:
            options["num_predict"] = request.decoding.max_tokens

        body = {
            "model": self.model,
            "stream": False,
            "format": output_type.model_json_schema(),
            "messages": [{"role": "user", "content": request.prompt}],
            "options": options,
        }
        http_request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                http_request, timeout=self.timeout_seconds
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
            raw = payload["message"]["content"]
            output = output_type.model_validate_json(raw)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise LanguageModelError("ollama-request-failed") from exc
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            raise LanguageModelError("ollama-structured-response-invalid") from exc

        output_payload = output.model_dump(mode="json")
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
        record = ModelCallRecord(
            signature_hash=compute_call_signature(request),
            model_id=request.model_id,
            task=request.task,
            output_schema_id=request.output_schema_id,
            prompt_hash=hash_prompt(request.prompt),
            response_hash=hash_payload(output_payload),
            output_payload=output_payload,
            latency_ms=elapsed_ms,
            status=ModelCallStatus.LIVE,
            decoding=request.decoding,
        )
        return StructuredCompletionResult(output=output, record=record)
