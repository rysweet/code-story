# specs: specs/06-ingestion-pipeline/ingestion-pipeline.md
# code rules: .roo/rules-code/08-unified-test-infra.md, .roo/rules-code/04-testing-requirements.md

"""Integration tests for CLI query commands."""
from tests.conftest import get_test_config
import time
from typing import Any

import pytest
from click.testing import CliRunner

from codestory.cli.main import app

def is_host_native_mode() -> bool:
    """Host-native mode is deprecated. All tests now use containerized services."""
    return False

# All environment and service setup is now handled by the unified_test_env fixture.
# No manual environment variable or health check logic is needed here.

@pytest.mark.usefixtures("unified_test_env")
class TestQueryCommands:
    """Integration tests for query-related CLI commands.

    All service/container setup is handled by the unified_test_env fixture.
    """

    def test_query_run_cypher(self: Any, cli_runner: CliRunner) -> None:
        """Test 'query run' command with simple Cypher query, with Neo4j retry loop.

        All environment variables and service setup are handled by unified_test_env.
        """
        import os
        import time
        from neo4j import GraphDatabase
        from neo4j.exceptions import ServiceUnavailable, AuthError

        config = get_test_config()
        env = config.as_dict()
        # Prevent TOML config from overriding test env: point to test config or /dev/null
        env['CODESTORY_CONFIG_FILE'] = "tests/fixtures/test_config.toml"
        env.pop('ENV_FILE', None)

        neo4j_uri = env.get("CODESTORY_NEO4J__URI") or env.get("NEO4J_URI")
        username = env.get("CODESTORY_NEO4J__USERNAME") or env.get("NEO4J_USERNAME", "neo4j")
        password = env.get("CODESTORY_NEO4J__PASSWORD") or env.get("NEO4J_PASSWORD") or "password"

        # Attempt to connect to Neo4j directly before invoking CLI; fail immediately if unavailable
        driver = GraphDatabase.driver(neo4j_uri, auth=(username, password))
        try:
            with driver.session() as session:
                result = session.run("RETURN 1 AS ready")
                assert result.single()["ready"] == 1, "Neo4j did not return ready=1"
        except (ServiceUnavailable, AuthError, Exception) as e:
            driver.close()
            import pytest
            pytest.fail(f"Could not connect to Neo4j: {e}")
        driver.close()

        # Retry CLI invocation up to 5 times to handle race conditions
        import subprocess
        script_path = "tests/integration/test_cli/run_query_cypher.sh"
        import stat
        st = os.stat(script_path)
        os.chmod(script_path, st.st_mode | stat.S_IEXEC)
        abs_script_path = os.path.abspath(script_path)
        for attempt in range(5):
            proc = subprocess.run(
                [
                    "bash",
                    abs_script_path,
                    env["NEO4J_URI"],
                    env["CODESTORY_CONFIG_FILE"],
                ],
                text=True,
            )
            output = (proc.stdout or "") + "\n" + (proc.stderr or "")
            if proc.returncode == 0 and "Query Results" in output and "count" in output:
                break
            else:
                time.sleep(2)
        else:
            assert proc.returncode == 0, "CLI exited with nonzero code"
            assert "Query Results" in output, "'Query Results' not in CLI output"
            assert "count" in output, "'count' not in CLI output"

    def test_query_help(self: Any, cli_runner: CliRunner) -> None:
        """Test 'query --help' CLI output with correct Neo4j env setup."""
        config = get_test_config()
        env = config.as_dict()
        result = cli_runner.invoke(
            app, ["query", "--help"], env=env
        )
        assert result.exit_code == 0, "CLI exited with nonzero code"
        assert "Usage:" in result.output, "'Usage:' not in CLI output"
        assert "query" in result.output, "'query' not in CLI output"

    def test_query_run_with_format(self: Any, cli_runner: CliRunner) -> None:
        """Test 'query run' with --format json using correct Neo4j env."""
        config = get_test_config()
        env = config.as_dict()
        result = cli_runner.invoke(
            app, ["query", "run", "MATCH (n) RETURN count(n) as count LIMIT 5", "--format", "json"], env=env
        )
        assert result.exit_code == 0, "CLI exited with nonzero code"
        assert "count" in result.output, "'count' not in CLI output"

    def test_query_run_with_limit(self: Any, cli_runner: CliRunner) -> None:
        """Test 'query run' with LIMIT using correct Neo4j env."""
        import os
        config = get_test_config()
        env = config.as_dict()
        env['CODESTORY_CONFIG_FILE'] = "tests/fixtures/test_config.toml"
        env.pop('ENV_FILE', None)
        for attempt in range(5):
            result = cli_runner.invoke(
                app, ["query", "run", "MATCH (n) RETURN n LIMIT 2"], env=env
            )
            if result.exit_code == 0 and "Query Results" in result.output:
                break
            else:
                import time
                time.sleep(2)
        else:
            assert result.exit_code == 0, "CLI exited with nonzero code"
            assert "Query Results" in result.output, "'Query Results' not in CLI output"

    def test_query_export(
        self: Any, cli_runner: CliRunner, test_containers_and_service
    ) -> None:
        pass

    def test_query_explore(self: Any, cli_runner: CliRunner) -> None:
        """Minimal test for 'query explore' CLI command with correct Neo4j env setup."""
        config = get_test_config()
        env = config.as_dict()
        result = cli_runner.invoke(
            app, ["query", "explore"], env=env
        )
        assert result.exit_code == 0, "CLI exited with nonzero code"

# Minimal direct Neo4j connectivity test (not via CLI)
def test_direct_neo4j_connectivity():
    """Directly test Neo4j connectivity from the test process (not via CLI)."""
    from tests.conftest import get_test_config
    from neo4j import GraphDatabase
    config = get_test_config()
    uri = config.get("CODESTORY_NEO4J__URI") or config.get("NEO4J_URI")
    username = config.get("CODESTORY_NEO4J__USERNAME") or config.get("NEO4J_USERNAME", "neo4j")
    password = config.get("CODESTORY_NEO4J__PASSWORD") or config.get("NEO4J_PASSWORD") or "password"
    driver = GraphDatabase.driver(uri, auth=(username, password))
    with driver.session() as session:
        result = session.run("RETURN 42 AS answer")
        assert result.single()["answer"] == 42
    driver.close()
