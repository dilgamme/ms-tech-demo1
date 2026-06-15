from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class Message(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")

class RoutingRequest(BaseModel):
    prompt: str = Field(..., description="User prompt to route")
    messages: Optional[List[Message]] = Field(default=None, description="Chat history")
    conversationId: Optional[str] = Field(default=None, description="Foundry conversation ID")
    modelMode: Literal["auto", "reasoning", "general"] = Field(
        default="auto",
        description="Model selection mode: auto router, forced reasoning, or forced general model",
    )
    fastMode: bool = Field(
        default=True,
        description="Use optimized response budgets; retained for API compatibility",
    )

class ResponseMetrics(BaseModel):
    latencyMs: Optional[int] = Field(default=None, description="End-to-end response latency in milliseconds")
    inputTokens: Optional[int] = Field(default=None, description="Input/prompt tokens used")
    outputTokens: Optional[int] = Field(default=None, description="Output/completion tokens used")
    totalTokens: Optional[int] = Field(default=None, description="Total tokens used")

class RagSource(BaseModel):
    title: str = Field(..., description="Source document title")
    chunk: str = Field(..., description="Retrieved source chunk")
    source: Optional[str] = Field(default=None, description="Source path or URL")
    score: Optional[float] = Field(default=None, description="Search score")

class RoutingResponse(BaseModel):
    modelUsed: str = Field(..., description="Name of the model used")
    reason: str = Field(..., description="Reason for routing to this model")
    answer: str = Field(..., description="The model's response")
    conversationId: Optional[str] = Field(default=None, description="Foundry conversation ID")
    metrics: Optional[ResponseMetrics] = Field(default=None, description="Latency and token usage metrics")
    sources: List[RagSource] = Field(default_factory=list, description="Grounding sources, when used")
    pendingResponseId: Optional[str] = Field(default=None, description="Background model response ID")
    pending: bool = Field(default=False, description="Whether a background response is still running")

class RagRequest(BaseModel):
    question: str = Field(..., description="Question to answer using indexed RAG documents")
    topK: Optional[int] = Field(default=None, ge=1, le=10, description="Number of chunks to retrieve")
    fastMode: bool = Field(
        default=True,
        description="Use optimized response budgets; retained for API compatibility",
    )

class RagResponse(BaseModel):
    answer: str = Field(..., description="Answer grounded in retrieved documents")
    modelUsed: str = Field(..., description="Name of the model used")
    indexUsed: str = Field(..., description="Azure AI Search index used")
    sources: List[RagSource] = Field(default_factory=list, description="Retrieved source chunks")

class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Image generation prompt")

class ImageGenerationResponse(BaseModel):
    answer: str = Field(..., description="Short assistant message")
    modelUsed: str = Field(..., description="Image generation model deployment")
    reason: str = Field(..., description="Routing reason")
    imageDataUrl: str = Field(..., description="Generated image as a data URL")

class ImageAnalysisRequest(BaseModel):
    prompt: str = Field(default="Describe this image.", description="Question or instruction about the image")
    imageDataUrl: str = Field(..., description="Uploaded image as a data URL")

class ImageAnalysisResponse(BaseModel):
    answer: str = Field(..., description="Model response about the image")
    modelUsed: str = Field(..., description="Vision-capable model deployment")
    reason: str = Field(..., description="Routing reason")

class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error description")
