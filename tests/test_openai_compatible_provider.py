from __future__ import annotations

import json
import sys
import unittest
from io import BytesIO
from unittest.mock import patch

from pydantic import BaseModel

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

from tiannara.domain.models.model_call import (  # noqa: E402
    DecodingParameters,
    ModelCallStatus,
    StructuredCompletionRequest,
)
from tiannara.infrastructure.llm.openai_compatible_provider import (  # noqa: E402
    OpenAICompatibleProvider,
)


class _Output(BaseModel):
    verdict: str
    count: int


class _Response(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class OpenAICompatibleProviderTests(unittest.TestCase):
    def setUp(self):
        self.provider = OpenAICompatibleProvider(
            base_url="http://127.0.0.1:11434/v1",
            model_id="local-test-model",
            timeout_seconds=2,
        )
        self.request = StructuredCompletionRequest(
            model_id="local-test-model",
            task="intent.extraction",
            prompt="Return verdict and count.",
            output_schema_id="test.output.v1",
            decoding=DecodingParameters(temperature=0),
        )

    @patch("tiannara.infrastructure.llm.openai_compatible_provider.urlopen")
    def test_returns_schema_validated_live_result_with_provenance(self, urlopen):
        response = {
            "choices": [{"message": {"content": json.dumps({"verdict": "PASS", "count": 2})}}],
            "usage": {"prompt_tokens": 15, "completion_tokens": 7},
        }
        urlopen.return_value = _Response(json.dumps(response).encode())
        result = self.provider.complete_structured(self.request, _Output)
        self.assertEqual(result.output.verdict, "PASS")
        self.assertEqual(result.output.count, 2)
        self.assertEqual(result.record.status, ModelCallStatus.LIVE)
        self.assertEqual(result.record.model_id, self.request.model_id)
        self.assertEqual(result.record.input_tokens, 15)
        self.assertEqual(len(result.record.signature_hash), 64)
        self.assertIn("/v1/chat/completions", urlopen.call_args.args[0].full_url)

    @patch("tiannara.infrastructure.llm.openai_compatible_provider.urlopen")
    def test_provider_failure_is_not_replayed_or_fabricated(self, urlopen):
        from urllib.error import URLError
        urlopen.side_effect = URLError("offline")
        from tiannara.domain.models.model_call import LanguageModelError
        with self.assertRaises(LanguageModelError):
            self.provider.complete_structured(self.request, _Output)


if __name__ == "__main__":
    unittest.main()
