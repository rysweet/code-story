"""Initialize test configuration for test environments.

This module is intended to be imported by test fixtures to ensure
test configuration is properly initialized and loaded.
"""

import os
from pathlib import Path

# Ensure we're in a test environment
os.environ["CODESTORY_TEST_ENV"] = "true"

# Add more environment variables required for tests
os.environ["NEO4J_DATABASE"] = "testdb"
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "password"
os.environ["REDIS_URI"] = "redis://localhost:6379/0"
os.environ["OPENAI_API_KEY"] = "sk-test-key-openai"

# Double underscore format for Pydantic nested settings
os.environ["NEO4J__URI"] = "bolt://localhost:7687"
os.environ["NEO4J__USERNAME"] = "neo4j"
os.environ["NEO4J__PASSWORD"] = "password"
os.environ["NEO4J__DATABASE"] = "testdb"
os.environ["REDIS__URI"] = "redis://localhost:6379/0"
os.environ["OPENAI__API_KEY"] = "sk-test-key-openai"
os.environ["OPENAI__EMBEDDING_MODEL"] = "text-embedding-3-small"
os.environ["OPENAI__CHAT_MODEL"] = "gpt-4o"
os.environ["OPENAI__REASONING_MODEL"] = "gpt-4o"

# Azure OpenAI settings
os.environ["AZURE_OPENAI__API_KEY"] = "test-azure-key"
os.environ["AZURE_OPENAI__ENDPOINT"] = "<your-endpoint>"
os.environ["AZURE_OPENAI__DEPLOYMENT_ID"] = "gpt-4o"

# Service settings
os.environ["SERVICE__HOST"] = "127.0.0.1"
os.environ["SERVICE__PORT"] = "8000"

# Ingestion settings
os.environ["INGESTION__CONFIG_PATH"] = "pipeline_config.yml"

# Plugins settings
os.environ["PLUGINS__ENABLED"] = "filesystem"

# Telemetry settings
os.environ["TELEMETRY__METRICS_PORT"] = "9090"

# Interface settings
os.environ["INTERFACE__THEME"] = "light"

# Azure settings
os.environ["AZURE__KEYVAULT_NAME"] = "test-key-vault"

def create_test_config_file():
    """Create the test configuration file if it doesn't exist."""
    # Get path to the project root
    project_root = Path(__file__).parent.parent.parent
    
    test_config_path = project_root / "tests" / "fixtures" / "test_config.toml"
    
    if not test_config_path.exists():
        # Create the test config.toml file
        test_config_content = """# Test configuration file for CI environments

[neo4j]
uri = "bolt://localhost:7687"
username = "neo4j"
password = "password"
database = "testdb"

[redis]
uri = "redis://localhost:6379/0"

[openai]
api_key = "sk-test-key-openai"
embedding_model = "text-embedding-3-small"
chat_model = "gpt-4o"
reasoning_model = "gpt-4o"

[azure_openai]
api_key = "sk-test-key-azure"
endpoint = "<your-endpoint>"
deployment_id = "gpt-4o"
embedding_model = "text-embedding-3-small"
chat_model = "gpt-4o"
reasoning_model = "gpt-4o"

[service]
host = "0.0.0.0"
port = 8000
workers = 4
log_level = "INFO"
environment = "testing"
enable_telemetry = true
worker_concurrency = 4

[ingestion]
config_path = "pipeline_config.yml"
chunk_size = 1024
chunk_overlap = 200
embedding_model = "text-embedding-3-small"
embedding_dimensions = 1536
max_retries = 3
retry_backoff_factor = 2.0
concurrency = 5

[plugins]
enabled = ["blarify", "filesystem", "summarizer", "docgrapher"]
plugin_directory = "plugins"

[telemetry]
metrics_port = 9090
metrics_endpoint = "/metrics"
trace_sample_rate = 1.0
log_format = "json"

[interface]
theme = "dark"
default_view = "graph"
graph_layout = "force"
max_nodes = 1000
max_edges = 5000
auto_refresh = true
refresh_interval = 30

[azure]
keyvault_name = ""
tenant_id = ""
client_id = ""
client_secret = ""
"""
        test_config_path.write_text(test_config_content)
        print(f"Created test config file at {test_config_path}")
    else:
        print(f"Test config file already exists at {test_config_path}")
        
    return test_config_path

# Create the test config file
test_config_path = create_test_config_file()