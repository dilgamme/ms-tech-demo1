import logging

from fastapi import APIRouter, HTTPException

from app.image_service import get_image_service
from app.models import (
    ImageAnalysisRequest,
    ImageAnalysisResponse,
    ImageGenerationRequest,
    ImageGenerationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/images", tags=["images"])


@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_image(request: ImageGenerationRequest) -> ImageGenerationResponse:
    try:
        return await get_image_service().generate(request.prompt)
    except ValueError as exc:
        logger.error("Image generation failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected image generation failure")
        raise HTTPException(status_code=500, detail="Image generation failed") from exc


@router.post("/analyze", response_model=ImageAnalysisResponse)
async def analyze_image(request: ImageAnalysisRequest) -> ImageAnalysisResponse:
    try:
        return await get_image_service().analyze(request.prompt, request.imageDataUrl)
    except ValueError as exc:
        logger.error("Image analysis failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected image analysis failure")
        raise HTTPException(status_code=500, detail="Image analysis failed") from exc
