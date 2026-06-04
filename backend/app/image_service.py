import asyncio
import base64
import json
import logging
import urllib.error
import urllib.request

from app.azure_auth import get_cognitive_services_auth_headers
from app.config import settings
from app.models import ImageAnalysisResponse, ImageGenerationResponse

logger = logging.getLogger(__name__)

IMAGE_TIMEOUT_SECONDS = 60
OPENAI_V1_API = "openai/v1"


class ImageService:
    def __init__(self):
        self.generation_endpoint = (
            settings.IMAGE_OPENAI_ENDPOINT
            or settings.FOUNDRY_ROUTER_ENDPOINT
            or settings.AZURE_OPENAI_ENDPOINT
        ).rstrip("/")
        self.understanding_endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip("/")
        self.generation_model = settings.IMAGE_GENERATION_MODEL
        self.understanding_model = settings.IMAGE_UNDERSTANDING_MODEL or settings.ROUTER_MODEL

    async def generate(self, prompt: str) -> ImageGenerationResponse:
        payload = {
            "model": self.generation_model,
            "prompt": prompt,
            "size": settings.IMAGE_GENERATION_SIZE,
            "quality": settings.IMAGE_GENERATION_QUALITY,
            "n": 1,
        }
        data = await self._post_json(
            self.generation_endpoint,
            "/images/generations",
            payload,
            settings.IMAGE_OPENAI_KEY,
        )
        image = (data.get("data") or [{}])[0]
        b64_json = image.get("b64_json")
        if not b64_json:
            raise ValueError("Image generation did not return base64 image data")
        return ImageGenerationResponse(
            answer="Generated an image from your prompt.",
            modelUsed=self.generation_model,
            reason=f"Image route: generation prompt -> {self.generation_model}",
            imageDataUrl=f"data:image/png;base64,{b64_json}",
        )

    async def analyze(self, prompt: str, image_data_url: str) -> ImageAnalysisResponse:
        if not image_data_url.startswith("data:image/"):
            raise ValueError("Image must be sent as a data:image/... URL")
        self._validate_data_url_size(image_data_url)
        payload = {
            "model": self.understanding_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an image understanding module for an Azure AI demo. "
                        "Answer clearly and mention visible uncertainty when needed."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt or "Describe this image."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_data_url,
                                "detail": "auto",
                            },
                        },
                    ],
                },
            ],
            "max_completion_tokens": 700,
        }
        data = await self._post_json(
            self.understanding_endpoint,
            "/chat/completions",
            payload,
            settings.AZURE_OPENAI_KEY,
        )
        answer = (
            ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
            or ""
        )
        return ImageAnalysisResponse(
            answer=answer,
            modelUsed=self.understanding_model,
            reason=f"Image route: uploaded image + question -> {self.understanding_model}",
        )

    async def _post_json(
        self,
        endpoint: str,
        path: str,
        payload: dict,
        api_key: str | None,
    ) -> dict:
        url = f"{endpoint}/{OPENAI_V1_API}{path}"
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                **get_cognitive_services_auth_headers(api_key),
            },
        )
        try:
            raw = await asyncio.wait_for(
                asyncio.to_thread(self._urlopen_read, request),
                timeout=IMAGE_TIMEOUT_SECONDS,
            )
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            logger.error("Azure image API call failed: %s", detail)
            raise ValueError(detail or "Azure image API call failed") from exc
        return json.loads(raw.decode("utf-8"))

    def _urlopen_read(self, request: urllib.request.Request) -> bytes:
        with urllib.request.urlopen(request, timeout=IMAGE_TIMEOUT_SECONDS) as response:
            return response.read()

    def _validate_data_url_size(self, image_data_url: str) -> None:
        _, _, encoded = image_data_url.partition(",")
        try:
            size = len(base64.b64decode(encoded, validate=True))
        except ValueError as exc:
            raise ValueError("Image data URL is not valid base64") from exc
        if size > 10 * 1024 * 1024:
            raise ValueError("Image upload is too large; use an image under 10 MB")


_image_service = None


def get_image_service() -> ImageService:
    global _image_service
    if _image_service is None:
        _image_service = ImageService()
    return _image_service
