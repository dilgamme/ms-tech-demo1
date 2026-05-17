from pydantic import BaseModel, Field
from typing import List, Optional

class Message(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")

class RoutingRequest(BaseModel):
    prompt: str = Field(..., description="User prompt to route")
    messages: Optional[List[Message]] = Field(default=None, description="Chat history")

class RoutingResponse(BaseModel):
    modelUsed: str = Field(..., description="Name of the model used")
    reason: str = Field(..., description="Reason for routing to this model")
    answer: str = Field(..., description="The model's response")

class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error description")
