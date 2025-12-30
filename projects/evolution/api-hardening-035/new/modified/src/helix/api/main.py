"""HELIX API - FastAPI application.

This API provides:
1. OpenAI-compatible endpoints for Open WebUI integration
2. HELIX-specific endpoints for project execution
3. SSE streaming for real-time progress updates

ADR-030 Fix 8: Global Exception Handler with structured logging.
ADR-035 Fix 3: Rate Limiting integration with slowapi.
"""

import os
import sys
import logging
import traceback
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

# Ensure src is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .routes import openai, helix, stream, evolution
from .middleware.rate_limiter import limiter, RateLimitExceededHandler

# Configure logging
LOG_DIR = Path(__file__).parent.parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "api.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Debug mode from environment
DEBUG = os.environ.get("HELIX_DEBUG", "false").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("=" * 60)
    logger.info("HELIX API Starting")
    logger.info("=" * 60)
    logger.info(f"Port: {os.environ.get('PORT', 8001)}")
    logger.info(f"Debug: {DEBUG}")
    logger.info(f"Docs: http://localhost:{os.environ.get('PORT', 8001)}/docs")
    logger.info("Rate Limiting: Enabled (10 req/min per IP)")
    logger.info("=" * 60)

    # Set NVM path
    nvm_path = "/home/aiuser01/.nvm/versions/node/v20.19.6/bin"
    if nvm_path not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{nvm_path}:{os.environ.get('PATH', '')}"

    yield

    # Shutdown
    logger.info("HELIX API Shutting down")


app = FastAPI(
    title="HELIX API",
    description="AI Development Orchestrator API",
    version="4.0.0",
    lifespan=lifespan,
)

# ADR-035 Fix 3: Rate Limiter State
# The limiter needs to be attached to the app state for slowapi to work
app.state.limiter = limiter

# ADR-035 Fix 3: Rate Limit Exception Handler
app.add_exception_handler(RateLimitExceeded, RateLimitExceededHandler)


# Global Exception Handler (ADR-030 Fix 8)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Log all unhandled exceptions with full traceback.
    Returns structured error response.

    ADR-030 Fix 8: Global Exception Handler
    """
    # Log full traceback
    logger.error(
        f"Unhandled exception in {request.method} {request.url.path}",
        exc_info=exc
    )

    # Build response
    error_response = {
        "error": "Internal Server Error",
        "type": type(exc).__name__,
        "message": str(exc),
        "path": str(request.url.path),
        "timestamp": datetime.now().isoformat(),
    }

    # Include traceback in debug mode
    if DEBUG:
        error_response["traceback"] = traceback.format_exc()

    return JSONResponse(
        status_code=500,
        content=error_response
    )


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for debugging."""
    start_time = datetime.now()

    response = await call_next(request)

    duration = (datetime.now() - start_time).total_seconds()

    # Only log non-health requests or if DEBUG
    if DEBUG or request.url.path not in ["/health", "/docs", "/openapi.json"]:
        logger.debug(
            f"{request.method} {request.url.path} -> {response.status_code} ({duration:.3f}s)"
        )

    return response


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
app.include_router(evolution.router)


@app.get("/")
async def root():
    """API root - basic info."""
    return {
        "name": "HELIX API",
        "version": "4.0.0",
        "status": "running",
        "docs": "/docs",
        "security": {
            "rate_limiting": "10 requests/minute per IP",
            "input_validation": "enabled",
        },
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
