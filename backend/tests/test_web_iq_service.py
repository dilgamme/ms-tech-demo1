import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.models import RagSource
from app.router_logic import ModelRouter
from app.web_iq_service import WebIQResult, WebIQService


class FakeResponse:
    output_text = "Microsoft announced an Azure update."

    def model_dump(self):
        return {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": self.output_text,
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "url": "https://azure.microsoft.com/blog/update",
                                    "title": "Azure update",
                                    "start_index": 0,
                                    "end_index": 19,
                                }
                            ],
                        }
                    ],
                },
                {
                    "type": "web_search_call",
                    "action": {
                        "sources": [
                            {
                                "url": "https://azure.microsoft.com/blog/update",
                                "title": "Azure update",
                            },
                            {
                                "url": "https://learn.microsoft.com/azure/",
                                "title": "Azure documentation",
                            },
                        ]
                    },
                },
            ]
        }


class WebIQServiceTests(unittest.TestCase):
    def test_extracts_and_deduplicates_cited_sources(self):
        sources = WebIQService._extract_sources(FakeResponse(), FakeResponse.output_text)

        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0].title, "Azure update")
        self.assertEqual(sources[0].source, "https://azure.microsoft.com/blog/update")
        self.assertEqual(sources[1].title, "Azure documentation")

    def test_extracts_output_text(self):
        self.assertEqual(
            WebIQService._extract_text(FakeResponse()),
            "Microsoft announced an Azure update.",
        )


class WebIQRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_fresh_prompt_uses_web_iq(self):
        router = ModelRouter.__new__(ModelRouter)
        router._rule_based_route = lambda prompt: {
            "route": "router",
            "reason": "fresh",
            "intent": "realtime",
        }
        result = WebIQResult(
            answer="Fresh answer",
            model="gpt-5.4-mini",
            sources=[
                RagSource(
                    title="Example",
                    chunk="Fresh source",
                    source="https://example.com/news",
                )
            ],
        )
        service = SimpleNamespace(search=AsyncMock(return_value=result))

        with (
            patch("app.router_logic.settings.WEB_IQ_ENABLED", True),
            patch("app.router_logic.get_web_iq_service", return_value=service),
        ):
            response = await router.route_prompt("What is the latest Azure news?")

        self.assertEqual(response.answer, "Fresh answer")
        self.assertEqual(response.modelUsed, "Web IQ + gpt-5.4-mini")
        self.assertEqual(response.sources, result.sources)

    async def test_web_iq_failure_uses_existing_realtime_fallback(self):
        router = ModelRouter.__new__(ModelRouter)
        router.router_model = "gpt-5.4-mini"
        router._rule_based_route = lambda prompt: {
            "route": "router",
            "reason": "fresh",
            "intent": "realtime",
        }
        router._call_router_model = AsyncMock(return_value="Provider fallback")
        service = SimpleNamespace(search=AsyncMock(side_effect=RuntimeError("unavailable")))

        with (
            patch("app.router_logic.settings.WEB_IQ_ENABLED", True),
            patch("app.router_logic.get_web_iq_service", return_value=service),
        ):
            response = await router.route_prompt("Search the web for Azure news")

        self.assertEqual(response.answer, "Provider fallback")
        self.assertEqual(response.reason, "Web IQ unavailable, fallback to realtime providers")


if __name__ == "__main__":
    unittest.main()
