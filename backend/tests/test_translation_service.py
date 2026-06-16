import os
import sys
import unittest

import httpx

os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://example.cognitiveservices.azure.com/")
os.environ.setdefault("AZURE_OPENAI_KEY", "test-key")
os.environ.setdefault("TRANSLATOR_ENABLED", "true")
os.environ.setdefault("TRANSLATOR_ENDPOINT", "https://example.cognitiveservices.azure.com/")
os.environ["TRANSLATOR_KEY"] = "test-key"

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.translation_service import (  # noqa: E402
    TranslationRequest,
    TranslationService,
    parse_translation_request,
    resolve_translation_request,
)
from app.config import settings  # noqa: E402


class TranslationRequestParsingTests(unittest.TestCase):
    def test_parses_target_first_request(self):
        request = parse_translation_request("Translate to Polish: Hello, how are you?")

        self.assertEqual(request.text, "Hello, how are you?")
        self.assertEqual(request.target_language, "pl")
        self.assertIsNone(request.source_language)

    def test_parses_quoted_text_and_target_at_end(self):
        request = parse_translation_request('Translate "Good morning" into Japanese')

        self.assertEqual(request.text, "Good morning")
        self.assertEqual(request.target_language, "ja")

    def test_parses_explicit_source_and_target(self):
        request = parse_translation_request("Translate from English to French: Cloud routing")

        self.assertEqual(request.text, "Cloud routing")
        self.assertEqual(request.source_language, "en")
        self.assertEqual(request.target_language, "fr")

    def test_returns_none_for_ambiguous_request(self):
        self.assertIsNone(parse_translation_request("Can you translate this for me?"))

    def test_resolves_follow_up_pronoun_from_last_assistant_message(self):
        request = resolve_translation_request(
            "translate it to Azeri now",
            [
                {"role": "user", "content": "Translate to Polish: Hi, how are you?"},
                {"role": "assistant", "content": "Czesc, jak sie masz?"},
            ],
        )

        self.assertEqual(request.text, "Czesc, jak sie masz?")
        self.assertEqual(request.target_language, "az")


class TranslationServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_calls_translator_and_returns_detected_language(self):
        settings.TRANSLATOR_KEY = "test-key"

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/translator/text/v3.0/translate")
            self.assertEqual(request.url.params["to"], "pl")
            self.assertEqual(request.headers["ocp-apim-subscription-key"], "test-key")
            return httpx.Response(
                200,
                json=[{
                    "detectedLanguage": {"language": "en", "score": 1.0},
                    "translations": [{"text": "Czesc", "to": "pl"}],
                }],
            )

        service = TranslationService(transport=httpx.MockTransport(handler))
        result = await service.translate(
            TranslationRequest(
                text="Hello",
                target_language="pl",
                target_language_name="polish",
            )
        )

        self.assertEqual(result.text, "Czesc")
        self.assertEqual(result.detected_language, "en")


if __name__ == "__main__":
    unittest.main()
