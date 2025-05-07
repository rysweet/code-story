"""Main entry point for Code Story API service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.codestory.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Code Story API",
    description="API for Code Story knowledge graph service",
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
        "name": settings.project_name,
        "version": settings.version,
        "description": settings.description,
    }