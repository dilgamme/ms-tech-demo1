import asyncio
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from openai import OpenAI

from app.config import settings
from app.models import RagResponse, RagSource

logger = logging.getLogger(__name__)

SEARCH_API_VERSION = "2024-07-01"
RAG_TIMEOUT_SECONDS = 20
MAX_CHUNK_CHARS = 1800


class RagService:
    def __init__(self):
        if not settings.AZURE_SEARCH_ENDPOINT:
            raise ValueError("AZURE_SEARCH_ENDPOINT is not configured")
        if not settings.AZURE_SEARCH_KEY:
            raise ValueError("AZURE_SEARCH_KEY is not configured")

        endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip("/")
        self.openai_client = OpenAI(
            api_key=settings.AZURE_OPENAI_KEY,
            base_url=f"{endpoint}/openai/v1/"
        )
        self.search_endpoint = settings.AZURE_SEARCH_ENDPOINT.rstrip("/")
        self.search_key = settings.AZURE_SEARCH_KEY
        self.index_name = settings.AZURE_SEARCH_INDEX
        self.answer_model = settings.RAG_MODEL or settings.ROUTER_MODEL

    async def answer(self, question: str, top_k: int | None = None) -> RagResponse:
        k = top_k or settings.RAG_TOP_K
        sources = await self._search(question, k)
        if not sources:
            return RagResponse(
                answer="I could not find relevant information in the indexed documents.",
                modelUsed=self.answer_model,
                indexUsed=self.index_name,
                sources=[]
            )

        answer = await self._generate_answer(question, sources)
        return RagResponse(
            answer=answer,
            modelUsed=self.answer_model,
            indexUsed=self.index_name,
            sources=sources
        )

    async def _search(self, question: str, top_k: int) -> list[RagSource]:
        payload = {
            "search": question,
            "top": top_k,
            "select": "title,chunk",
            "vectorQueries": [
                {
                    "kind": "text",
                    "text": question,
                    "fields": "text_vector",
                    "k": top_k
                }
            ]
        }
        data = await self._post_search(payload)
        results = []
        for item in data.get("value", []):
            chunk = (item.get("chunk") or "").strip()
            if not chunk:
                continue
            results.append(
                RagSource(
                    title=item.get("title") or "Untitled source",
                    chunk=chunk[:MAX_CHUNK_CHARS],
                    score=item.get("@search.score")
                )
            )
        return results

    async def _generate_answer(self, question: str, sources: list[RagSource]) -> str:
        context = "\n\n".join(
            f"[{idx}] {source.title}\n{source.chunk}"
            for idx, source in enumerate(sources, start=1)
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "Answer using only the retrieved document context. "
                    "If the context does not contain the answer, say that the indexed documents do not include it. "
                    "Keep the answer concise and cite source titles in parentheses."
                )
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nRetrieved document context:\n{context}"
            }
        ]
        response = await asyncio.wait_for(
            asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=self.answer_model,
                messages=messages,
                max_completion_tokens=650,
                timeout=RAG_TIMEOUT_SECONDS
            ),
            timeout=RAG_TIMEOUT_SECONDS
        )
        return response.choices[0].message.content or ""

    async def _post_search(self, payload: dict) -> dict:
        index_path = urllib.parse.quote(self.index_name, safe="")
        url = (
            f"{self.search_endpoint}/indexes/{index_path}/docs/search"
            f"?api-version={SEARCH_API_VERSION}"
        )
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "api-key": self.search_key
            }
        )

        try:
            raw = await asyncio.wait_for(
                asyncio.to_thread(self._urlopen_read, request),
                timeout=RAG_TIMEOUT_SECONDS
            )
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            logger.error("Azure Search RAG query failed: %s", detail)
            raise ValueError(f"Azure Search query failed: {detail}") from exc

        return json.loads(raw.decode("utf-8"))

    def _urlopen_read(self, request: urllib.request.Request) -> bytes:
        with urllib.request.urlopen(request, timeout=RAG_TIMEOUT_SECONDS) as response:
            return response.read()


_rag_service = None


def get_rag_service() -> RagService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RagService()
    return _rag_service
