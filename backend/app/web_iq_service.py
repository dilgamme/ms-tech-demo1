import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

from openai import OpenAI

from app.azure_auth import get_openai_api_key
from app.config import settings
from app.models import RagSource


@dataclass
class WebIQResult:
    answer: str
    model: str
    sources: list[RagSource]


class WebIQService:
    def __init__(self):
        endpoint = (settings.WEB_IQ_ENDPOINT or "").rstrip("/")
        if not endpoint:
            raise ValueError("WEB_IQ_ENDPOINT is required when Web IQ is enabled")

        self.model = settings.WEB_IQ_MODEL or settings.ROUTER_MODEL
        self.client = OpenAI(
            api_key=settings.WEB_IQ_KEY or get_openai_api_key(),
            base_url=f"{endpoint}/openai/v1/",
            max_retries=0,
        )

    async def search(
        self,
        prompt: str,
        messages: list | None = None,
        fast_mode: bool = False,
    ) -> WebIQResult:
        tool = {
            "type": "web_search",
            "search_context_size": settings.WEB_IQ_SEARCH_CONTEXT_SIZE,
        }
        if settings.WEB_IQ_COUNTRY:
            tool["user_location"] = {
                "type": "approximate",
                "country": settings.WEB_IQ_COUNTRY,
            }

        response = await asyncio.wait_for(
            asyncio.to_thread(
                self.client.responses.create,
                model=self.model,
                input=self._prepare_input(prompt, messages),
                instructions=(
                    f"Current date: {datetime.now(timezone.utc).date().isoformat()}. "
                    "Use web search for fresh, real-world information. Search the public web yourself; "
                    "do not ask the user to provide a source unless the requested information is private, "
                    "ambiguous, or unavailable in the search results. Answer clearly and concisely. "
                    "Base time-sensitive claims on the search results, preserve uncertainty, and cite sources. "
                    "For sports, elections, prices, releases, schedules, and live/current events, verify the "
                    "latest available result or fixture before answering. "
                    "For image or video requests, return useful public pages or media URLs; do not claim that "
                    "you directly inspected media unless the search result provides that information."
                    + (
                        " Fast mode is enabled: lead with the answer and include only the most relevant sources."
                        if fast_mode
                        else ""
                    )
                ),
                tools=[tool],
                include=["web_search_call.action.sources"],
                max_output_tokens=450 if fast_mode else 1200,
                timeout=settings.WEB_IQ_TIMEOUT_SECONDS,
            ),
            timeout=settings.WEB_IQ_TIMEOUT_SECONDS + 5,
        )

        answer = self._extract_text(response)
        sources = self._extract_sources(response, answer)
        return WebIQResult(answer=answer, model=self.model, sources=sources)

    @staticmethod
    def _prepare_input(prompt: str, messages: list | None) -> list[dict]:
        prepared = []
        for message in list(messages or [])[-6:]:
            role = message.get("role")
            content = str(message.get("content", ""))[:1200]
            if role in {"user", "assistant"} and content:
                prepared.append({"role": role, "content": content})
        prepared.append({"role": "user", "content": prompt})
        return prepared

    @staticmethod
    def _extract_text(response) -> str:
        output_text = getattr(response, "output_text", None)
        if output_text:
            return output_text

        payload = WebIQService._as_dict(response)
        parts = []
        for item in payload.get("output", []):
            for content in item.get("content", []):
                if content.get("text"):
                    parts.append(content["text"])
        if not parts:
            raise ValueError("Web IQ returned no text output")
        return "\n".join(parts)

    @staticmethod
    def _extract_sources(response, answer: str) -> list[RagSource]:
        payload = WebIQService._as_dict(response)
        candidates = []

        for item in payload.get("output", []):
            if item.get("type") == "message":
                for content in item.get("content", []):
                    for annotation in content.get("annotations", []):
                        if annotation.get("type") == "url_citation":
                            start = annotation.get("start_index")
                            end = annotation.get("end_index")
                            excerpt = ""
                            if isinstance(start, int) and isinstance(end, int):
                                excerpt = answer[start:end].strip()
                            candidates.append({
                                "url": annotation.get("url"),
                                "title": annotation.get("title"),
                                "excerpt": excerpt,
                            })
            if item.get("type") == "web_search_call":
                for source in (item.get("action") or {}).get("sources", []):
                    candidates.append({
                        "url": source.get("url"),
                        "title": source.get("title"),
                        "excerpt": "",
                    })

        sources = []
        seen_urls = set()
        for candidate in candidates:
            url = candidate.get("url")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            title = candidate.get("title") or urlparse(url).netloc or "Web source"
            excerpt = candidate.get("excerpt") or "Public web source consulted by Web IQ."
            sources.append(RagSource(title=title, chunk=excerpt, source=url))
            if len(sources) >= settings.WEB_IQ_MAX_SOURCES:
                break
        return sources

    @staticmethod
    def _as_dict(value) -> dict:
        if isinstance(value, dict):
            return value
        if hasattr(value, "model_dump"):
            return value.model_dump()
        raise TypeError("Unsupported Responses API payload")


_web_iq_service = None


def get_web_iq_service() -> WebIQService:
    global _web_iq_service
    if _web_iq_service is None:
        _web_iq_service = WebIQService()
    return _web_iq_service
