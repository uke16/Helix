# HELIX v4 Bootstrap - Phase 12: REST API

Create the FastAPI-based REST API for HELIX v4 with WebSocket streaming.

## Target Directories

- API code: `/home/aiuser01/helix-v4/src/helix/api/`
- Docker: `/home/aiuser01/helix-v4/docker/helix-api/`
- Config: `/home/aiuser01/helix-v4/config/api.yaml`

## Architecture Overview

```
┌──────────────┐     ┌──────────────────────────────────────────────┐
│  Open WebUI  │     │  HELIX API (FastAPI)                         │
│  (Browser)   │────►│  Port 8100                                   │
└──────────────┘     │                                              │
                     │  POST /api/v1/discuss      - Chat with Meta  │
                     │  POST /api/v1/projects     - Create project  │
                     │  GET  /api/v1/projects     - List projects   │
                     │  GET  /api/v1/projects/{id} - Get project    │
                     │  POST /api/v1/projects/{id}/execute - Start  │
                     │  GET  /api/v1/projects/{id}/status  - Status │
                     │  GET  /api/v1/stream/{id}  - SSE streaming   │
                     └──────────────────────────────────────────────┘
                                        │
                     ┌──────────────────┼──────────────────┐
                     ▼                  ▼                  ▼
              ┌────────────┐    ┌────────────┐    ┌────────────┐
              │ PostgreSQL │    │ Orchestrator│    │Claude Code │
              │ (Jobs/State)│    │            │    │ Instances  │
              └────────────┘    └────────────┘    └────────────┘
```

## Files to Create

### 1. `/home/aiuser01/helix-v4/src/helix/api/__init__.py`

```python
from .main import app, create_app

__all__ = ["app", "create_app"]
```

### 2. `/home/aiuser01/helix-v4/src/helix/api/main.py`

FastAPI application setup:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .routes import discuss, projects, execute, stream
from .database import init_db, close_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()

def create_app() -> FastAPI:
    app = FastAPI(
        title="HELIX v4 API",
        description="AI Development Orchestration System",
        version="4.0.0",
        lifespan=lifespan,
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(discuss.router, prefix="/api/v1", tags=["discuss"])
    app.include_router(projects.router, prefix="/api/v1", tags=["projects"])
    app.include_router(execute.router, prefix="/api/v1", tags=["execute"])
    app.include_router(stream.router, prefix="/api/v1", tags=["stream"])
    
    return app

app = create_app()
```

### 3. `/home/aiuser01/helix-v4/src/helix/api/models.py`

Pydantic models:

```python
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional

class ProjectStatus(str, Enum):
    DRAFT = "draft"
    DISCUSSING = "discussing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

class PhaseStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

# Request Models
class DiscussRequest(BaseModel):
    project_id: Optional[str] = None
    message: str
    user_id: str

class CreateProjectRequest(BaseModel):
    name: str
    description: str
    project_type: str = "feature"
    user_id: str

class ExecuteRequest(BaseModel):
    start_phase: Optional[str] = None
    model: str = "claude-opus-4"
    user_id: str

# Response Models
class DiscussResponse(BaseModel):
    project_id: str
    message: str
    phase: str  # "discussion", "clarification", "documentation"
    artifacts: list[str] = []  # Created files (ADR, spec)

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    status: ProjectStatus
    current_phase: Optional[str]
    phases: list[dict]
    created_at: datetime
    updated_at: datetime
    user_id: str

class ExecuteResponse(BaseModel):
    project_id: str
    job_id: str
    status: str
    stream_url: str

class StreamEvent(BaseModel):
    event_type: str  # "phase_start", "phase_end", "output", "file", "error", "cost"
    timestamp: datetime
    phase: Optional[str]
    data: dict

# Database Models
class Job(BaseModel):
    id: str
    project_id: str
    user_id: str
    status: str
    current_phase: Optional[str]
    started_at: datetime
    finished_at: Optional[datetime]
    error: Optional[str]
```

### 4. `/home/aiuser01/helix-v4/src/helix/api/config.py`

```python
from pydantic_settings import BaseSettings
from pathlib import Path

class APISettings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8100
    debug: bool = False
    
    # Database
    database_url: str = "postgresql+asyncpg://helix:helix@localhost:5434/helix"
    
    # Limits
    max_projects_per_user: int = 10
    max_concurrent_jobs: int = 5
    
    # Streaming
    stream_buffer_size: int = 100
    stream_heartbeat_interval: int = 15
    
    # Paths
    projects_dir: Path = Path("/home/aiuser01/helix-v4/projects/external")
    
    class Config:
        env_prefix = "HELIX_API_"
        env_file = ".env"

settings = APISettings()
```

### 5. `/home/aiuser01/helix-v4/src/helix/api/database.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, DateTime, Text, Enum as SQLEnum
from datetime import datetime
import enum

from .config import settings

class Base(DeclarativeBase):
    pass

class JobStatus(enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobModel(Base):
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    status = Column(SQLEnum(JobStatus), default=JobStatus.QUEUED)
    current_phase = Column(String, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)

class ProjectModel(Base):
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    project_type = Column(String, default="feature")
    status = Column(String, default="draft")
    user_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def close_db():
    await engine.dispose()

async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
```

### 6. `/home/aiuser01/helix-v4/src/helix/api/auth.py`

```python
from fastapi import HTTPException, Header
from typing import Optional
import jwt

# Open WebUI passes user info in headers
# For now, trust the user_id header (internal network)
# TODO: Add JWT validation for production

async def get_current_user(
    x_user_id: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
) -> str:
    """Extract user from Open WebUI headers."""
    
    if x_user_id:
        return x_user_id
    
    if authorization and authorization.startswith("Bearer "):
        # TODO: Validate JWT from Open WebUI
        token = authorization[7:]
        # For now, just extract user_id claim
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload.get("sub", "anonymous")
        except:
            pass
    
    raise HTTPException(status_code=401, detail="User ID required")
```

### 7. `/home/aiuser01/helix-v4/src/helix/api/routes/__init__.py`

```python
from . import discuss, projects, execute, stream
```

### 8. `/home/aiuser01/helix-v4/src/helix/api/routes/discuss.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from ..models import DiscussRequest, DiscussResponse
from ..database import get_session, ProjectModel
from ..auth import get_current_user
from ...consultant import ConsultantMeeting
from ...llm_client import LLMClient

router = APIRouter()

@router.post("/discuss", response_model=DiscussResponse)
async def discuss(
    request: DiscussRequest,
    user_id: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Have a discussion with the Meta-Consultant.
    
    Stage 1: Natural language discussion about features
    - Ask clarifying questions
    - Discuss implications
    - Eventually create ADR and spec.yaml
    """
    
    # Get or create project for this discussion
    if request.project_id:
        project = await session.get(ProjectModel, request.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not your project")
    else:
        # New discussion - create draft project
        project = ProjectModel(
            id=str(uuid.uuid4()),
            name="New Discussion",
            description=request.message[:200],
            status="discussing",
            user_id=user_id,
        )
        session.add(project)
        await session.commit()
    
    # Run consultant discussion
    llm_client = LLMClient()
    # TODO: Implement discussion logic with ConsultantMeeting
    # For now, return placeholder
    
    return DiscussResponse(
        project_id=project.id,
        message="Discussion started. What specific aspects would you like to explore?",
        phase="discussion",
        artifacts=[],
    )
```

### 9. `/home/aiuser01/helix-v4/src/helix/api/routes/projects.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from pathlib import Path

from ..models import CreateProjectRequest, ProjectResponse
from ..database import get_session, ProjectModel
from ..auth import get_current_user
from ..config import settings

router = APIRouter()

@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    request: CreateProjectRequest,
    user_id: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create a new HELIX project."""
    
    # Check user's project count
    result = await session.execute(
        select(ProjectModel).where(ProjectModel.user_id == user_id)
    )
    user_projects = result.scalars().all()
    
    if len(user_projects) >= settings.max_projects_per_user:
        raise HTTPException(
            status_code=400, 
            detail=f"Maximum {settings.max_projects_per_user} projects per user"
        )
    
    # Create project
    project_id = str(uuid.uuid4())
    project = ProjectModel(
        id=project_id,
        name=request.name,
        description=request.description,
        project_type=request.project_type,
        status="draft",
        user_id=user_id,
    )
    
    # Create project directory
    project_dir = settings.projects_dir / user_id / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    
    session.add(project)
    await session.commit()
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        current_phase=None,
        phases=[],
        created_at=project.created_at,
        updated_at=project.updated_at,
        user_id=project.user_id,
    )

@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    user_id: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List all projects for current user."""
    
    result = await session.execute(
        select(ProjectModel).where(ProjectModel.user_id == user_id)
    )
    projects = result.scalars().all()
    
    return [
        ProjectResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            status=p.status,
            current_phase=None,
            phases=[],
            created_at=p.created_at,
            updated_at=p.updated_at,
            user_id=p.user_id,
        )
        for p in projects
    ]

@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    user_id: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get project details."""
    
    project = await session.get(ProjectModel, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your project")
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        current_phase=None,
        phases=[],
        created_at=project.created_at,
        updated_at=project.updated_at,
        user_id=project.user_id,
    )
```

### 10. `/home/aiuser01/helix-v4/src/helix/api/routes/execute.py`

```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import asyncio

from ..models import ExecuteRequest, ExecuteResponse
from ..database import get_session, ProjectModel, JobModel, JobStatus
from ..auth import get_current_user
from ..queue import job_queue
from ..config import settings

router = APIRouter()

@router.post("/projects/{project_id}/execute", response_model=ExecuteResponse)
async def execute_project(
    project_id: str,
    request: ExecuteRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Start executing a HELIX project.
    
    Stage 2: After discussion is complete, run the implementation workflow.
    """
    
    # Get project
    project = await session.get(ProjectModel, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your project")
    
    if project.status not in ["ready", "paused", "failed"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Project status '{project.status}' cannot be executed"
        )
    
    # Create job
    job_id = str(uuid.uuid4())
    job = JobModel(
        id=job_id,
        project_id=project_id,
        user_id=user_id,
        status=JobStatus.QUEUED,
    )
    
    session.add(job)
    project.status = "running"
    await session.commit()
    
    # Queue job for execution
    await job_queue.enqueue(job_id, project_id, request.start_phase, request.model)
    
    return ExecuteResponse(
        project_id=project_id,
        job_id=job_id,
        status="queued",
        stream_url=f"/api/v1/stream/{job_id}",
    )

@router.post("/projects/{project_id}/cancel")
async def cancel_execution(
    project_id: str,
    user_id: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Cancel a running project execution."""
    
    project = await session.get(ProjectModel, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your project")
    
    # TODO: Implement cancellation via job queue
    
    return {"status": "cancelled"}
```

### 11. `/home/aiuser01/helix-v4/src/helix/api/routes/stream.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import json
from datetime import datetime

from ..database import get_session, JobModel
from ..auth import get_current_user
from ..queue import job_queue
from ..config import settings

router = APIRouter()

@router.get("/stream/{job_id}")
async def stream_job(
    job_id: str,
    user_id: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Stream job execution events via Server-Sent Events (SSE).
    
    Event types:
    - phase_start: Phase execution started
    - phase_end: Phase execution completed
    - output: Claude Code output (filtered by config)
    - file: File created/modified
    - error: Error occurred
    - cost: Token/cost update
    - heartbeat: Keep-alive ping
    """
    
    job = await session.get(JobModel, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your job")
    
    async def event_generator():
        """Generate SSE events from job queue."""
        
        # Subscribe to job events
        async for event in job_queue.subscribe(job_id):
            # Format as SSE
            event_data = {
                "event_type": event["type"],
                "timestamp": datetime.utcnow().isoformat(),
                "phase": event.get("phase"),
                "data": event.get("data", {}),
            }
            
            yield f"event: {event['type']}\n"
            yield f"data: {json.dumps(event_data)}\n\n"
            
            # Check if job finished
            if event["type"] in ["completed", "failed", "cancelled"]:
                break
        
        # Send final event
        yield f"event: done\ndata: {{}}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
```

### 12. `/home/aiuser01/helix-v4/src/helix/api/queue.py`

```python
from dataclasses import dataclass
from typing import AsyncGenerator, Optional
import asyncio
import uuid
from datetime import datetime

from ..orchestrator import Orchestrator
from ..observability import HelixLogger, MetricsCollector
from .config import settings

@dataclass
class QueuedJob:
    id: str
    project_id: str
    start_phase: Optional[str]
    model: str
    queued_at: datetime

class JobQueue:
    """
    Simple async job queue for HELIX executions.
    
    For production, consider using:
    - Redis + asyncio for distributed queue
    - PostgreSQL NOTIFY/LISTEN for events
    """
    
    def __init__(self):
        self._queue: asyncio.Queue[QueuedJob] = asyncio.Queue()
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._running_jobs: dict[str, asyncio.Task] = {}
        self._worker_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the job worker."""
        self._worker_task = asyncio.create_task(self._worker())
    
    async def stop(self):
        """Stop the job worker."""
        if self._worker_task:
            self._worker_task.cancel()
    
    async def enqueue(
        self, 
        job_id: str, 
        project_id: str, 
        start_phase: Optional[str],
        model: str,
    ):
        """Add job to queue."""
        job = QueuedJob(
            id=job_id,
            project_id=project_id,
            start_phase=start_phase,
            model=model,
            queued_at=datetime.utcnow(),
        )
        await self._queue.put(job)
        await self._emit(job_id, {"type": "queued"})
    
    async def subscribe(self, job_id: str) -> AsyncGenerator[dict, None]:
        """Subscribe to job events."""
        queue: asyncio.Queue[dict] = asyncio.Queue()
        
        if job_id not in self._subscribers:
            self._subscribers[job_id] = []
        self._subscribers[job_id].append(queue)
        
        try:
            while True:
                event = await asyncio.wait_for(
                    queue.get(), 
                    timeout=settings.stream_heartbeat_interval
                )
                yield event
                
                if event["type"] in ["completed", "failed", "cancelled"]:
                    break
        except asyncio.TimeoutError:
            # Send heartbeat
            yield {"type": "heartbeat"}
        finally:
            self._subscribers[job_id].remove(queue)
    
    async def _emit(self, job_id: str, event: dict):
        """Emit event to all subscribers."""
        if job_id in self._subscribers:
            for queue in self._subscribers[job_id]:
                await queue.put(event)
    
    async def _worker(self):
        """Process jobs from queue."""
        while True:
            job = await self._queue.get()
            
            # Check concurrent limit
            while len(self._running_jobs) >= settings.max_concurrent_jobs:
                await asyncio.sleep(1)
            
            # Start job
            task = asyncio.create_task(self._run_job(job))
            self._running_jobs[job.id] = task
    
    async def _run_job(self, job: QueuedJob):
        """Execute a single job."""
        try:
            await self._emit(job.id, {"type": "started"})
            
            # Create orchestrator
            project_dir = settings.projects_dir / job.project_id
            orchestrator = Orchestrator()
            
            # Run with event callbacks
            async def on_phase_start(phase: str):
                await self._emit(job.id, {
                    "type": "phase_start",
                    "phase": phase,
                })
            
            async def on_phase_end(phase: str, success: bool):
                await self._emit(job.id, {
                    "type": "phase_end",
                    "phase": phase,
                    "data": {"success": success},
                })
            
            async def on_output(phase: str, output: str):
                await self._emit(job.id, {
                    "type": "output",
                    "phase": phase,
                    "data": {"output": output},
                })
            
            # Execute
            result = await orchestrator.run_project(
                project_dir,
                start_phase=job.start_phase,
                model=job.model,
                callbacks={
                    "on_phase_start": on_phase_start,
                    "on_phase_end": on_phase_end,
                    "on_output": on_output,
                },
            )
            
            await self._emit(job.id, {
                "type": "completed",
                "data": {"result": result},
            })
            
        except Exception as e:
            await self._emit(job.id, {
                "type": "failed",
                "data": {"error": str(e)},
            })
        finally:
            del self._running_jobs[job.id]

# Global queue instance
job_queue = JobQueue()
```

### 13. `/home/aiuser01/helix-v4/config/api.yaml`

```yaml
# HELIX v4 API Configuration

server:
  host: "0.0.0.0"
  port: 8100
  debug: false

database:
  url: "postgresql+asyncpg://helix:helix@helix-postgres:5432/helix"
  pool_size: 10
  max_overflow: 20

limits:
  max_projects_per_user: 10
  max_concurrent_jobs: 5
  max_job_duration_minutes: 60

streaming:
  buffer_size: 100
  heartbeat_interval: 15
  # What to stream from Claude Code
  output_filter:
    include:
      - phase_start
      - phase_end
      - file_created
      - file_modified
      - error
      - cost_update
    # Optionally filter Claude Code output
    claude_output:
      enabled: true
      max_lines_per_event: 50
      filter_patterns:
        - "^\\s*$"  # Empty lines
        - "^Thinking\\.\\.\\."  # Thinking messages

auth:
  # Trust Open WebUI headers (internal network)
  trust_proxy_headers: true
  # Future: JWT validation
  jwt_secret: null
  jwt_algorithm: "HS256"

paths:
  projects_dir: "/home/aiuser01/helix-v4/projects/external"
  logs_dir: "/home/aiuser01/helix-v4/logs"
```

### 14. `/home/aiuser01/helix-v4/docker/helix-api/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for Claude Code
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g @anthropic-ai/claude-code

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/helix /app/helix
COPY config /app/config
COPY templates /app/templates

# Environment
ENV PYTHONPATH=/app
ENV HELIX_API_HOST=0.0.0.0
ENV HELIX_API_PORT=8100

EXPOSE 8100

CMD ["uvicorn", "helix.api.main:app", "--host", "0.0.0.0", "--port", "8100"]
```

### 15. `/home/aiuser01/helix-v4/docker/helix-api/docker-compose.yaml`

```yaml
version: "3.8"

services:
  helix-api:
    build:
      context: ../..
      dockerfile: docker/helix-api/Dockerfile
    container_name: helix-api
    ports:
      - "8100:8100"
    environment:
      - HELIX_API_DATABASE_URL=postgresql+asyncpg://helix:helix@helix-postgres:5432/helix
      - HELIX_OPENROUTER_API_KEY=${HELIX_OPENROUTER_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
    volumes:
      - ../../projects:/app/projects
      - ../../logs:/app/logs
      - ../../skills:/app/skills
    depends_on:
      helix-postgres:
        condition: service_healthy
    networks:
      - helix-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8100/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  helix-postgres:
    image: postgres:16-alpine
    container_name: helix-postgres
    environment:
      POSTGRES_USER: helix
      POSTGRES_PASSWORD: helix
      POSTGRES_DB: helix
    volumes:
      - helix-postgres-data:/var/lib/postgresql/data
    ports:
      - "5434:5432"
    networks:
      - helix-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U helix"]
      interval: 10s
      timeout: 5s
      retries: 5

networks:
  helix-network:
    driver: bridge

volumes:
  helix-postgres-data:
```

### 16. `/home/aiuser01/helix-v4/docker/helix-api/requirements.txt`

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-jose[cryptography]>=3.3.0
httpx>=0.24.0
jinja2>=3.0.0
pyyaml>=6.0.0
```

## Instructions

1. Create the directory structure:
   - `/home/aiuser01/helix-v4/src/helix/api/`
   - `/home/aiuser01/helix-v4/src/helix/api/routes/`
   - `/home/aiuser01/helix-v4/docker/helix-api/`

2. Create all 16 files with the exact content shown above

3. All code in English

4. Create `output/result.json` when done

## Output

```json
{
  "status": "success",
  "files_created": [
    "src/helix/api/__init__.py",
    "src/helix/api/main.py",
    "src/helix/api/models.py",
    "src/helix/api/config.py",
    "src/helix/api/database.py",
    "src/helix/api/auth.py",
    "src/helix/api/queue.py",
    "src/helix/api/routes/__init__.py",
    "src/helix/api/routes/discuss.py",
    "src/helix/api/routes/projects.py",
    "src/helix/api/routes/execute.py",
    "src/helix/api/routes/stream.py",
    "config/api.yaml",
    "docker/helix-api/Dockerfile",
    "docker/helix-api/docker-compose.yaml",
    "docker/helix-api/requirements.txt"
  ]
}
```
