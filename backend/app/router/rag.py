import logging

from fastapi import APIRouter, HTTPException

from app.models import RagRequest, RagResponse
from app.rag_service import get_rag_service

router = APIRouter(prefix="/api", tags=["rag"])
logger = logging.getLogger(__name__)


@router.post("/rag", response_model=RagResponse)
async def rag_answer(request: RagRequest) -> RagResponse:
    try:
        logger.info("RAG question: %s", request.question[:100])
        service = get_rag_service()
        return await service.answer(request.question, request.topK)
    except ValueError as exc:
        logger.error("RAG configuration/query error: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("RAG answer error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing RAG request: {exc}")
