from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
import logging

from app.memory_service import get_memory_service
from app.models import RoutingRequest, RoutingResponse, ErrorResponse
from app.router_logic import get_router
from app.user_auth import UserIdentity, get_optional_user_identity

router = APIRouter(prefix="/api", tags=["routing"])
logger = logging.getLogger(__name__)

@router.post("/routePrompt", response_model=RoutingResponse)
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
        memory_scope = identity.memory_scope if identity else x_memory_user_id
        memory_context = await memory_service.search_context(memory_scope, request.prompt)
        if memory_context:
            messages.insert(0, {"role": "system", "content": memory_context})
        
        # Route the prompt
        result = await router_instance.route_prompt(request.prompt, messages)
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


@router.get("/memory/status")
async def memory_status() -> dict:
    return await get_memory_service().status()


@router.post("/memory/reset")
async def reset_memory(
    x_memory_user_id: str | None = Header(default=None),
    identity: UserIdentity | None = Depends(get_optional_user_identity),
) -> dict:
    memory_scope = identity.memory_scope if identity else x_memory_user_id
    if not memory_scope:
        raise HTTPException(status_code=400, detail="X-Memory-User-ID header is required")
    deleted = await get_memory_service().delete_scope(memory_scope)
    return {"deleted": deleted}


@router.get("/memory/search")
async def search_memory(
    query: str | None = Query(default=None, max_length=1000),
    x_memory_user_id: str | None = Header(default=None),
    identity: UserIdentity | None = Depends(get_optional_user_identity),
) -> dict:
    memory_scope = identity.memory_scope if identity else x_memory_user_id
    if not memory_scope:
        raise HTTPException(status_code=400, detail="X-Memory-User-ID header is required")
    memories = await get_memory_service().search_memories(memory_scope, query)
    return {"memories": memories}
