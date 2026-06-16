import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.router_logic import ModelRouter


class ReasoningRoutingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.router = ModelRouter.__new__(ModelRouter)

    def test_code_debugging_routes_to_mini(self):
        route = self.router._rule_based_route(
            "Debug this Python exception and identify the root cause."
        )

        self.assertEqual(route["route"], "mini")
        self.assertIn("complex reasoning", route["reason"])

    def test_architecture_planning_routes_to_mini(self):
        route = self.router._rule_based_route(
            "Design an architecture for a resilient API with these constraints."
        )

        self.assertEqual(route["route"], "mini")

    def test_high_complexity_prompt_automatically_routes_to_pro(self):
        route = self.router._rule_based_route(
            """
            Design a multi-region Kubernetes platform and compare active-active
            with active-passive deployment. It must preserve strong consistency,
            support regional failover, minimize cost, and handle network partitions.

            1. Provide the target architecture and migration plan.
            2. Analyze failure modes and operational tradeoffs.
            3. Include Terraform and Kubernetes implementation considerations.
            4. Recommend the best approach and justify the decision.
            """
        )

        self.assertEqual(route["route"], "reasoning")
        self.assertIn("high-complexity", route["reason"])

    def test_compound_production_migration_prompt_routes_to_pro(self):
        route = self.router._rule_based_route(
            """
            Design a production-ready migration plan for a high-traffic monolithic
            application to microservices. Compare at least three architectures,
            quantify trade-offs in cost, reliability, latency, and operational
            complexity, identify failure modes and edge cases, then recommend a
            phased implementation with rollback criteria.
            """
        )

        self.assertEqual(route["route"], "reasoning")
        self.assertIn("GPT-5-Pro", route["reason"])

    def test_architecture_decision_prompt_routes_to_pro(self):
        route = self.router._rule_based_route(
            """
            I need a rigorous architecture decision, not a quick summary.

            Compare three migration strategies for moving a large legacy monolith
            to cloud-native microservices: big-bang rewrite, strangler-fig
            migration, and modular monolith first.

            Evaluate them across risk, delivery speed, team maturity, rollback
            safety, observability, data consistency, and long-term maintainability.
            Then choose the best option for a mid-sized engineering team with
            limited DevOps maturity, list the biggest failure modes, and give a
            phased 90-day execution plan with concrete milestones.
            """
        )

        self.assertEqual(route["route"], "reasoning")
        self.assertIn("architecture decision", route["reason"])

    def test_typical_architecture_prompt_remains_on_mini(self):
        route = self.router._rule_based_route(
            "Design a high availability architecture for a customer API with failover."
        )

        self.assertEqual(route["route"], "mini")

    def test_high_traffic_workload_is_not_mistaken_for_live_traffic(self):
        route = self.router._rule_based_route(
            "Design a scalable API for a high-traffic application."
        )

        self.assertEqual(route["route"], "mini")

    def test_math_and_logic_routes_to_mini(self):
        route = self.router._rule_based_route(
            "Solve 24 / 6 + 7 and explain the reasoning."
        )

        self.assertEqual(route["route"], "mini")

    def test_simple_question_uses_mini(self):
        route = self.router._rule_based_route("What is Azure?")

        self.assertEqual(route["route"], "mini")
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

        self.assertEqual(route["route"], "realtime")
        self.assertEqual(route["intent"], "realtime")

    async def test_mini_route_calls_mini_answer_model(self):
        self.router.router_model = "gpt-5.4-mini"
        self.router._call_mini_answer_model = AsyncMock(return_value="Reasoned answer")

        response = await self.router.route_prompt(
            "Compare options and recommend the best approach."
        )

        self.router._call_mini_answer_model.assert_awaited_once()
        self.assertEqual(response.modelUsed, "gpt-5.4-mini")

    async def test_classifier_reasoning_intent_maps_to_mini(self):
        completion = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            '{"intent":"planning","confidence":0.91,'
                            '"route":"mini","reason":"planning task"}'
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

    async def test_low_confidence_classifier_defaults_to_mini(self):
        completion = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            '{"intent":"unknown","confidence":0.31,'
                            '"route":"reasoning","reason":"uncertain"}'
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

        classification = await self.router._classify_intent("An ambiguous request")

        self.assertEqual(classification["route"], "mini")
        self.assertIn("low-confidence", classification["reason"])

    async def test_automatic_pro_guard_overrides_low_classifier_confidence(self):
        completion = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            '{"intent":"planning","confidence":0.42,'
                            '"route":"mini","reason":"uncertain"}'
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
        prompt = """
        Design a multi-region Kubernetes platform and compare active-active with
        active-passive. It must preserve consistency and handle network partitions.

        1. Analyze failure modes and tradeoffs.
        2. Provide a migration plan.
        3. Include Terraform and Kubernetes implementation details.
        4. Recommend and justify the best architecture for these requirements.
        """

        classification = await self.router._classify_intent(prompt)

        self.assertEqual(classification["route"], "reasoning")
        self.assertIn("GPT-5-Pro", classification["reason"])

    async def test_classifier_failure_defaults_to_mini(self):
        self.router.router_model = "gpt-5.4-mini"
        self.router.client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=unittest.mock.Mock(side_effect=RuntimeError("classifier unavailable"))
                )
            )
        )

        classification = await self.router._classify_intent("An unmatched request")

        self.assertEqual(classification["route"], "mini")
        self.assertEqual(classification["intent"], "simple")


class ExpandedRuleRoutingTests(unittest.TestCase):
    def setUp(self):
        self.router = ModelRouter.__new__(ModelRouter)

    def assert_route(self, prompt, route, intent):
        result = self.router._rule_based_route(prompt)
        self.assertIsNotNone(result, prompt)
        self.assertEqual(result["route"], route, prompt)
        self.assertEqual(result["intent"], intent, prompt)

    def test_common_mini_rules(self):
        cases = (
            ("Hello, how are you?", "conversation"),
            ("Write an email asking for a project update.", "writing"),
            ("Extract the action items from this text.", "extraction"),
            ("Make this professional: send it today.", "transformation"),
            ("Give me ideas for an Azure workshop.", "planning"),
            ("How does Azure Functions work?", "simple"),
        )

        for prompt, intent in cases:
            with self.subTest(prompt=prompt):
                self.assert_route(prompt, "mini", intent)

    def test_specialized_rules_keep_priority(self):
        cases = (
            ("Translate to Polish: Hello", "deepseek", "translation"),
            ("Summarize this report in five bullets", "deepseek", "summary"),
            ("What is the weather today?", "realtime", "realtime"),
            ("Use GPT-5-Pro and deeply analyze this design", "reasoning", "reasoning"),
        )

        for prompt, route, intent in cases:
            with self.subTest(prompt=prompt):
                self.assert_route(prompt, route, intent)

    def test_temporal_word_without_live_data_stays_on_mini(self):
        self.assert_route(
            "Make this professional: please send the report today.",
            "mini",
            "transformation",
        )

    def test_temporal_word_with_live_subject_uses_realtime(self):
        self.assert_route(
            "What Azure announcements happened today?",
            "realtime",
            "realtime",
        )

    def test_high_availability_architecture_is_not_live_data(self):
        self.assert_route(
            "Design a high availability architecture for this API.",
            "mini",
            "reasoning",
        )


if __name__ == "__main__":
    unittest.main()
