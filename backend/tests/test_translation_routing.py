import os
import sys
import unittest

os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://example.cognitiveservices.azure.com/")
os.environ.setdefault("AZURE_OPENAI_KEY", "test-key")
os.environ.setdefault("TRANSLATOR_ENABLED", "true")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.router_logic import ModelRouter  # noqa: E402
from app.translation_service import TranslationResult  # noqa: E402


class FakeTranslationService:
    def __init__(self, result: TranslationResult | None = None, error: Exception | None = None):
        self.result = result
        self.error = error

    async def translate(self, request):
        if self.error:
            raise self.error
        return self.result


class TranslationRoutingTests(unittest.IsolatedAsyncioTestCase):
    def make_router(self, translation_service):
        router = ModelRouter.__new__(ModelRouter)
        router.translation_service = translation_service
        router.deepseek_model = "DeepSeek-V4-Flash"

        async def deepseek(prompt, messages=None, fast_mode=False):
            return "deepseek fallback"

        router._call_deepseek_model = deepseek
        return router

    async def test_routes_parseable_translation_to_translator(self):
        router = self.make_router(
            FakeTranslationService(
                result=TranslationResult(text="Czesc", detected_language="en")
            )
        )

        result = await router.route_prompt("Translate to Polish: Hello")

        self.assertEqual(result.modelUsed, "Azure-AI-Translator")
        self.assertEqual(result.answer, "Czesc")
        self.assertIn("detected source en", result.reason)

    async def test_ambiguous_translation_falls_back_to_deepseek(self):
        router = self.make_router(
            FakeTranslationService(result=TranslationResult(text="unused"))
        )

        result = await router.route_prompt("Can you translate this for me?")

        self.assertEqual(result.modelUsed, "DeepSeek-V4-Flash")
        self.assertEqual(result.answer, "deepseek fallback")
        self.assertIn("ambiguous", result.reason.lower())

    async def test_translator_error_falls_back_to_deepseek(self):
        router = self.make_router(
            FakeTranslationService(error=httpx_error())
        )

        result = await router.route_prompt("Translate to French: Hello")

        self.assertEqual(result.modelUsed, "DeepSeek-V4-Flash")
        self.assertEqual(result.answer, "deepseek fallback")
        self.assertIn("unavailable", result.reason.lower())

    async def test_follow_up_translation_uses_previous_assistant_text(self):
        router = self.make_router(
            FakeTranslationService(
                result=TranslationResult(text="Salam, necesen?", detected_language="pl")
            )
        )

        result = await router.route_prompt(
            "translate it to Azeri now",
            [{"role": "assistant", "content": "Czesc, jak sie masz?"}],
        )

        self.assertEqual(result.modelUsed, "Azure-AI-Translator")
        self.assertEqual(result.answer, "Salam, necesen?")


def httpx_error() -> Exception:
    return RuntimeError("translator unavailable")


if __name__ == "__main__":
    unittest.main()
