"""OpenAI-compatible API routes for Open WebUI integration."""

import time
import uuid
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatCompletionChunk,
    ChatMessage,
    StreamChoice,
    StreamDelta,
    ModelInfo,
)

router = APIRouter(prefix="/v1", tags=["OpenAI Compatible"])


@router.get("/models")
async def list_models() -> dict:
    """List available models (OpenAI-compatible)."""
    models = [
        ModelInfo(
            id="helix-consultant",
            created=int(time.time()),
            owned_by="helix",
        ),
        ModelInfo(
            id="helix-developer",
            created=int(time.time()),
            owned_by="helix",
        ),
    ]
    return {
        "object": "list",
        "data": [m.model_dump() for m in models],
    }


@router.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """Handle chat completion (OpenAI-compatible).
    
    This endpoint makes HELIX work with Open WebUI.
    When stream=True, returns SSE stream.
    """
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    created = int(time.time())
    
    # Get the last user message
    user_message = ""
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break
    
    if request.stream:
        return StreamingResponse(
            _stream_response(completion_id, created, request.model, user_message),
            media_type="text/event-stream",
        )
    
    # Non-streaming response
    # For now, return a helpful message about using HELIX
    response_text = _generate_response(user_message, request.model)
    
    return ChatCompletionResponse(
        id=completion_id,
        created=created,
        model=request.model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(role="assistant", content=response_text),
                finish_reason="stop",
            )
        ],
        usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    )


def _generate_response(user_message: str, model: str) -> str:
    """Generate response based on user message.
    
    This is a simple implementation. In production, this would
    integrate with the Consultant for discussion or trigger execution.
    """
    msg_lower = user_message.lower()
    
    # Check for HELIX commands
    if any(word in msg_lower for word in ["erstelle", "create", "build", "implement"]):
        return (
            "I understand you want to create something. "
            "To start a HELIX project, I'll need more details:\n\n"
            "1. **What** do you want to build?\n"
            "2. **Why** is this needed?\n"
            "3. Any **constraints** or requirements?\n\n"
            "Once you provide these details, I can create a project specification "
            "and execute it through HELIX phases."
        )
    
    if any(word in msg_lower for word in ["status", "progress", "running"]):
        return (
            "To check project status, use:\n"
            "- `GET /helix/jobs` - List all jobs\n"
            "- `GET /helix/jobs/{job_id}` - Get specific job\n"
            "- `GET /helix/stream/{job_id}` - Live stream"
        )
    
    return (
        f"Hello! I'm HELIX, an AI development orchestrator.\n\n"
        f"I can help you:\n"
        f"- **Create features** - Describe what you need\n"
        f"- **Fix bugs** - Tell me about the issue\n"
        f"- **Research** - Explore technical topics\n\n"
        f"What would you like to work on?"
    )


async def _stream_response(
    completion_id: str,
    created: int,
    model: str,
    user_message: str,
):
    """Stream response chunks."""
    import json
    
    response_text = _generate_response(user_message, model)
    
    # Stream character by character (or word by word for speed)
    words = response_text.split(" ")
    
    for i, word in enumerate(words):
        chunk = ChatCompletionChunk(
            id=completion_id,
            created=created,
            model=model,
            choices=[
                StreamChoice(
                    index=0,
                    delta=StreamDelta(
                        role="assistant" if i == 0 else None,
                        content=word + " " if i < len(words) - 1 else word,
                    ),
                    finish_reason=None,
                )
            ],
        )
        yield f"data: {json.dumps(chunk.model_dump())}\n\n"
        # Small delay for visual effect
        import asyncio
        await asyncio.sleep(0.02)
    
    # Final chunk
    final_chunk = ChatCompletionChunk(
        id=completion_id,
        created=created,
        model=model,
        choices=[
            StreamChoice(
                index=0,
                delta=StreamDelta(),
                finish_reason="stop",
            )
        ],
    )
    yield f"data: {json.dumps(final_chunk.model_dump())}\n\n"
    yield "data: [DONE]\n\n"
