"""OpenAI-compatible API routes for Open WebUI integration.

This module handles chat completions by:
1. Managing consultant sessions
2. Running Claude Code instances for each turn
3. Returning responses in OpenAI format

Enhanced with ADR-013 live streaming:
- Tool call events are streamed as they happen
- No more waiting for complete response
- Prevents timeout in Open WebUI

Enhanced with ADR-029 session persistence:
- X-Conversation-ID header support for stable session mapping
- Same conversation always maps to same session
- Enables true multi-turn dialogs with context
"""

import asyncio
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Header, Request
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
    ]
    return {
        "object": "list",
        "data": [m.model_dump() for m in models],
    }


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    http_request: Request,
    x_conversation_id: Optional[str] = Header(None, alias="X-Conversation-ID"),
):
    """Handle chat completion with Claude Code consultant.

    This is the main integration point for Open WebUI.
    Each conversation maps to a session directory where
    Claude Code runs as the consultant.

    ADR-029: Extracts X-Conversation-ID header for persistent session mapping.
    When this header is present (sent by Open WebUI), the same conversation
    always maps to the same session, enabling true multi-turn dialogs.
    """
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    created = int(time.time())

    # Get messages
    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    if not messages:
        return _error_response(completion_id, created, request.model, "No messages provided")

    # Get first user message for session creation
    first_user_message = ""
    for msg in messages:
        if msg.get("role") == "user":
            first_user_message = msg.get("content", "")
            break

    if not first_user_message:
        return _error_response(completion_id, created, request.model, "No user message found")

    # ADR-029: Get or create session using X-Conversation-ID if available
    session_id, session_state = session_manager.get_or_create_session(
        first_message=first_user_message,
        conversation_id=x_conversation_id,
    )
    
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
    
    # Refresh session state after updates and generate CLAUDE.md
    session_state = session_manager.get_state(session_id) or session_state
    context = session_manager.get_context(session_id)

    await _generate_session_claude_md(session_id, session_state, context)

    session_path = session_manager.get_session_path(session_id)

    if request.stream:
        # Use live streaming - events are sent as Claude works
        return StreamingResponse(
            _run_consultant_streaming(
                session_path, completion_id, created, request.model
            ),
            media_type="text/event-stream",
        )

    # Non-streaming: wait for complete response
    response_text = await _run_consultant(session_id, session_state)

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
        helix_root="/home/aiuser01/helix-v4",
    )
    
    session_path = session_manager.get_session_path(session_id)
    (session_path / "CLAUDE.md").write_text(content)


async def _run_consultant_streaming(
    session_path: Path,
    completion_id: str,
    created: int,
    model: str,
) -> AsyncGenerator[str, None]:
    """Run Claude Code with live streaming to Open WebUI.

    This streams events as they happen:
    - Tool calls (Read, Write, Bash, etc.)
    - Progress text
    - Final response

    The key benefit: Open WebUI sees activity and doesn't timeout.

    Fixes (ADR-027):
    - FIX 1: Delete stale response.md before starting
    - FIX 2: Validate response.md timestamp
    - FIX 3: Don't read stale response after timeout/error
    """
    # === FIX 1: Delete stale response before starting ===
    response_file = session_path / "output" / "response.md"
    if response_file.exists():
        response_file.unlink()

    # Track start time for timestamp validation (FIX 2)
    start_time = time.time()

    # Set NVM path
    nvm_path = "/home/aiuser01/.nvm/versions/node/v20.19.6/bin"
    os.environ["PATH"] = f"{nvm_path}:{os.environ.get('PATH', '')}"

    # Create runner
    runner = ClaudeRunner(
        claude_cmd="/home/aiuser01/helix-v4/control/claude-wrapper.sh",
        use_stdbuf=True,
    )

    # Check availability
    available = await runner.check_availability()
    if not available:
        yield _make_chunk(completion_id, created, model, "Claude Code ist nicht verfuegbar.", role="assistant")
        yield _make_final_chunk(completion_id, created, model)
        yield "data: [DONE]\n\n"
        return

    # Stream initial status
    yield _make_chunk(completion_id, created, model, "[Starte Claude Code...]\n\n", role="assistant")

    # Track what we've sent
    last_tool: str | None = None
    stdout_buffer: list[str] = []

    async def on_output(stream: str, line: str) -> None:
        """Callback for each line of output."""
        nonlocal last_tool
        if stream == "stdout":
            stdout_buffer.append(line)

    # Run with streaming
    try:
        result = await runner.run_phase_streaming(
            phase_dir=session_path,
            on_output=on_output,
            timeout=600,
        )

        # === FIX 2: Validate response file timestamp ===
        response_text = None
        if response_file.exists():
            file_mtime = os.path.getmtime(response_file)
            if file_mtime >= start_time:
                # File was written AFTER we started - use it
                response_text = response_file.read_text()
            # else: File is stale, don't use it

        if not response_text:
            # Try to extract from stdout
            stdout = "\n".join(stdout_buffer)
            for line in stdout.strip().split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    data = json.loads(line)
                    if data.get("type") == "result" and data.get("result"):
                        response_text = data["result"]
                        break
                except json.JSONDecodeError:
                    continue

            if not response_text:
                response_text = stdout or "Verarbeitung abgeschlossen."

        # Stream the actual response
        yield _make_chunk(completion_id, created, model, "\n\n---\n\n")
        words = response_text.split(" ")
        for i, word in enumerate(words):
            content = word + " " if i < len(words) - 1 else word
            yield _make_chunk(completion_id, created, model, content)
            await asyncio.sleep(0.01)  # Small delay for smoother streaming

    except asyncio.TimeoutError:
        # === FIX 3a: Don't read stale response after timeout ===
        yield _make_chunk(completion_id, created, model,
            "\n\n**Timeout** - Verarbeitung hat zu lange gedauert. "
            "Bitte versuche es erneut.")
        yield _make_final_chunk(completion_id, created, model)
        yield "data: [DONE]\n\n"
        return  # Exit here, don't continue

    except Exception as e:
        # === FIX 3b: Don't read stale response after error ===
        yield _make_chunk(completion_id, created, model, f"\n\n**Fehler:** {str(e)}")
        yield _make_final_chunk(completion_id, created, model)
        yield "data: [DONE]\n\n"
        return  # Exit here, don't continue

    # Final chunk
    yield _make_final_chunk(completion_id, created, model)
    yield "data: [DONE]\n\n"


def _make_chunk(
    completion_id: str,
    created: int,
    model: str,
    content: str,
    role: str | None = None,
) -> str:
    """Create an SSE chunk in OpenAI format."""
    chunk = ChatCompletionChunk(
        id=completion_id,
        created=created,
        model=model,
        choices=[
            StreamChoice(
                index=0,
                delta=StreamDelta(role=role, content=content),
                finish_reason=None,
            )
        ],
    )
    return f"data: {json.dumps(chunk.model_dump())}\n\n"


def _make_final_chunk(completion_id: str, created: int, model: str) -> str:
    """Create the final SSE chunk with finish_reason."""
    chunk = ChatCompletionChunk(
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
    return f"data: {json.dumps(chunk.model_dump())}\n\n"


async def _run_consultant(session_id: str, state: SessionState) -> str:
    """Run Claude Code for the consultant session (non-streaming)."""
    session_path = session_manager.get_session_path(session_id)
    
    # Set NVM path
    nvm_path = "/home/aiuser01/.nvm/versions/node/v20.19.6/bin"
    os.environ["PATH"] = f"{nvm_path}:{os.environ.get('PATH', '')}"
    
    # Create runner
    runner = ClaudeRunner(
        claude_cmd="/home/aiuser01/helix-v4/control/claude-wrapper.sh",
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
            timeout=600,  # 10 minutes max for consultant
        )
        
        if result.success:
            # Read response from output
            response_file = session_path / "output" / "response.md"
            if response_file.exists():
                return response_file.read_text()
            else:
                # Claude didn't write response file - parse stdout
                # With stream-json output, we need to extract the result
                stdout = result.stdout or ""
                
                # Try to parse stream-json format
                for line in stdout.strip().split("\n"):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("type") == "result" and data.get("result"):
                            return data["result"]
                    except json.JSONDecodeError:
                        continue
                
                # Fallback to raw stdout if no result found
                return stdout or "Ich habe deine Anfrage analysiert, aber keine Antwort generiert."
        else:
            # Error case - also try to parse stream-json for error message
            stderr = result.stderr or ""
            stdout = result.stdout or ""
            
            # Try to find error in stream-json
            for line in (stdout + "\n" + stderr).strip().split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    data = json.loads(line)
                    if data.get("type") == "result" and data.get("is_error"):
                        return f"❌ Fehler: {data.get('result', 'Unbekannter Fehler')}"
                except json.JSONDecodeError:
                    continue
            
            return f"❌ Fehler bei der Verarbeitung:\n```\n{stderr[:500]}\n```"
            
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


## Legacy _stream_response removed - replaced by _run_consultant_streaming
# The new streaming function streams events DURING execution, not after
