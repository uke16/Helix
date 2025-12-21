"""HELIX API - FastAPI application.

This API provides:
1. OpenAI-compatible endpoints for Open WebUI integration
2. HELIX-specific endpoints for project execution
3. SSE streaming for real-time progress updates
"""

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure src is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .routes import openai, helix, stream


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("=" * 60)
    print("HELIX API Starting")
    print("=" * 60)
    print(f"Port: {os.environ.get('PORT', 8001)}")
    print(f"Docs: http://localhost:{os.environ.get('PORT', 8001)}/docs")
    print("=" * 60)
    
    # Set NVM path
    nvm_path = "/home/aiuser01/.nvm/versions/node/v20.19.6/bin"
    if nvm_path not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{nvm_path}:{os.environ.get('PATH', '')}"
    
    yield
    
    # Shutdown
    print("HELIX API Shutting down")


app = FastAPI(
    title="HELIX API",
    description="AI Development Orchestrator API",
    version="4.0.0",
    lifespan=lifespan,
)

# CORS for Open WebUI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Open WebUI needs this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(openai.router)
app.include_router(helix.router)
app.include_router(stream.router)


@app.get("/")
async def root():
    """API root - basic info."""
    return {
        "name": "HELIX API",
        "version": "4.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "openai": "/v1/chat/completions",
            "models": "/v1/models",
            "discuss": "/helix/discuss",
            "execute": "/helix/execute",
            "jobs": "/helix/jobs",
            "stream": "/helix/stream/{job_id}",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
