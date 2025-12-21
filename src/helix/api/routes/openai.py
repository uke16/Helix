"""OpenAI-compatible API routes for Open WebUI integration.

This module handles chat completions by:
1. Managing consultant sessions
2. Running Claude Code instances for each turn
3. Returning responses in OpenAI format
"""

import asyncio
import os
import sys
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from jinja2 import Environment, FileSystemLoader

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from helix.claude_runner import ClaudeRunner

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
from ..session_manager import session_manager, SessionState

router = APIRouter(prefix="/v1", tags=["OpenAI Compatible"])

# Template environment
TEMPLATE_DIR = Path(__file__).parent.parent.parent.parent.parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))


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
async def chat_completions(request: ChatCompletionRequest, http_request: Request):
    """Handle chat completion with Claude Code consultant.
    
    This is the main integration point for Open WebUI.
    Each conversation maps to a session directory where
    Claude Code runs as the consultant.
    """
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    created = int(time.time())
    
    # Get messages
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    
    if not messages:
        return _error_response(completion_id, created, request.model, "No messages provided")
    
    # Get or create session
    session_id = session_manager.get_session_id_from_messages(messages)
    
    if not session_id:
        return _error_response(completion_id, created, request.model, "Could not determine session")
    
    # Check if session exists
    if not session_manager.session_exists(session_id):
        # New session - create it
        original_request = messages[0].get('content', '')
        session_manager.create_session(session_id, original_request)
    
    # Save current messages
    session_manager.save_messages(session_id, messages)
    
    # Extract state from messages
    conv_state = session_manager.extract_state_from_messages(messages)
    
    # Update session state
    session_manager.update_state(session_id, step=conv_state["step"])
    
    # Save context answers
    for key in ["what", "why", "constraints"]:
        if conv_state["answers"].get(key):
            session_manager.save_context(session_id, key, conv_state["answers"][key])
    
    # Generate CLAUDE.md for this session
    session_state = session_manager.get_state(session_id)
    context = session_manager.get_context(session_id)
    
    await _generate_session_claude_md(session_id, session_state, context)
    
    # Run Claude Code
    response_text = await _run_consultant(session_id, session_state)
    
    if request.stream:
        return StreamingResponse(
            _stream_response(completion_id, created, request.model, response_text),
            media_type="text/event-stream",
        )
    
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


async def _generate_session_claude_md(
    session_id: str, 
    state: SessionState, 
    context: dict[str, str]
) -> None:
    """Generate CLAUDE.md for the session from template."""
    template = jinja_env.get_template("consultant/session.md.j2")
    
    content = template.render(
        session_id=session_id,
        status=state.status,
        step=state.step,
        created_at=state.created_at.isoformat(),
        original_request=state.original_request,
        context=context,
        project_name=state.project_name or "Neues Projekt",
    )
    
    session_path = session_manager.get_session_path(session_id)
    (session_path / "CLAUDE.md").write_text(content)


async def _run_consultant(session_id: str, state: SessionState) -> str:
    """Run Claude Code for the consultant session."""
    session_path = session_manager.get_session_path(session_id)
    
    # Set NVM path
    nvm_path = "/home/aiuser01/.nvm/versions/node/v20.19.6/bin"
    os.environ["PATH"] = f"{nvm_path}:{os.environ.get('PATH', '')}"
    
    # Create runner
    runner = ClaudeRunner(
        claude_cmd=f"{nvm_path}/claude",
        use_stdbuf=True,
    )
    
    # Check availability
    available = await runner.check_availability()
    if not available:
        return "❌ Claude Code ist nicht verfügbar. Bitte später versuchen."
    
    # Run Claude Code in session directory
    try:
        result = await runner.run_phase(
            phase_dir=session_path,
            timeout=120,  # 2 minutes max for consultant
        )
        
        if result.success:
            # Read response from output
            response_file = session_path / "output" / "response.md"
            if response_file.exists():
                return response_file.read_text()
            else:
                # Claude didn't write response file - use stdout
                return result.stdout or "Ich habe deine Anfrage analysiert, aber keine Antwort generiert."
        else:
            # Error case
            return f"❌ Fehler bei der Verarbeitung:\n```\n{result.stderr[:500]}\n```"
            
    except asyncio.TimeoutError:
        return "⏱️ Timeout - die Verarbeitung hat zu lange gedauert."
    except Exception as e:
        return f"❌ Unerwarteter Fehler: {str(e)}"


def _error_response(completion_id: str, created: int, model: str, error: str) -> ChatCompletionResponse:
    """Create error response."""
    return ChatCompletionResponse(
        id=completion_id,
        created=created,
        model=model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(role="assistant", content=f"Fehler: {error}"),
                finish_reason="stop",
            )
        ],
        usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    )


async def _stream_response(
    completion_id: str,
    created: int,
    model: str,
    response_text: str,
):
    """Stream response in OpenAI format."""
    import json
    
    # Stream word by word
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
