"""
MergeMind — Main Application Entry Point

Initializes the FastAPI application, mounts the webhooks router,
and configures standard middleware.
"""

import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from src.api.webhooks import router as webhooks_router

from src.observability.tracer import setup_tracing
setup_tracing()

# Ensure all mergemind.* loggers write to stderr so Cloud Run captures them
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for the FastAPI application."""
    # Startup: Initialize tracing, establish connections
    
    yield
    
    # Shutdown: Clean up connections


# Initialize the FastAPI app
app = FastAPI(
    title="MergeMind Arbitration Engine",
    description="AI-Assisted code evaluation and programmable ledger system.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For hackathon/development purposes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the routers
app.include_router(webhooks_router)


@app.get("/health", tags=["system"])
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "version": app.version}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
