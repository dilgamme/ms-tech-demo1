import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.models import RagRequest, RoutingRequest
from app.router_logic import ModelRouter


class FastModeRoutingTests(unittest.IsolatedAsyncioTestCase):
    def test_request_defaults_to_optimized_mode(self):
        request = RoutingRequest(prompt="Hello")
        rag_request = RagRequest(question="What is indexed?")

        self.assertTrue(request.fastMode)
        self.assertTrue(rag_request.fastMode)

    async def test_fast_mode_preserves_managed_router_selection(self):
        router = ModelRouter.__new__(ModelRouter)
        router._rule_based_route = lambda prompt: {
            "route": "router",
            "reason": "Rule match: short/simple query → Foundry model-router",
            "intent": "simple",
        }
        router._call_foundry_router_model = AsyncMock(
            return_value=("Short answer", "gpt-5.4-mini")
        )

        response = await router.route_prompt("What is Azure?", fast_mode=True)

        router._call_foundry_router_model.assert_awaited_once_with(
            "What is Azure?",
            None,
            fast_mode=True,
        )
        self.assertEqual(response.modelUsed, "gpt-5.4-mini")
        self.assertNotIn("Fast response mode", response.reason)

    async def test_fast_mode_preserves_explicit_reasoning_route(self):
        router = ModelRouter.__new__(ModelRouter)
        router.reasoning_model = "gpt-5-pro-reasoning"
        router._call_reasoning_model = AsyncMock(return_value="Essential reasoning")

        response = await router.route_prompt(
            "Use GPT-5-Pro and reason deeply about this architecture",
            fast_mode=True,
        )

        router._call_reasoning_model.assert_awaited_once_with(
            "Use GPT-5-Pro and reason deeply about this architecture",
            None,
            fast_mode=True,
        )
        self.assertEqual(response.modelUsed, "gpt-5-pro-reasoning")
        self.assertNotIn("Fast response mode", response.reason)

    async def test_foundry_fast_mode_uses_smaller_output_budget(self):
        router = ModelRouter.__new__(ModelRouter)
        completion = SimpleNamespace(
            model="selected-model",
            choices=[SimpleNamespace(message=SimpleNamespace(content="Answer"))],
        )
        create = unittest.mock.Mock(return_value=completion)
        router.foundry_router_client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=create),
            )
        )
        router.foundry_router_model = "model-router"

        answer, model = await router._call_foundry_router_model(
            "Explain Azure",
            fast_mode=True,
        )

        self.assertEqual(answer, "Answer")
        self.assertEqual(model, "selected-model")
        self.assertEqual(create.call_args.kwargs["max_completion_tokens"], 350)
        self.assertIn(
            "Fast mode is enabled",
            create.call_args.kwargs["messages"][0]["content"],
        )

    async def test_reasoning_model_uses_dedicated_client(self):
        router = ModelRouter.__new__(ModelRouter)
        response = SimpleNamespace(output_text="Reasoned answer")
        create = unittest.mock.Mock(return_value=response)
        router.reasoning_client = SimpleNamespace(
            responses=SimpleNamespace(create=create),
        )
        router.reasoning_model = "gpt-5-pro-reasoning"

        answer = await router._call_reasoning_model(
            "Reason deeply about this design",
            fast_mode=True,
        )

        self.assertEqual(answer, "Reasoned answer")
        self.assertEqual(create.call_args.kwargs["model"], "gpt-5-pro-reasoning")
        self.assertEqual(create.call_args.kwargs["max_output_tokens"], 1200)
        self.assertEqual(create.call_args.kwargs["timeout"], 75)

    async def test_reasoning_model_continues_after_reasoning_only_response(self):
        router = ModelRouter.__new__(ModelRouter)
        analysis = SimpleNamespace(
            id="resp_reasoning",
            output_text=None,
            output=[],
            incomplete_details=SimpleNamespace(reason="max_output_tokens"),
        )
        answer_response = SimpleNamespace(output_text="Final Pro answer")
        create = unittest.mock.Mock(side_effect=[analysis, answer_response])
        router.reasoning_client = SimpleNamespace(
            responses=SimpleNamespace(create=create),
        )
        router.reasoning_model = "gpt-5-pro-reasoning"

        answer = await router._call_reasoning_model("Analyze this deeply", fast_mode=True)

        self.assertEqual(answer, "Final Pro answer")
        self.assertEqual(create.call_count, 2)
        continuation = create.call_args_list[1].kwargs
        self.assertEqual(continuation["previous_response_id"], "resp_reasoning")
        self.assertEqual(continuation["max_output_tokens"], 3000)
        self.assertEqual(continuation["timeout"], 120)


if __name__ == "__main__":
    unittest.main()
