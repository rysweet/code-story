"""
codestory.config

Configuration management for CodeStory.

Settings are loaded in the following precedence:
1. Environment variables (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
2. Values from a .env file in the project root (if present)
3. Pydantic default values (not used here; all fields are required)

If a required variable is missing, instantiating Settings will raise pydantic.ValidationError.

See the design spec for details on environment variable handling and precedence.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache

class Settings(BaseSettings):
    """
    Pydantic settings for CodeStory Neo4j connection.

    Required environment variables:
      - NEO4J_URI
      - NEO4J_USER
      - NEO4J_PASSWORD

    Loads from environment or .env file (if present).
    """
    neo4j_uri: str = Field(..., env="NEO4J_URI")
    neo4j_user: str = Field(..., env="NEO4J_USER")
    neo4j_password: str = Field(..., env="NEO4J_PASSWORD")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    """
    Returns a singleton instance of Settings.
    """
    return Settings()

__all__ = ["Settings", "get_settings"]