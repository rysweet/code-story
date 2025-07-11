"""Integration tests for CLI query commands."""
import os
import time
from typing import Any

import pytest
from click.testing import CliRunner

from codestory.cli.main import app

def is_host_native_mode() -> bool:
    """Host-native mode is deprecated. All tests now use containerized services."""
    return False

@pytest.fixture(autouse=True, scope="module")
def setup_neo4j_env_and_wait(test_containers_and_service):
    # Set the Neo4j URI and credentials for the test worker
    print(f"[setup_neo4j_env_and_wait] BEFORE: NEO4J_URI={os.environ.get('NEO4J_URI')}, CODESTORY_NEO4J__URI={os.environ.get('CODESTORY_NEO4J__URI')}")
    neo4j_uri = os.environ.get("NEO4J_URI")
    if not neo4j_uri:
        pytest.fail("NEO4J_URI must be set by the testcontainer fixture.")
    os.environ["CODESTORY_NEO4J__URI"] = neo4j_uri
    os.environ["NEO4J_URI"] = neo4j_uri
    os.environ["CODESTORY_NEO4J__USERNAME"] = os.environ.get("CODESTORY_NEO4J__USERNAME", "neo4j")
    os.environ["NEO4J_USERNAME"] = os.environ.get("NEO4J_USERNAME", "neo4j")
    os.environ["CODESTORY_NEO4J__PASSWORD"] = os.environ.get("CODESTORY_NEO4J__PASSWORD", "password")
    os.environ["NEO4J_PASSWORD"] = os.environ.get("NEO4J_PASSWORD", "password")
    print(f"[setup_neo4j_env_and_wait] AFTER: NEO4J_URI={os.environ.get('NEO4J_URI')}, CODESTORY_NEO4J__URI={os.environ.get('CODESTORY_NEO4J__URI')}")
    # Wait for Neo4j to be ready before running query tests
    from neo4j import GraphDatabase
    from neo4j.exceptions import ServiceUnavailable
    uri = os.environ.get("CODESTORY_NEO4J__URI") or os.environ.get("NEO4J_URI")
    username = os.environ.get("CODESTORY_NEO4J__USERNAME") or os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("CODESTORY_NEO4J__PASSWORD") or os.environ.get("NEO4J_PASSWORD") or "password"
    driver = GraphDatabase.driver(uri, auth=(username, password))
    for attempt in range(30):
        try:
            with driver.session() as session:
                result = session.run("RETURN 1 AS ready")
                if result.single()["ready"] == 1:
                    print("[test_query_integration] Neo4j is ready.")
                    break
        except ServiceUnavailable as e:
            print(f"[test_query_integration] Waiting for Neo4j to be ready... ({e})")
            time.sleep(1)
    else:
        pytest.fail("Neo4j did not become ready in time.")
    driver.close()

@pytest.mark.usefixtures("test_containers_and_service", "setup_neo4j_env_and_wait")
class TestQueryCommands:
    """Integration tests for query-related CLI commands."""

    def test_query_run_cypher(
        self: Any, cli_runner: CliRunner, test_containers_and_service
    ) -> None:
        """Test 'query run' command with simple Cypher query, with Neo4j retry loop."""
        import os
        import time
        from neo4j import GraphDatabase
        from neo4j.exceptions import ServiceUnavailable, AuthError

        env = os.environ.copy()
        # Explicitly set Neo4j URIs from test_containers_and_service
        neo4j_uri = test_containers_and_service['neo4j_uri']
        print(f"[test_query_run_cypher] Using Neo4j URI for subprocess: {neo4j_uri}")
        assert neo4j_uri.startswith("bolt://localhost:"), (
            f"Neo4j URI must use localhost and mapped port, got: {neo4j_uri}"
        )
        env['NEO4J_URI'] = neo4j_uri
        env['CODESTORY_NEO4J__URI'] = neo4j_uri
        # Prevent TOML config from overriding test env: point to test config or /dev/null
        env['CODESTORY_CONFIG_FILE'] = "tests/fixtures/test_config.toml"
        # Prevent .env from being loaded if possible (pydantic uses env_file, but we want to ensure test env wins)
        # Optionally, unset ENV_FILE or related variables if present
        env.pop('ENV_FILE', None)
        # Clear settings cache to avoid stale config from parent process
        try:
            from codestory.config.settings import get_settings
            get_settings.cache_clear()
        except Exception:
            pass
        username = env.get("CODESTORY_NEO4J__USERNAME") or env.get("NEO4J_USERNAME", "neo4j")
        password = env.get("CODESTORY_NEO4J__PASSWORD") or env.get("NEO4J_PASSWORD") or "password"
        port = env.get("CODESTORY_SERVICE__PORT") or env.get("PORT") or env.get("CODESTORY_TEST_PORT")
        # Print all relevant Neo4j/service env vars and config file paths before invoking CLI
        env_dump = {
            "NEO4J_URI": env.get("NEO4J_URI"),
            "CODESTORY_NEO4J__URI": env.get("CODESTORY_NEO4J__URI"),
            "NEO4J_USERNAME": env.get("NEO4J_USERNAME"),
            "CODESTORY_NEO4J__USERNAME": env.get("CODESTORY_NEO4J__USERNAME"),
            "NEO4J_PASSWORD": env.get("NEO4J_PASSWORD"),
            "CODESTORY_NEO4J__PASSWORD": env.get("CODESTORY_NEO4J__PASSWORD"),
            "CODESTORY_SERVICE__PORT": env.get("CODESTORY_SERVICE__PORT"),
            "PORT": env.get("PORT"),
            "CODESTORY_TEST_PORT": env.get("CODESTORY_TEST_PORT"),
            "CODESTORY_CONFIG_FILE": env.get("CODESTORY_CONFIG_FILE"),
            "CONFIG_FILE": env.get("CONFIG_FILE"),
        }
        print("[test_query_run_cypher] ENV DUMP:", env_dump)

        # Attempt to connect to Neo4j directly before invoking CLI; fail immediately if unavailable
        driver = GraphDatabase.driver(neo4j_uri, auth=(username, password))
        try:
            with driver.session() as session:
                result = session.run("RETURN 1 AS ready")
                assert result.single()["ready"] == 1, "Neo4j did not return ready=1"
            print("[test_query_run_cypher] Direct Neo4j connection succeeded.")
        except (ServiceUnavailable, AuthError, Exception) as e:
            print(f"[test_query_run_cypher] ERROR: Could not connect to Neo4j: {e}")
            driver.close()
            import pytest
            pytest.fail(f"Could not connect to Neo4j: {e}")
        driver.close()

        # Extra: ensure Neo4j is ready for subprocesses (simulate CLI env)
        import subprocess, sys
        for attempt in range(10):
            proc = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "from neo4j import GraphDatabase; "
                        f"driver=GraphDatabase.driver('{neo4j_uri}', auth=('neo4j','password')); "
                        "with driver.session() as s: "
                        "r=s.run('RETURN 1 AS ready'); "
                        "assert r.single()['ready']==1"
                    ),
                ],
                env=env,
                capture_output=True,
                text=True,
            )
            if proc.returncode == 0:
                print("[test_query_run_cypher] Subprocess Neo4j check succeeded.")
                break
            else:
                print(f"[test_query_run_cypher] Subprocess Neo4j check failed (attempt {attempt+1}): {proc.stderr.strip()}")
                import time
                time.sleep(1)
        else:
            import pytest
            pytest.fail("Neo4j not ready for subprocess after 10 attempts")

        if port:
            env["CODESTORY_SERVICE__PORT"] = str(port)
        # Give Neo4j a moment to fully accept new connections after subprocess check
        time.sleep(5)
        # Retry CLI invocation up to 5 times to handle race conditions
        import time
        import subprocess
        for attempt in range(5):
            # Use a shell script to set the environment and invoke the CLI
            script_path = "tests/integration/test_cli/run_query_cypher.sh"
            import stat
            # Ensure the script is executable
            st = os.stat(script_path)
            os.chmod(script_path, st.st_mode | stat.S_IEXEC)
            abs_script_path = os.path.abspath(script_path)
            print(f"RUNNING SHELL SCRIPT: {abs_script_path}")
            print(f"Script exists: {os.path.exists(abs_script_path)}")
            print(f"Script is executable: {os.access(abs_script_path, os.X_OK)}")
            proc = subprocess.run(
                [
                    "bash",
                    abs_script_path,
                    env["NEO4J_URI"],
                    env["CODESTORY_CONFIG_FILE"],
                ],
                text=True,
            )
            output = ""  # Output will be printed directly to stdout/stderr
            output = proc.stdout + "\n" + proc.stderr
            if proc.returncode == 0 and "Query Results" in output and "count" in output:
                print("[test_query_run_cypher] TEST PASSED (subprocess)")
                print("[test_query_run_cypher] ENV SUMMARY:", {k: v for k, v in env_dump.items() if v})
                print("[test_query_run_cypher] CLI OUTPUT SUMMARY:")
                lines = output.splitlines()
                for line in lines:
                    if "Query Results" in line or "count" in line:
                        print(line)
                break
            else:
                print(f"[test_query_run_cypher] CLI attempt {attempt+1} failed (subprocess)")
                print("[test_query_run_cypher] ENV DUMP:", env_dump)
                print("[test_query_run_cypher] CLI EXIT CODE:", proc.returncode)
                print("[test_query_run_cypher] CLI OUTPUT:\n", output)
                time.sleep(2)
        else:
            assert proc.returncode == 0, "CLI exited with nonzero code"
            assert "Query Results" in output, "'Query Results' not in CLI output"
            assert "count" in output, "'count' not in CLI output"

    def test_query_help(
        self: Any, cli_runner: CliRunner, test_containers_and_service
    ) -> None:
        # Test 'query --help' CLI output with correct Neo4j env setup
        import os
        env = os.environ.copy()
        neo4j_uri = test_containers_and_service['neo4j_uri']
        env['NEO4J_URI'] = neo4j_uri
        env['CODESTORY_NEO4J__URI'] = neo4j_uri
        port = env.get("CODESTORY_SERVICE__PORT") or env.get("PORT") or env.get("CODESTORY_TEST_PORT")
        if port:
            env["CODESTORY_SERVICE__PORT"] = str(port)
        result = cli_runner.invoke(
            app, ["query", "--help"], env=env
        )
        if result.exit_code != 0 or "Usage:" not in result.output or "query" not in result.output:
            print("[test_query_help] TEST FAILED")
            print("[test_query_help] CLI EXIT CODE:", result.exit_code)
            print("[test_query_help] CLI OUTPUT:\n", result.output)
            if hasattr(result, "exc_info") and result.exc_info:
                print("[test_query_help] CLI ERROR INFO:", result.exc_info)
            assert result.exit_code == 0, "CLI exited with nonzero code"
            assert "Usage:" in result.output, "'Usage:' not in CLI output"
            assert "query" in result.output, "'query' not in CLI output"
        else:
            print("[test_query_help] TEST PASSED")
            print("[test_query_help] CLI OUTPUT SUMMARY:")
            lines = result.output.splitlines()
            for line in lines:
                if "Usage:" in line or "query" in line:
                    print(line)

    def test_query_run_with_format(
        self: Any, cli_runner: CliRunner, test_containers_and_service
    ) -> None:
        # This test should use the correct Neo4j URI from the testcontainer in the CLI environment
        import os
        env = os.environ.copy()
        neo4j_uri = test_containers_and_service['neo4j_uri']
        env['NEO4J_URI'] = neo4j_uri
        env['CODESTORY_NEO4J__URI'] = neo4j_uri
        username = env.get("CODESTORY_NEO4J__USERNAME") or env.get("NEO4J_USERNAME", "neo4j")
        password = env.get("CODESTORY_NEO4J__PASSWORD") or env.get("NEO4J_PASSWORD") or "password"
        port = env.get("CODESTORY_SERVICE__PORT") or env.get("PORT") or env.get("CODESTORY_TEST_PORT")
        if port:
            env["CODESTORY_SERVICE__PORT"] = str(port)
        # Run the CLI with --format json
        result = cli_runner.invoke(
            app, ["query", "run", "MATCH (n) RETURN count(n) as count LIMIT 5", "--format", "json"], env=env
        )
        # If the test fails, print full CLI output and error messages
        if result.exit_code != 0 or "count" not in result.output:
            print("[test_query_run_with_format] TEST FAILED")
            print("[test_query_run_with_format] CLI EXIT CODE:", result.exit_code)
            print("[test_query_run_with_format] CLI OUTPUT:\n", result.output)
            if hasattr(result, "exc_info") and result.exc_info:
                print("[test_query_run_with_format] CLI ERROR INFO:", result.exc_info)
            assert result.exit_code == 0, "CLI exited with nonzero code"
            assert "count" in result.output, "'count' not in CLI output"
        # If the test passes, summarize the environment and output
        else:
            print("[test_query_run_with_format] TEST PASSED")
            print("[test_query_run_with_format] ENV SUMMARY:", {k: v for k, v in env.items() if k.startswith("NEO4J") or k.startswith("CODESTORY") or k == "PORT"})
            print("[test_query_run_with_format] CLI OUTPUT SUMMARY:")
            lines = result.output.splitlines()
            for line in lines:
                if "count" in line:
                    print(line)

    def test_query_run_with_limit(
        self: Any, cli_runner: CliRunner, test_containers_and_service
    ) -> None:
        # This test should use the correct Neo4j URI from the testcontainer in the CLI environment
        import os
        import subprocess
        import sys
        import time

        env = os.environ.copy()
        neo4j_uri = test_containers_and_service['neo4j_uri']
        env['NEO4J_URI'] = neo4j_uri
        env['CODESTORY_NEO4J__URI'] = neo4j_uri
        # Prevent TOML config from overriding test env: point to test config or /dev/null
        env['CODESTORY_CONFIG_FILE'] = "tests/fixtures/test_config.toml"
        # Prevent .env from being loaded if possible
        env.pop('ENV_FILE', None)
        username = env.get("CODESTORY_NEO4J__USERNAME") or env.get("NEO4J_USERNAME", "neo4j")
        password = env.get("CODESTORY_NEO4J__PASSWORD") or env.get("NEO4J_PASSWORD") or "password"
        port = env.get("CODESTORY_SERVICE__PORT") or env.get("PORT") or env.get("CODESTORY_TEST_PORT")
        if port:
            env["CODESTORY_SERVICE__PORT"] = str(port)

        # Ensure Neo4j is ready for subprocesses (simulate CLI env)
        for attempt in range(10):
            proc = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "from neo4j import GraphDatabase; "
                        f"driver=GraphDatabase.driver('{neo4j_uri}', auth=('neo4j','password')); "
                        "with driver.session() as s: "
                        "r=s.run('RETURN 1 AS ready'); "
                        "assert r.single()['ready']==1"
                    ),
                ],
                env=env,
                capture_output=True,
                text=True,
            )
            if proc.returncode == 0:
                print("[test_query_run_with_limit] Subprocess Neo4j check succeeded.")
                break
            else:
                print(f"[test_query_run_with_limit] Subprocess Neo4j check failed (attempt {attempt+1}): {proc.stderr.strip()}")
                time.sleep(1)
        else:
            import pytest
            pytest.fail("Neo4j not ready for subprocess after 10 attempts")

        # Give Neo4j a moment to fully accept new connections after subprocess check
        time.sleep(5)
        # Retry CLI invocation up to 5 times to handle race conditions
        for attempt in range(5):
            result = cli_runner.invoke(
                app, ["query", "run", "MATCH (n) RETURN n LIMIT 2"], env=env
            )
            if result.exit_code == 0 and "Query Results" in result.output:
                print("[test_query_run_with_limit] TEST PASSED")
                print("[test_query_run_with_limit] ENV SUMMARY:", {k: v for k, v in env.items() if k.startswith("NEO4J") or k.startswith("CODESTORY") or k == "PORT"})
                print("[test_query_run_with_limit] CLI OUTPUT SUMMARY:")
                lines = result.output.splitlines()
                for line in lines:
                    if "Query Results" in line or "n" in line:
                        print(line)
                break
            else:
                print(f"[test_query_run_with_limit] CLI attempt {attempt+1} failed")
                print("[test_query_run_with_limit] CLI EXIT CODE:", result.exit_code)
                print("[test_query_run_with_limit] CLI OUTPUT:\n", result.output)
                if hasattr(result, "exc_info") and result.exc_info:
                    print("[test_query_run_with_limit] CLI ERROR INFO:", result.exc_info)
                time.sleep(2)
        else:
            assert result.exit_code == 0, "CLI exited with nonzero code"
            assert "Query Results" in result.output, "'Query Results' not in CLI output"

    def test_query_export(
        self: Any, cli_runner: CliRunner, test_containers_and_service
    ) -> None:
        pass

    def test_query_explore(
        self: Any, cli_runner: CliRunner, test_containers_and_service
    ) -> None:
        # Minimal test for 'query explore' CLI command with correct Neo4j env setup
        import os
        env = os.environ.copy()
        neo4j_uri = test_containers_and_service['neo4j_uri']
        env['NEO4J_URI'] = neo4j_uri
        env['CODESTORY_NEO4J__URI'] = neo4j_uri
        username = env.get("CODESTORY_NEO4J__USERNAME") or env.get("NEO4J_USERNAME", "neo4j")
        password = env.get("CODESTORY_NEO4J__PASSWORD") or env.get("NEO4J_PASSWORD") or "password"
        port = env.get("CODESTORY_SERVICE__PORT") or env.get("PORT") or env.get("CODESTORY_TEST_PORT")
        if port:
            env["CODESTORY_SERVICE__PORT"] = str(port)
        # Run the CLI 'query explore' command (with no extra args)
        result = cli_runner.invoke(
            app, ["query", "explore"], env=env
        )
        # If the test fails, print full CLI output and error messages
        if result.exit_code != 0:
            print("[test_query_explore] TEST FAILED")
            print("[test_query_explore] CLI EXIT CODE:", result.exit_code)
            print("[test_query_explore] CLI OUTPUT:\n", result.output)
            if hasattr(result, "exc_info") and result.exc_info:
                print("[test_query_explore] CLI ERROR INFO:", result.exc_info)
            assert result.exit_code == 0, "CLI exited with nonzero code"
        else:
            print("[test_query_explore] TEST PASSED")
            print("[test_query_explore] CLI OUTPUT SUMMARY:")
            lines = result.output.splitlines()
            for line in lines:
                if line.strip():
                    print(line)

# Minimal direct Neo4j connectivity test (not via CLI)
def test_direct_neo4j_connectivity():
    """Directly test Neo4j connectivity from the test process (not via CLI)."""
    import os
    from neo4j import GraphDatabase
    uri = os.environ.get("CODESTORY_NEO4J__URI") or os.environ.get("NEO4J_URI")
    username = os.environ.get("CODESTORY_NEO4J__USERNAME") or os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("CODESTORY_NEO4J__PASSWORD") or os.environ.get("NEO4J_PASSWORD") or "password"
    driver = GraphDatabase.driver(uri, auth=(username, password))
    with driver.session() as session:
        result = session.run("RETURN 42 AS answer")
        assert result.single()["answer"] == 42
    driver.close()
