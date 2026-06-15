import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.models import RagResponse, RagSource
from app.router_logic import ModelRouter


class SelfKnowledgeRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_repository_question_uses_grounded_rag(self):
        router = ModelRouter.__new__(ModelRouter)
        rag_response = RagResponse(
            answer="This app uses FastAPI and React.",
            modelUsed="gpt-5.4-mini",
            indexUsed="test-index",
            sources=[
                RagSource(
                    title="MS Tech Demo: SOLUTION_ARCHITECTURE.md",
                    chunk="FastAPI backend and React frontend.",
                    source="https://github.com/example/repo/blob/main/SOLUTION_ARCHITECTURE.md",
                )
            ],
        )

        with (
            patch("app.router_logic.settings.SELF_KNOWLEDGE_RAG_ENABLED", True),
            patch("app.router_logic.settings.AZURE_SEARCH_ENDPOINT", "https://search.example"),
            patch(
                "app.router_logic.get_rag_service",
                return_value=SimpleNamespace(answer=AsyncMock(return_value=rag_response)),
            ),
        ):
            response = await router.route_prompt("How are you built?")

        self.assertEqual(response.reason, "Repository-grounded self knowledge")
        self.assertEqual(response.answer, rag_response.answer)
        self.assertEqual(response.sources, rag_response.sources)

    async def test_github_readme_deployment_question_uses_grounded_rag(self):
        router = ModelRouter.__new__(ModelRouter)
        rag_service = SimpleNamespace(
            answer=AsyncMock(
                return_value=RagResponse(
                    answer="GitHub Actions deploys the frontend and backend.",
                    modelUsed="gpt-5.4-mini",
                    indexUsed="test-index",
                    sources=[
                        RagSource(
                            title="MS Tech Demo: README.md",
                            chunk="Push to main deploys through GitHub Actions.",
                            source="https://github.com/example/repo/blob/main/README.md",
                        )
                    ],
                )
            )
        )

        with (
            patch("app.router_logic.settings.SELF_KNOWLEDGE_RAG_ENABLED", True),
            patch("app.router_logic.settings.AZURE_SEARCH_ENDPOINT", "https://search.example"),
            patch("app.router_logic.get_rag_service", return_value=rag_service),
        ):
            response = await router.route_prompt(
                "Check my GitHub README and explain how this app is deployed."
            )

        rag_service.answer.assert_awaited_once()
        self.assertEqual(response.reason, "Repository-grounded self knowledge")
        self.assertEqual(response.sources[0].title, "MS Tech Demo: README.md")

    async def test_rag_failure_falls_back_to_normal_routing(self):
        router = ModelRouter.__new__(ModelRouter)
        router.router_model = "gpt-5.4-mini"
        router._rule_based_route = lambda prompt: {
            "route": "mini",
            "reason": "test fallback",
            "intent": "simple",
        }
        router._call_mini_answer_model = AsyncMock(return_value="Fallback answer")

        with (
            patch("app.router_logic.settings.SELF_KNOWLEDGE_RAG_ENABLED", True),
            patch("app.router_logic.settings.AZURE_SEARCH_ENDPOINT", "https://search.example"),
            patch(
                "app.router_logic.get_rag_service",
                return_value=SimpleNamespace(answer=AsyncMock(side_effect=RuntimeError("search unavailable"))),
            ),
        ):
            response = await router.route_prompt("Tell me about this app")

        self.assertEqual(response.answer, "Fallback answer")
        self.assertEqual(response.modelUsed, "gpt-5.4-mini")

    def test_casual_greeting_is_not_self_knowledge(self):
        router = ModelRouter.__new__(ModelRouter)

        self.assertFalse(router._contains_any("how are you?", (
            "how are you built",
            "how were you built",
        )))


if __name__ == "__main__":
    unittest.main()
