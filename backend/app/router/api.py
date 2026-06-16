from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
import logging
import time

from app.memory_service import get_memory_service
from app.conversation_service import get_conversation_service
from app.models import RoutingRequest, RoutingResponse, ErrorResponse, ResponseMetrics
from app.router_logic import get_router
from app.user_auth import UserIdentity, get_optional_user_identity

router = APIRouter(prefix="/api", tags=["routing"])
logger = logging.getLogger(__name__)


def _user_scope(identity: UserIdentity | None, browser_scope: str | None) -> str:
    scope = identity.memory_scope if identity else browser_scope
    if not scope:
        raise HTTPException(status_code=400, detail="X-Memory-User-ID header is required")
    return scope


def _with_latency(result: RoutingResponse, started_at: float) -> RoutingResponse:
    latency_ms = int((time.monotonic() - started_at) * 1000)
    metrics = result.metrics.model_dump(exclude_none=True) if result.metrics else {}
    metrics["latencyMs"] = latency_ms
    result.metrics = ResponseMetrics(**metrics)
    return result

@router.post("/routePrompt", response_model=RoutingResponse, response_model_exclude_none=True)
async def route_prompt(
    request: RoutingRequest,
    background_tasks: BackgroundTasks,
    x_memory_user_id: str | None = Header(default=None),
    identity: UserIdentity | None = Depends(get_optional_user_identity),
) -> RoutingResponse:
    """
    Route a prompt to the appropriate model based on intent classification.
    
    Returns which model was used and the response.
    """
    try:
        started_at = time.monotonic()
        logger.info(f"Routing prompt: {request.prompt[:100]}...")
        
        router_instance = get_router()
        
        # Prepare messages from request
        messages = []
        if request.messages:
            for msg in request.messages:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        memory_service = get_memory_service()
        memory_scope = _user_scope(identity, x_memory_user_id)
        memory_context = await memory_service.search_context(memory_scope, request.prompt)
        if memory_context:
            messages.insert(0, {"role": "system", "content": memory_context})
        
        # Route the prompt
        result = await router_instance.route_prompt(
            request.prompt,
            messages,
            fast_mode=request.fastMode,
            model_mode=request.modelMode,
        )
        result = _with_latency(result, started_at)
        conversation_id = await get_conversation_service().append_turn(
            memory_scope,
            request.conversationId,
            request.prompt,
            result.answer,
            result.modelUsed,
            result.reason,
        )
        result.conversationId = conversation_id
        background_tasks.add_task(
            memory_service.update_from_turn,
            memory_scope,
            request.prompt,
            result.answer,
        )
        
        logger.info(f"Routed to {result.modelUsed} with reason: {result.reason}")
        return result
        
    except Exception as e:
        logger.error(f"Error routing prompt: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )


@router.get("/reasoning/{response_id}", response_model=RoutingResponse, response_model_exclude_none=True)
async def reasoning_response(response_id: str) -> RoutingResponse:
    try:
        started_at = time.monotonic()
        return _with_latency(await get_router().poll_reasoning_response(response_id), started_at)
    except Exception as exc:
        logger.error("Reasoning poll error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error polling reasoning response: {exc}")


@router.get("/memory/status")
async def memory_status() -> dict:
    return await get_memory_service().status()


@router.post("/memory/reset")
async def reset_memory(
    x_memory_user_id: str | None = Header(default=None),
    identity: UserIdentity | None = Depends(get_optional_user_identity),
) -> dict:
    memory_scope = _user_scope(identity, x_memory_user_id)
    deleted = await get_memory_service().delete_scope(memory_scope)
    return {"deleted": deleted}


@router.get("/memory/search")
async def search_memory(
    query: str | None = Query(default=None, max_length=1000),
    x_memory_user_id: str | None = Header(default=None),
    identity: UserIdentity | None = Depends(get_optional_user_identity),
) -> dict:
    memory_scope = _user_scope(identity, x_memory_user_id)
    memories = await get_memory_service().search_memories(memory_scope, query)
    return {"memories": memories}


@router.get("/conversations")
async def list_conversations(
    x_memory_user_id: str | None = Header(default=None),
    identity: UserIdentity | None = Depends(get_optional_user_identity),
) -> dict:
    conversations = await get_conversation_service().list_conversations(_user_scope(identity, x_memory_user_id))
    return {"conversations": conversations}


@router.post("/conversations")
async def create_conversation(
    x_memory_user_id: str | None = Header(default=None),
    identity: UserIdentity | None = Depends(get_optional_user_identity),
) -> dict:
    return await get_conversation_service().create_conversation(_user_scope(identity, x_memory_user_id))


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    x_memory_user_id: str | None = Header(default=None),
    identity: UserIdentity | None = Depends(get_optional_user_identity),
) -> dict:
    try:
        return await get_conversation_service().get_conversation(_user_scope(identity, x_memory_user_id), conversation_id)
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    x_memory_user_id: str | None = Header(default=None),
    identity: UserIdentity | None = Depends(get_optional_user_identity),
) -> dict:
    try:
        await get_conversation_service().delete_conversation(_user_scope(identity, x_memory_user_id), conversation_id)
        return {"deleted": True}
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
