from fastapi import APIRouter, HTTPException
import logging

from app.models import RoutingRequest, RoutingResponse, ErrorResponse
from app.router_logic import get_router

router = APIRouter(prefix="/api", tags=["routing"])
logger = logging.getLogger(__name__)

@router.post("/routePrompt", response_model=RoutingResponse)
async def route_prompt(request: RoutingRequest) -> RoutingResponse:
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
        
        # Route the prompt
        result = await router_instance.route_prompt(request.prompt, messages)
        
        logger.info(f"Routed to {result.modelUsed} with reason: {result.reason}")
        return result
        
    except Exception as e:
        logger.error(f"Error routing prompt: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )
