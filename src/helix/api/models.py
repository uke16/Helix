"""Pydantic models for HELIX API."""

from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Status of a HELIX job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PhaseStatus(str, Enum):
    """Status of a single phase."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# OpenAI-compatible models
class ChatMessage(BaseModel):
    """OpenAI-compatible chat message."""
    role: str = Field(..., description="Role: system, user, or assistant")
    content: str = Field(..., description="Message content")


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""
    model: str = Field(default="helix-consultant", description="Model to use")
    messages: list[ChatMessage] = Field(..., description="Conversation messages")
    stream: bool = Field(default=False, description="Enable streaming")
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1)


class ChatCompletionChoice(BaseModel):
    """Single choice in completion response."""
    index: int
    message: ChatMessage
    finish_reason: str | None = "stop"


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: dict[str, int] | None = None


class StreamDelta(BaseModel):
    """Delta for streaming response."""
    role: str | None = None
    content: str | None = None


class StreamChoice(BaseModel):
    """Choice in streaming response."""
    index: int
    delta: StreamDelta
    finish_reason: str | None = None


class ChatCompletionChunk(BaseModel):
    """OpenAI-compatible streaming chunk."""
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: list[StreamChoice]


# HELIX-specific models
class DiscussRequest(BaseModel):
    """Request to start a consultant discussion."""
    message: str = Field(..., description="User's request/question")
    project_type: str = Field(default="feature", description="Type: feature, bugfix, research")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")


class ExecuteRequest(BaseModel):
    """Request to execute a HELIX project."""
    project_path: str = Field(..., description="Path to project directory")
    phase_filter: list[str] | None = Field(default=None, description="Run only these phases")


class JobInfo(BaseModel):
    """Information about a HELIX job."""
    job_id: str
    status: JobStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    current_phase: str | None = None
    phases: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class PhaseEvent(BaseModel):
    """SSE event for phase progress."""
    event_type: str  # phase_start, output, file_created, phase_end, error
    phase_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ModelInfo(BaseModel):
    """Model information for /v1/models."""
    id: str
    object: str = "model"
    created: int
    owned_by: str = "helix"


# Remote Control models
class SpawnClaudeRequest(BaseModel):
    """Request to spawn a new Claude instance."""
    prompt: str = Field(..., description="Prompt to send to Claude", min_length=1)
    working_dir: str | None = Field(default=None, description="Working directory")
    timeout: int = Field(default=600, ge=10, le=3600, description="Timeout in seconds")
    system_prompt: str | None = Field(default=None, description="System prompt override")
    output_format: str = Field(default="text", description="Output format: text, json, stream-json")


class ReadLogsRequest(BaseModel):
    """Request to read log files."""
    log_type: str = Field(default="api", description="Log type: api, helix, helix-test")
    lines: int = Field(default=100, ge=1, le=5000, description="Number of lines to return")
    search: str | None = Field(default=None, description="Filter lines containing this string")


class ControlCommandRequest(BaseModel):
    """Request to run a HELIX control command."""
    command: str = Field(..., description="Control command: status, health, logs")
