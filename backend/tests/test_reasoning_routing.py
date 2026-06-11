import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.router_logic import ModelRouter


class ReasoningRoutingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.router = ModelRouter.__new__(ModelRouter)

    def test_code_debugging_routes_to_mini_before_foundry_router(self):
        route = self.router._rule_based_route(
            "Debug this Python exception and identify the root cause."
        )

        self.assertEqual(route["route"], "mini")
        self.assertIn("Pre-router reasoning gate", route["reason"])

    def test_architecture_planning_routes_to_mini(self):
        route = self.router._rule_based_route(
            "Design an architecture for a resilient API with these constraints."
        )

        self.assertEqual(route["route"], "mini")

    def test_math_and_logic_routes_to_mini(self):
        route = self.router._rule_based_route(
            "Solve 24 / 6 + 7 and explain the reasoning."
        )

        self.assertEqual(route["route"], "mini")

    def test_simple_question_still_uses_managed_router(self):
        route = self.router._rule_based_route("What is Azure?")

        self.assertEqual(route["route"], "router")
        self.assertEqual(route["intent"], "simple")

    def test_explicit_pro_request_keeps_pro_route(self):
        route = self.router._rule_based_route(
            "Use GPT-5-Pro and take your time to analyze this design."
        )

        self.assertEqual(route["route"], "reasoning")

    def test_freshness_takes_priority_over_reasoning(self):
        route = self.router._rule_based_route(
            "Analyze today's stock price and explain the likely drivers."
        )

        self.assertEqual(route["route"], "router")
        self.assertEqual(route["intent"], "realtime")

    async def test_mini_route_does_not_call_foundry_router(self):
        self.router.router_model = "gpt-5.4-mini"
        self.router._call_mini_answer_model = AsyncMock(return_value="Reasoned answer")
        self.router._call_foundry_router_model = AsyncMock()

        response = await self.router.route_prompt(
            "Compare options and recommend the best approach."
        )

        self.router._call_mini_answer_model.assert_awaited_once()
        self.router._call_foundry_router_model.assert_not_awaited()
        self.assertEqual(response.modelUsed, "gpt-5.4-mini")

    async def test_classifier_reasoning_intent_maps_to_mini(self):
        completion = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            '{"intent":"planning","confidence":0.91,'
                            '"route":"router","reason":"planning task"}'
                        )
                    )
                )
            ]
        )
        self.router.router_model = "gpt-5.4-mini"
        self.router.client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=unittest.mock.Mock(return_value=completion))
            )
        )

        classification = await self.router._classify_intent(
            "Create a phased migration strategy for this workload."
        )

        self.assertEqual(classification["route"], "mini")
        self.assertIn("GPT-5-mini", classification["reason"])


if __name__ == "__main__":
    unittest.main()
