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
- X-OpenWebUI-Chat-Id header support for stable session mapping
- Same conversation always maps to same session
- Enables true multi-turn dialogs with context

Refactored with ADR-034 LLM-Native flow:
- Step detection moved from Python to LLM
- LLM sets step markers in response (<!-- STEP: X -->)
- Python extracts and logs the step, no longer controls flow
"""

import asyncio
import logging
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
from helix.enforcement.response_enforcer import ResponseEnforcer
from helix.enforcement.validators import (
    StepMarkerValidator,
    ADRStructureValidator,
    FileExistenceValidator,
)

# HELIX root for file existence validation
HELIX_ROOT = Path("/home/aiuser01/helix-v4")

from ..middleware import InputValidator, limiter, CHAT_COMPLETIONS_LIMIT
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
# NOTE: Rate limiting disabled for streaming endpoint (slowapi incompatible with StreamingResponse)
# Rate limiting should be handled at the reverse proxy level (nginx/traefik)
async def chat_completions(
    request: Request,  # MUST be named 'request' for slowapi rate limiter
    chat_request: ChatCompletionRequest,
    x_chat_id: Optional[str] = Header(None, alias="X-OpenWebUI-Chat-Id"),
):
    """Handle chat completion with Claude Code consultant.

    This is the main integration point for Open WebUI.
    Each conversation maps to a session directory where
    Claude Code runs as the consultant.

    ADR-029: Extracts X-OpenWebUI-Chat-Id header for persistent session mapping.
    When this header is present (sent by Open WebUI), the same conversation
    always maps to the same session, enabling true multi-turn dialogs.

    ADR-034: Step detection is now handled by the LLM, not by Python.
    The LLM reports its current step via markers in its response.

    ADR-035: Rate limiting (10/min) and input validation for security.
    """
    # ADR-035: Validate input before processing
    InputValidator.validate_chat_request(chat_request)

    completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    created = int(time.time())

    # Get messages
    messages = [{"role": m.role, "content": m.content} for m in chat_request.messages]

    if not messages:
        return _error_response(completion_id, created, chat_request.model, "No messages provided")

    # Get first user message for session creation
    first_user_message = ""
    for msg in messages:
        if msg.get("role") == "user":
            first_user_message = msg.get("content", "")
            break

    if not first_user_message:
        return _error_response(completion_id, created, chat_request.model, "No user message found")

    # ADR-029: Get or create session using X-OpenWebUI-Chat-Id if available
    session_id, session_state = session_manager.get_or_create_session(
        first_message=first_user_message,
        conversation_id=x_chat_id,
    )

    # Save current messages
    session_manager.save_messages(session_id, messages)

    # ADR-034: Extract only basic metadata, step is not detected here anymore
    conv_state = session_manager.extract_state_from_messages(messages)
    # conv_state now only contains: original_request, message_count
    # Step detection happens AFTER LLM response via extract_step_from_response()

    # Get existing context (what, why, constraints from previous turns)
    context = session_manager.get_context(session_id)

    await _generate_session_claude_md(session_id, session_state, context, messages=messages)  # Bug-006: Pass messages

    session_path = session_manager.get_session_path(session_id)

    if chat_request.stream:
        # Use live streaming - events are sent as Claude works
        return StreamingResponse(
            _run_consultant_streaming(
                session_path, session_id, completion_id, created, chat_request.model
            ),
            media_type="text/event-stream",
        )

    # Non-streaming: wait for complete response
    response_text = await _run_consultant(session_id, session_state)

    # ADR-034: Extract step from LLM response and update session
    _update_step_from_response(session_id, response_text)

    return ChatCompletionResponse(
        id=completion_id,
        created=created,
        model=chat_request.model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(role="assistant", content=response_text),
                finish_reason="stop",
            )
        ],
        usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    )


def _update_step_from_response(session_id: str, response_text: str) -> str | None:
    """Extract step from LLM response and update session state.

    ADR-034: The LLM sets a step marker at the end of its response:
    <!-- STEP: what|why|constraints|generate|finalize|done -->

    This function extracts the step and updates the session state.
    The step is for observability only, not for flow control.

    Args:
        session_id: The session to update.
        response_text: The LLM response text containing the step marker.

    Returns:
        The extracted step, or None if no marker found.
    """
    step = session_manager.extract_step_from_response(response_text)
    if step:
        session_manager.update_state(session_id, step=step)
    return step


async def _generate_session_claude_md(
    session_id: str,
    state: SessionState,
    context: dict[str, str],
    messages: list[dict] | None = None,
) -> None:
    """Generate CLAUDE.md for the session from template.
    
    Bug-006 Fix: Now includes full chat history so Claude sees
    all messages, not just the original request.
    """
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
        messages=messages or [],  # Bug-006: Pass chat history to template
    )

    session_path = session_manager.get_session_path(session_id)
    (session_path / "CLAUDE.md").write_text(content)


async def _run_consultant_streaming(
    session_path: Path,
    session_id: str,
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

    ADR-034:
    - After streaming, extract step marker from response and update session
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
    response_text = None
    try:
        result = await runner.run_phase_streaming(
            phase_dir=session_path,
            on_output=on_output,
            timeout=600,
        )

        # === FIX 2: Validate response file timestamp ===
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

            # Second: Extract last assistant text message (FIX: bug-raw-jsonl-fallback)
            if not response_text:
                for line in reversed(stdout.strip().split("\n")):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("type") == "assistant":
                            msg = data.get("message", {})
                            content_blocks = msg.get("content", [])
                            for block in content_blocks:
                                if block.get("type") == "text" and block.get("text"):
                                    response_text = block["text"]
                                    break
                            if response_text:
                                break
                    except json.JSONDecodeError:
                        continue

            # Final fallback - clean message, NOT raw JSONL
            if not response_text:
                response_text = "Verarbeitung abgeschlossen."

        # =====================================================================
        # ADR-038: Full Response Enforcement with all 3 Validators
        # =====================================================================
        logger = logging.getLogger(__name__)

        # Create enforcer with all validators
        enforcer = ResponseEnforcer(
            runner=runner,
            max_retries=2,
            validators=[
                StepMarkerValidator(),
                ADRStructureValidator(),
                FileExistenceValidator(helix_root=HELIX_ROOT),
            ]
        )

        # Validation context for FileExistenceValidator
        validation_context = {"helix_root": HELIX_ROOT}

        # Run full enforcement pipeline
        enforcement_result = await enforcer.enforce_streaming_response(
            response=response_text,
            phase_dir=session_path,
            runner=runner,
            context=validation_context,
            max_retries=2,
        )

        # Log enforcement results
        if enforcement_result.fallback_applied:
            logger.info(
                f"ADR-038: Fallback applied for session {session_id}, "
                f"issues: {[i.code for i in enforcement_result.issues]}"
            )
        elif enforcement_result.attempts > 1:
            logger.info(
                f"ADR-038: Retry succeeded for session {session_id} "
                f"after {enforcement_result.attempts} attempts"
            )

        # Check if enforcement completely failed
        if not enforcement_result.success:
            # Stream error information to user
            logger.error(
                f"ADR-038: Enforcement failed for session {session_id}: "
                f"{[i.code for i in enforcement_result.issues]}"
            )
            yield _make_chunk(completion_id, created, model, "\n\n---\n\n")
            yield _make_chunk(
                completion_id, created, model,
                "⚠️ **Hinweis:** Die Antwort konnte nicht vollständig validiert werden.\n\n"
            )
            # Still stream the response (best effort)
            response_text = enforcement_result.response
        else:
            response_text = enforcement_result.response

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

    # ADR-034: Extract step from response and update session state
    if response_text:
        _update_step_from_response(session_id, response_text)

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
    """Run Claude Code for the consultant session (non-streaming).

    ADR-038: Full enforcement with all 3 validators, retry logic, and fallbacks.
    """
    session_path = session_manager.get_session_path(session_id)
    logger = logging.getLogger(__name__)

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
        return "Claude Code ist nicht verfuegbar. Bitte spaeter versuchen."

    # Run Claude Code in session directory
    try:
        result = await runner.run_phase(
            phase_dir=session_path,
            timeout=600,  # 10 minutes max for consultant
        )

        response_text = None

        if result.success:
            # Read response from output
            response_file = session_path / "output" / "response.md"
            if response_file.exists():
                response_text = response_file.read_text()
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
                            response_text = data["result"]
                            break
                    except json.JSONDecodeError:
                        continue

                # Fallback to raw stdout if no result found
                if not response_text:
                    response_text = stdout or "Ich habe deine Anfrage analysiert, aber keine Antwort generiert."
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
                        return f"Fehler: {data.get('result', 'Unbekannter Fehler')}"
                except json.JSONDecodeError:
                    continue

            return f"Fehler bei der Verarbeitung:\n```\n{stderr[:500]}\n```"

        # =====================================================================
        # ADR-038: Full Response Enforcement with all 3 Validators
        # =====================================================================
        enforcer = ResponseEnforcer(
            runner=runner,
            max_retries=2,
            validators=[
                StepMarkerValidator(),
                ADRStructureValidator(),
                FileExistenceValidator(helix_root=HELIX_ROOT),
            ]
        )

        # Validation context for FileExistenceValidator
        validation_context = {"helix_root": HELIX_ROOT}

        # Run full enforcement pipeline
        enforcement_result = await enforcer.enforce_streaming_response(
            response=response_text,
            phase_dir=session_path,
            runner=runner,
            context=validation_context,
            max_retries=2,
        )

        # Log enforcement results
        if enforcement_result.fallback_applied:
            logger.info(
                f"ADR-038: Fallback applied for session {session_id}, "
                f"issues: {[i.code for i in enforcement_result.issues]}"
            )
        elif enforcement_result.attempts > 1:
            logger.info(
                f"ADR-038: Retry succeeded for session {session_id} "
                f"after {enforcement_result.attempts} attempts"
            )

        # Check if enforcement completely failed
        if not enforcement_result.success:
            logger.error(
                f"ADR-038: Enforcement failed for session {session_id}: "
                f"{[i.code for i in enforcement_result.issues]}"
            )
            # Return response with warning
            return (
                enforcement_result.response +
                "\n\n---\n\n⚠️ **Hinweis:** Die Antwort konnte nicht vollständig validiert werden."
            )

        return enforcement_result.response

    except asyncio.TimeoutError:
        return "Timeout - die Verarbeitung hat zu lange gedauert."
    except Exception as e:
        return f"Unerwarteter Fehler: {str(e)}"


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
