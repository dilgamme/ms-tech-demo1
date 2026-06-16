import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.models import RagRequest, RagResponse
from app.router.rag import rag_answer


class RagRouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_rag_uses_enterprise_documents_namespace(self):
        service = SimpleNamespace(
            answer=AsyncMock(
                return_value=RagResponse(
                    answer="Refunds are processed within 7-14 business days.",
                    modelUsed="gpt-5.4-mini",
                    indexUsed="rag-1779444354799",
                    sources=[],
                )
            )
        )

        with patch("app.router.rag.get_rag_service", return_value=service):
            response = await rag_answer(RagRequest(question="What is ticket refund policy?"))

        self.assertEqual(response.answer, "Refunds are processed within 7-14 business days.")
        service.answer.assert_awaited_once()
        self.assertEqual(service.answer.await_args.kwargs["namespace"], "documents")


if __name__ == "__main__":
    unittest.main()
