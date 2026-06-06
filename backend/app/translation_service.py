import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.azure_auth import get_translator_auth_headers
from app.config import settings


LANGUAGE_CODES = {
    "afrikaans": "af",
    "arabic": "ar",
    "azeri": "az",
    "azerbaijani": "az",
    "bengali": "bn",
    "bulgarian": "bg",
    "catalan": "ca",
    "chinese": "zh-Hans",
    "chinese simplified": "zh-Hans",
    "simplified chinese": "zh-Hans",
    "chinese traditional": "zh-Hant",
    "traditional chinese": "zh-Hant",
    "croatian": "hr",
    "czech": "cs",
    "danish": "da",
    "dutch": "nl",
    "english": "en",
    "estonian": "et",
    "farsi": "fa",
    "persian": "fa",
    "finnish": "fi",
    "french": "fr",
    "german": "de",
    "greek": "el",
    "hebrew": "he",
    "hindi": "hi",
    "hungarian": "hu",
    "indonesian": "id",
    "italian": "it",
    "japanese": "ja",
    "korean": "ko",
    "latvian": "lv",
    "lithuanian": "lt",
    "malay": "ms",
    "norwegian": "nb",
    "polish": "pl",
    "portuguese": "pt",
    "brazilian portuguese": "pt",
    "romanian": "ro",
    "russian": "ru",
    "serbian": "sr-Cyrl",
    "slovak": "sk",
    "slovenian": "sl",
    "spanish": "es",
    "swahili": "sw",
    "swedish": "sv",
    "thai": "th",
    "turkish": "tr",
    "ukrainian": "uk",
    "urdu": "ur",
    "vietnamese": "vi",
}

_LANGUAGE_PATTERN = "|".join(
    re.escape(name) for name in sorted(LANGUAGE_CODES, key=len, reverse=True)
)


@dataclass(frozen=True)
class TranslationRequest:
    text: str
    target_language: str
    target_language_name: str
    source_language: str | None = None


@dataclass(frozen=True)
class TranslationResult:
    text: str
    detected_language: str | None = None


def parse_translation_request(prompt: str) -> TranslationRequest | None:
    normalized = prompt.strip()
    patterns = (
        rf"^translate(?:\s+this|\s+the following)?(?:\s+text)?\s+from\s+"
        rf"(?P<source>{_LANGUAGE_PATTERN})\s+(?:to|into)\s+"
        rf"(?P<target>{_LANGUAGE_PATTERN})\s*[:,-]\s*(?P<text>.+)$",
        rf"^translate(?:\s+this|\s+the following)?(?:\s+text)?\s+(?:to|into)\s+"
        rf"(?P<target>{_LANGUAGE_PATTERN})\s*[:,-]\s*(?P<text>.+)$",
        rf"^translate\s+(?P<text>.+?)\s+(?:to|into)\s+(?P<target>{_LANGUAGE_PATTERN})"
        rf"(?:\s+now)?[.!?]?$",
        rf"^(?:how do you say|say|write)\s+(?P<text>.+?)\s+in\s+"
        rf"(?P<target>{_LANGUAGE_PATTERN})[.!?]?$",
        rf"^(?P<text>.+?)\s+in\s+(?P<target>{_LANGUAGE_PATTERN})[.!?]?$",
    )

    for pattern in patterns:
        match = re.match(pattern, normalized, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            continue

        text = _strip_wrapping_quotes(match.group("text").strip())
        target_name = match.group("target").lower()
        source_name = match.groupdict().get("source")
        if not text:
            return None
        return TranslationRequest(
            text=text,
            target_language=LANGUAGE_CODES[target_name],
            target_language_name=target_name,
            source_language=LANGUAGE_CODES[source_name.lower()] if source_name else None,
        )

    return None


def resolve_translation_request(
    prompt: str,
    messages: list[dict] | None = None,
) -> TranslationRequest | None:
    request = parse_translation_request(prompt)
    if not request or request.text.lower() not in {"it", "this", "that", "this text", "that text"}:
        return request

    for message in reversed(messages or []):
        if message.get("role") != "assistant":
            continue
        content = str(message.get("content", "")).strip()
        if content:
            return TranslationRequest(
                text=content,
                target_language=request.target_language,
                target_language_name=request.target_language_name,
                source_language=request.source_language,
            )
    return None


def _strip_wrapping_quotes(text: str) -> str:
    quote_pairs = (('"', '"'), ("'", "'"), ("“", "”"), ("‘", "’"))
    for opening, closing in quote_pairs:
        if text.startswith(opening) and text.endswith(closing) and len(text) >= 2:
            return text[1:-1].strip()
    return text


class TranslationService:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        endpoint = (settings.TRANSLATOR_ENDPOINT or settings.AZURE_OPENAI_ENDPOINT).rstrip("/")
        self.url = f"{endpoint}/translator/text/v3.0/translate"
        self.transport = transport

    async def translate(self, request: TranslationRequest) -> TranslationResult:
        params: dict[str, Any] = {
            "api-version": settings.TRANSLATOR_API_VERSION,
            "to": request.target_language,
            "textType": "plain",
        }
        if request.source_language:
            params["from"] = request.source_language

        async with httpx.AsyncClient(
            timeout=settings.TRANSLATOR_TIMEOUT_SECONDS,
            transport=self.transport,
        ) as client:
            response = await client.post(
                self.url,
                params=params,
                headers={
                    **get_translator_auth_headers(),
                    "Content-Type": "application/json",
                },
                json=[{"Text": request.text}],
            )
            response.raise_for_status()

        payload = response.json()
        if not payload or not payload[0].get("translations"):
            raise ValueError("Azure AI Translator returned no translation")

        detected = payload[0].get("detectedLanguage", {}).get("language")
        return TranslationResult(
            text=payload[0]["translations"][0]["text"],
            detected_language=detected,
        )
