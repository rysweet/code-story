"""
Module to override adapter factory functions to always use real adapters.
This ensures we're never using dummy/mock adapters in demo or integration mode.
"""

import logging
import os
from typing import Callable, Any, TypeVar, cast

from .infrastructure.neo4j_adapter import Neo4jAdapter
from .infrastructure.celery_adapter import CeleryAdapter
from .infrastructure.openai_adapter import OpenAIAdapter

# Set up logging
logger = logging.getLogger(__name__)

T = TypeVar('T')

def force_real_adapter(create_fn: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to ensure that only real adapters are returned, never falling back to mocks.
    
    Args:
        create_fn: Original factory function
        
    Returns:
        Wrapped function that only returns real adapters
    """
    
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            # Create a real adapter
            adapter = create_fn(*args, **kwargs)
            
            # Force unwrap any Result/Promise
            if hasattr(adapter, "__await__"):
                adapter = await adapter
                
            # Log successful creation
            logger.info(f"Successfully created real adapter: {type(adapter).__name__}")
            return adapter
        except Exception as e:
            # Instead of falling back to a dummy adapter, raise the exception
            # This forces the service to fail if it can't connect to real services
            logger.error(f"Failed to create real adapter and fallbacks are disabled: {str(e)}")
            raise
            
    return cast(Callable[..., T], wrapper)

# Functions to override the factory functions in their respective modules
# These must be imported and used to override the originals

async def get_real_neo4j_adapter() -> Neo4jAdapter:
    """Create a Neo4j adapter without fallbacks."""
    adapter = Neo4jAdapter()
    await adapter.check_health()  # Will raise exception if connection fails
    return adapter

async def get_real_celery_adapter() -> CeleryAdapter:
    """Create a Celery adapter without fallbacks."""
    adapter = CeleryAdapter()
    health = await adapter.check_health()
    if health["status"] != "healthy":
        raise RuntimeError(f"Celery adapter not healthy: {health}")
    return adapter

async def get_real_openai_adapter() -> OpenAIAdapter:
    """Create an OpenAI adapter with resilient client for fallbacks."""
    # Import here to avoid circular imports
    from .api.dependencies import get_resilient_openai_adapter
    
    # Check if we should bypass adapter strict checking
    if os.environ.get("CODESTORY_NO_MODEL_CHECK", "").lower() in ["true", "1", "yes"]:
        # Use the resilient adapter that handles fallbacks automatically
        adapter = await get_resilient_openai_adapter()
        logger.info("Using resilient OpenAI adapter with fallback in NO_MODEL_CHECK mode")
        return adapter
    
    # Normal strict mode
    adapter = OpenAIAdapter()
    health = await adapter.check_health()
    
    # Check if this is using the demo mode
    if health["status"] == "degraded" and "demo" in str(health.get("details", {}).get("message", "")):
        raise RuntimeError("OpenAI adapter is using demo mode")
        
    # Support degraded clients only when using fallback mode
    if health["status"] == "degraded" and health.get("details", {}).get("fallback", False):
        logger.warning("OpenAI adapter is in degraded state with fallback authentication")
        # Accept fallback mode when needed
    elif health["status"] != "healthy":
        raise RuntimeError(f"OpenAI adapter is not healthy: {health}")
        
    return adapter

# Apply the overrides when this module is imported
def apply_overrides() -> None:
    """
    Apply all the overrides to the adapter factory functions.
    This function should be called during application startup.
    """
    # Import the modules that define the factory functions
    from .infrastructure import neo4j_adapter, celery_adapter, openai_adapter
    
    # Override the factory functions
    neo4j_adapter.get_neo4j_adapter = get_real_neo4j_adapter
    celery_adapter.get_celery_adapter = get_real_celery_adapter
    openai_adapter.get_openai_adapter = get_real_openai_adapter
    
    logger.info("Applied real adapter overrides - demo/mock adapters are disabled")