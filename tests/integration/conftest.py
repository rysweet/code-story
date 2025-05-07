"""Pytest configuration for integration tests."""

import os
import pytest
from typing import Dict, Any

from dotenv import load_dotenv


@pytest.fixture(scope="session", autouse=True)
def load_env_vars():
    """Load environment variables for integration tests.
    
    This fixture automatically loads environment variables from .env file
    and ensures that the Neo4j connection settings are available for tests.
    """
    # Load environment variables from .env file
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    load_dotenv(env_path)
    
    # Set default Neo4j test variables if not already set
    # The setup_test_db.sh script should set these, but this is a fallback
    if "NEO4J_URI" not in os.environ:
        os.environ["NEO4J_URI"] = "bolt://localhost:7688"
    if "NEO4J_USERNAME" not in os.environ:
        os.environ["NEO4J_USERNAME"] = "neo4j"
    if "NEO4J_PASSWORD" not in os.environ:
        os.environ["NEO4J_PASSWORD"] = "password"
    if "NEO4J_DATABASE" not in os.environ:
        os.environ["NEO4J_DATABASE"] = "codestory-test"