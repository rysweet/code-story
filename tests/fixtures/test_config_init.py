from typing import Any

"Initialize test configuration for test environments.\n\nThis module is intended to be imported by test fixtures to ensure\ntest configuration is properly initialized and loaded.\n"
from pathlib import Path
from tests.conftest import get_test_config

config = get_test_config()
config.set("CODESTORY_TEST_ENV", "true")
config.set("NEO4J_DATABASE", "neo4j")
config.set("NEO4J_URI", "bolt://localhost:7687")
config.set("NEO4J_USERNAME", "neo4j")
config.set("NEO4J_PASSWORD", "password")
config.set("REDIS_URI", "redis://localhost:6379/0")
config.set("OPENAI_API_KEY", "sk-test-key-openai")
config.set("NEO4J__URI", "bolt://localhost:7687")
config.set("NEO4J__USERNAME", "neo4j")
config.set("NEO4J__PASSWORD", "password")
config.set("NEO4J__DATABASE", "neo4j")
config.set("CODESTORY_NEO4J__URI", config.get("NEO4J_URI", "bolt://localhost:7687"))
config.set("REDIS__URI", "redis://localhost:6379/0")
config.set("OPENAI__API_KEY", "sk-test-key-openai")
config.set("OPENAI__EMBEDDING_MODEL", "text-embedding-3-small")
config.set("OPENAI__CHAT_MODEL", "gpt-4o")
config.set("OPENAI__REASONING_MODEL", "gpt-4o")
config.set("AZURE_OPENAI__API_KEY", "test-azure-key")
config.set("AZURE_OPENAI__ENDPOINT", "<your-endpoint>")
config.set("AZURE_OPENAI__DEPLOYMENT_ID", "gpt-4o")
config.set("SERVICE__HOST", "127.0.0.1")
config.set("SERVICE__PORT", "8000")
config.set("INGESTION__CONFIG_PATH", "pipeline_config.yml")
config.set("PLUGINS__ENABLED", '["filesystem"]')
config.set("TELEMETRY__METRICS_PORT", "9090")
config.set("INTERFACE__THEME", "light")
config.set("AZURE__KEYVAULT_NAME", "test-key-vault")


def create_test_config_file() -> Any:
    """Create the test configuration file if it doesn't exist."""
    project_root = Path(__file__).parent.parent.parent
    test_config_path = project_root / "tests" / "fixtures" / "test_config.toml"
    if not test_config_path.exists():
        test_config_content = '# Test configuration file for CI environments\n\n[neo4j]\nuri = "bolt://localhost:7687"\nusername = "neo4j"\npassword = "password"\ndatabase = "neo4j"\n\n[redis]\nuri = "redis://localhost:6379/0"\n\n[openai]\napi_key = "sk-test-key-openai"\nembedding_model = "text-embedding-3-small"\nchat_model = "gpt-4o"\nreasoning_model = "gpt-4o"\n\n[azure_openai]\napi_key = "sk-test-key-azure"\nendpoint = "<your-endpoint>"\ndeployment_id = "gpt-4o"\nembedding_model = "text-embedding-3-small"\nchat_model = "gpt-4o"\nreasoning_model = "gpt-4o"\n\n[service]\nhost = "0.0.0.0"\nport = 8000\nworkers = 4\nlog_level = "INFO"\nenvironment = "testing"\nenable_telemetry = true\nworker_concurrency = 4\n\n[ingestion]\nconfig_path = "pipeline_config.yml"\nchunk_size = 1024\nchunk_overlap = 200\nembedding_model = "text-embedding-3-small"\nembedding_dimensions = 1536\nmax_retries = 3\nretry_backoff_factor = 2.0\nconcurrency = 5\n\n[plugins]\nenabled = ["blarify", "filesystem", "summarizer", "docgrapher"]\nplugin_directory = "plugins"\n\n[telemetry]\nmetrics_port = 9090\nmetrics_endpoint = "/metrics"\ntrace_sample_rate = 1.0\nlog_format = "json"\n\n[interface]\ntheme = "dark"\ndefault_view = "graph"\ngraph_layout = "force"\nmax_nodes = 1000\nmax_edges = 5000\nauto_refresh = true\nrefresh_interval = 30\n\n[azure]\nkeyvault_name = ""\ntenant_id = ""\nclient_id = ""\nclient_secret = ""\n'
        test_config_path.write_text(test_config_content)
        print(f"Created test config file at {test_config_path}")
    else:
        print(f"Test config file already exists at {test_config_path}")
    return test_config_path


test_config_path = create_test_config_file()
