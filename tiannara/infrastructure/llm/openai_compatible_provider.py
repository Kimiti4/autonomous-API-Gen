"""OpenAI-compatible live structured-output provider.

This adapter speaks only the repository's LanguageModelProvider port. It is
opt-in, uses a caller-supplied endpoint/model, and never substitutes recorded
responses when the endpoint is unavailable.
"""
from __future__ import annotations

import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from tiannara.domain.models.model_call import (
    LanguageModelError,
    ModelCallRecord,
    ModelCallStatus,
    StructuredCompletionRequest,
    StructuredCompletionResult,
    compute_call_signature,
    hash_payload,
    hash_prompt,
)
from tiannara.domain.ports.language_model import LanguageModelProvider

OutputT = TypeVar("OutputT", bound=BaseModel)


class OpenAICompatibleProvider(LanguageModelProvider):
    """Live provider for endpoints implementing POST /v1/chat/completions.

    The endpoint must support JSON-object response mode. The requested Pydantic
    schema is included in the system instruction and the returned JSON is
    validated locally. API keys are optional for local endpoints.
    """

    def __init__(
        self,
        base_url: str,
        model_id: str,
        api_key: str | None = None,
        timeout_seconds: float = 90.0,
    ) -> None:
        if not base_url.strip() or not model_id.strip():
            raise ValueError("base_url and model_id are required")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._base_url = base_url.rstrip("/")
        self._model_id = model_id
        self._api_key = api_key
        self._timeout = timeout_seconds

    def complete_structured(
        self,
        request: StructuredCompletionRequest,
        output_type: type[OutputT],
    ) -> StructuredCompletionResult[OutputT]:
        schema = output_type.model_json_schema()
        system = (
            "Return exactly one JSON object conforming to this JSON Schema. "
            "Do not add markdown or commentary.\n"
            + json.dumps(schema, sort_keys=True, separators=(",", ":"))
        )
        body = {
            "model": self._model_id,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": request.prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": request.decoding.temperature,
            "top_p": request.decoding.top_p,
        }
        if request.decoding.max_tokens is not None:
            body["max_tokens"] = request.decoding.max_tokens
        if request.decoding.seed is not None:
            body["seed"] = request.decoding.seed

        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        endpoint = self._base_url
        if not endpoint.endswith("/chat/completions"):
            endpoint += "/chat/completions"
        req = Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        started = time.monotonic()
        try:
            with urlopen(req, timeout=self._timeout) as response:
                raw = response.read()
            payload = json.loads(raw.decode("utf-8"))
            content = payload["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise LanguageModelError("provider returned empty structured content")
            decoded = json.loads(content)
            output = output_type.model_validate(decoded)
        except (HTTPError, URLError, TimeoutError) as exc:
            raise LanguageModelError(
                f"live provider request failed: {type(exc).__name__}"
            ) from exc
        except (KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
            raise LanguageModelError(
                f"live provider returned invalid structured output: {type(exc).__name__}"
            ) from exc

        output_payload = output.model_dump(mode="json")
        usage = payload.get("usage") or {}
        record = ModelCallRecord(
            signature_hash=compute_call_signature(request),
            model_id=self._model_id,
            task=request.task,
            output_schema_id=request.output_schema_id,
            prompt_hash=hash_prompt(request.prompt),
            response_hash=hash_payload(output_payload),
            output_payload=output_payload,
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
            latency_ms=(time.monotonic() - started) * 1000,
            status=ModelCallStatus.LIVE,
            decoding=request.decoding,
        )
        return StructuredCompletionResult(output=output, record=record)
