"""Main entry point for the Model Context Protocol service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from codestory.config.settings import get_settings

settings = get_settings()

app = FastAPI(
    title="Code Story MCP API",
    description="Model Context Protocol API for Code Story",
    version=settings.version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only, restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": f"{settings.project_name}-mcp",
        "version": settings.version,
        "description": "Model Context Protocol API for Code Story",
    }