print("[conftest DEBUG] conftest.py loaded and executed at import")
import os
try:
    os.makedirs("test_container_logs", exist_ok=True)
    with open("test_container_logs/cli_integration_debug.log", "a") as f:
        f.write("[conftest DEBUG] LOGGING TEST ENTRY - FILE WRITE SUCCESSFUL\n")
except Exception as e:
    print(f"[conftest DEBUG] Failed to write to cli_integration_debug.log at import: {e}")

import shutil
import multiprocessing
multiprocessing.set_start_method("fork", force=True)
from neo4j import GraphDatabase
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
# Load .env file for OpenAI and other credentials
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import pytest

# Use testcontainers for integration test infrastructure
from testcontainers.neo4j import Neo4jContainer
from testcontainers.redis import RedisContainer

import socket
import subprocess
import sys
import time
import requests

# For health checks
from neo4j import GraphDatabase
import redis as redis_py
from celery import Celery
from celery.exceptions import TimeoutError as CeleryTimeoutError

@pytest.fixture(scope="session")
def neo4j_testcontainer():
    """Start a single Neo4j testcontainer for all test workers."""
    from testcontainers.neo4j import Neo4jContainer
    with Neo4jContainer("neo4j:community") as neo4j:
        bolt_url = f"bolt://{neo4j.get_container_host_ip()}:{neo4j.get_exposed_port(7687)}"
        os.environ["CODESTORY_NEO4J__URI"] = bolt_url
        os.environ["NEO4J_URI"] = bolt_url
        os.environ["CODESTORY_NEO4J__USERNAME"] = "neo4j"
        os.environ["NEO4J_USERNAME"] = "neo4j"
        os.environ["CODESTORY_NEO4J__PASSWORD"] = "password"
        os.environ["NEO4J_PASSWORD"] = "password"
        os.environ["CODESTORY_NEO4J__DATABASE"] = "neo4j"
        os.environ["NEO4J_DATABASE"] = "neo4j"
        print(f"[neo4j_testcontainer] Set CODESTORY_NEO4J__URI={bolt_url}")
        # Health check: wait for Neo4j to be ready before starting the backend
        for attempt in range(30):
            try:
                driver = GraphDatabase.driver(bolt_url, auth=("neo4j", "password"))
                with driver.session() as session:
                    result = session.run("CALL dbms.components()")
                    _ = result.single()
                print("[neo4j_testcontainer] Neo4j is ready.")
                driver.close()
                break
            except ServiceUnavailable as e:
                print(f"[neo4j_testcontainer] Waiting for Neo4j to be ready... ({e})")
                time.sleep(1)
        else:
            pytest.fail("Neo4j did not become ready in time (neo4j_testcontainer).")
        yield bolt_url

@pytest.fixture(scope="session")
def test_containers_and_service(neo4j_testcontainer):
    """
    Start Redis using testcontainers, configure environment, and launch the Code Story service and worker for integration tests.
    Yields the backend service port for use in tests.
    """
    bolt_url = neo4j_testcontainer
    # Build env dict for subprocesses
    env = os.environ.copy()
    print(f"[test_containers_and_service] NEO4J_URI in env: {env.get('NEO4J_URI')}")
    print(f"[test_containers_and_service] CODESTORY_NEO4J__URI in env: {env.get('CODESTORY_NEO4J__URI')}")
    # Ensure Celery worker can import project modules by including project root in PYTHONPATH
    project_root_path = "/Users/ryan/src/msec/code-story"
    env["PYTHONPATH"] = ":".join(
        filter(None, [project_root_path, env.get("PYTHONPATH", "")])
    )
    env["NEO4J_URI"] = bolt_url
    env["NEO4J_USERNAME"] = "neo4j"
    env["NEO4J_PASSWORD"] = "password"
    env["NEO4J_DATABASE"] = "neo4j"
    # --- Add additional aliases required by Neo4jConnector fallback order ---
    env["NEO4J__URI"] = bolt_url          # double-underscore variant
    os.environ["NEO4J__URI"] = bolt_url
    # -----------------------------------------------------------------------
    # Disable costly OpenAI health-check during integration tests
    env["DISABLE_OPENAI_HEALTHCHECK"] = "1"
    os.environ["DISABLE_OPENAI_HEALTHCHECK"] = "1"
    # Also set the settings-compatible env vars for all subprocesses
    env["CODESTORY_NEO4J__URI"] = bolt_url
    env["CODESTORY_NEO4J__USERNAME"] = "neo4j"
    env["CODESTORY_NEO4J__PASSWORD"] = "password"
    env["CODESTORY_NEO4J__DATABASE"] = "neo4j"
    # Set in os.environ for current process (pytest test process)
    os.environ["CODESTORY_NEO4J__URI"] = bolt_url
    os.environ["CODESTORY_NEO4J__USERNAME"] = "neo4j"
    os.environ["CODESTORY_NEO4J__PASSWORD"] = "password"
    os.environ["CODESTORY_NEO4J__DATABASE"] = "neo4j"
    os.environ["NEO4J_URI"] = bolt_url
    os.environ["NEO4J_USERNAME"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "password"
    os.environ["NEO4J_DATABASE"] = "neo4j"
    print(f"[conftest DEBUG] Set CODESTORY_NEO4J__URI={env['CODESTORY_NEO4J__URI']}")

    # Neo4j health check: wait for dbms.components to succeed
    neo4j_ready = False
    for attempt in range(30):
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                bolt_url, auth=("neo4j", "password")
            )
            with driver.session() as session:
                result = session.run("CALL dbms.components()")
                _ = result.single()
            neo4j_ready = True
            print("[conftest DEBUG] Neo4j is ready.")
            break
        except Exception as e:
            print(f"[conftest DEBUG] Waiting for Neo4j to be ready... ({e})")
            time.sleep(1)
        finally:
            if 'driver' in locals():
                driver.close()
    if not neo4j_ready:
        raise RuntimeError("Neo4j did not become ready in time.")
    # Wait for a few seconds to ensure Neo4j is fully ready before starting the backend
    print("[conftest DEBUG] Sleeping 5 seconds to ensure Neo4j is fully ready before starting the backend.")
    import time
    time.sleep(5)

    print(f"[conftest DEBUG] Neo4j testcontainer started with URI: {bolt_url}, username: neo4j, password: password")
    # Health check: wait for Neo4j to be ready before starting the backend

    # --- CRITICAL: Clear settings cache so backend picks up new env vars ---
    from codestory.config.settings import refresh_settings
    refresh_settings()
    print("[conftest DEBUG] Called refresh_settings() after setting Neo4j/Redis env vars.")
    from neo4j import GraphDatabase
    from neo4j.exceptions import ServiceUnavailable
    for attempt in range(30):
        try:
            driver = GraphDatabase.driver(bolt_url, auth=("neo4j", "password"))
            with driver.session() as session:
                result = session.run("RETURN 1 AS ready")
                if result.single()["ready"] == 1:
                    print("[conftest DEBUG] Neo4j is ready (pre-Redis).")
                    break
        except ServiceUnavailable as e:
            print(f"[conftest DEBUG] Waiting for Neo4j to be ready (pre-Redis)... ({e})")
            time.sleep(1)
    else:
        pytest.fail("Neo4j did not become ready in time (pre-Redis).")
    driver.close()
    # Move the entire test execution inside the RedisContainer context to keep Redis alive
    def _run_with_redis():
        import os
        os.makedirs("test_container_logs", exist_ok=True)
        debug_log_path = "test_container_logs/cli_integration_debug.log"
        with open(debug_log_path, "a") as f:
            f.write("[conftest DEBUG] LOGGING INITIALIZED\n")
        # Find a free port on the host for Redis
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            free_port = s.getsockname()[1]
        redis = RedisContainer("redis:7.2.4-alpine", auto_remove=False).with_bind_ports(6379, free_port)
        with redis:
            import time  # Ensure time is available for sleep
            # Debug: print docker ps after starting Redis container
            import subprocess
            print("[conftest DEBUG] Docker ps output after starting Redis container:")
            try:
                ps_output = subprocess.check_output(["docker", "ps", "-a"], text=True)
                print(ps_output)
            except Exception as e:
                print(f"[conftest DEBUG] Could not run docker ps: {e}")
            # --- Get host-mapped ports for Neo4j and Redis ---
            from urllib.parse import urlparse
            parsed = urlparse(bolt_url)
            # Always use localhost for host processes (pytest, subprocesses) to access testcontainer ports
            neo4j_host = parsed.hostname or "localhost"
            redis_host = "localhost"
            neo4j_port = parsed.port or 7687
            neo4j_uri = f"bolt://{neo4j_host}:{neo4j_port}"

            redis_port = redis.get_exposed_port(6379)
            redis_url = f"redis://{redis_host}:{redis_port}/0"
            print(f"[conftest DEBUG] Redis dynamic port: {redis_port}")
            print(f"[conftest DEBUG] Redis dynamic URL: {redis_url}")
            # Print docker ps and port mapping for Redis
            import subprocess
            try:
                ps_output = subprocess.check_output(["docker", "ps", "-a"], text=True)
                print("[conftest DEBUG] Docker ps output after Redis start:")
                print(ps_output)
            except Exception as e:
                print(f"[conftest DEBUG] Could not run docker ps: {e}")
            # Print environment before starting worker/backend
            debug_log_path = "test_container_logs/cli_integration_debug.log"
            def log_debug(msg):
                print(msg)
                try:
                    with open(debug_log_path, "a") as f:
                        f.write(msg + "\n")
                except Exception as e:
                    print(f"[conftest DEBUG] Failed to write to cli_integration_debug.log: {e}")
                # Fallback: also write to cwd
                try:
                    with open("cli_integration_debug.log", "a") as f:
                        f.write(msg + "\n")
                except Exception as e:
                    print(f"[conftest DEBUG] Failed to write to cli_integration_debug.log in cwd: {e}")
            log_debug(f"[conftest DEBUG] Redis dynamic port: {redis_port}")
            log_debug(f"[conftest DEBUG] Redis dynamic URL: {redis_url}")
            log_debug(f"[conftest DEBUG] env['CELERY_BROKER_URL'] = {env.get('CELERY_BROKER_URL')}")
            log_debug(f"[conftest DEBUG] os.environ['CELERY_BROKER_URL'] = {os.environ.get('CELERY_BROKER_URL')}")
            log_debug(f"[conftest DEBUG] env['REDIS_URI'] = {env.get('REDIS_URI')}")
            log_debug(f"[conftest DEBUG] os.environ['REDIS_URI'] = {os.environ.get('REDIS_URI')}")
            log_debug(f"[conftest DEBUG] env['CODESTORY_REDIS__URI'] = {env.get('CODESTORY_REDIS__URI')}")
            log_debug(f"[conftest DEBUG] os.environ['CODESTORY_REDIS__URI'] = {os.environ.get('CODESTORY_REDIS__URI')}")

            # --- Wait for Neo4j to be ready (robust, application-level) ---
            import socket
            import time
            neo4j_ready = False
            for attempt in range(60):
                try:
                    # TCP check
                    with socket.create_connection((neo4j_host, neo4j_port), timeout=2):
                        pass
                    # Application-level check
                    from neo4j import GraphDatabase
                    driver = GraphDatabase.driver(f"bolt://{neo4j_host}:{neo4j_port}", auth=("neo4j", "password"))
                    with driver.session() as session:
                        result = session.run("RETURN 1 AS ready")
                        if result.single()["ready"] == 1:
                            neo4j_ready = True
                            print(f"[conftest DEBUG] Neo4j is ready and accepting Bolt connections on {neo4j_host}:{neo4j_port}.")
                            break
                    driver.close()
                except Exception as e:
                    print(f"[conftest DEBUG] Waiting for Neo4j application on {neo4j_host}:{neo4j_port}... ({e})")
                time.sleep(1)
            if not neo4j_ready:
                raise RuntimeError(f"Neo4j application on {neo4j_host}:{neo4j_port} did not become ready in time.")

            # --- Wait for Redis to be ready (robust, application-level) ---
            redis_ready = False
            for attempt in range(60):
                try:
                    # TCP check
                    with socket.create_connection((redis_host, int(redis_port)), timeout=2):
                        pass
                    # Application-level check
                    import redis as redis_py
                    redis_client = redis_py.Redis.from_url(f"redis://{redis_host}:{redis_port}/0")
                    if redis_client.ping():
                        redis_ready = True
                        print(f"[conftest DEBUG] Redis is ready and accepting connections on {redis_host}:{redis_port}.")
                        break
                except Exception as e:
                    print(f"[conftest DEBUG] Waiting for Redis application on {redis_host}:{redis_port}... ({e})")
                time.sleep(1)
            if not redis_ready:
                raise RuntimeError(f"Redis application on {redis_host}:{redis_port} did not become ready in time.")

            # --- Set all Neo4j/Redis env vars for backend subprocess ---
            for var in [
                "CODESTORY_NEO4J__URI", "NEO4J_URI", "NEO4J__URI",
                "CODESTORY_NEO4J__USERNAME", "NEO4J_USERNAME", "NEO4J__USERNAME",
                "CODESTORY_NEO4J__PASSWORD", "NEO4J_PASSWORD", "NEO4J__PASSWORD",
                "CODESTORY_NEO4J__DATABASE", "NEO4J_DATABASE", "NEO4J__DATABASE"
            ]:
                if "USERNAME" in var:
                    env[var] = "neo4j"
                elif "PASSWORD" in var:
                    env[var] = "password"
                elif "DATABASE" in var:
                    env[var] = "neo4j"
                elif "URI" in var:
                    env[var] = neo4j_uri

            for var in [
                "CODESTORY_REDIS__URI", "REDIS_URI", "REDIS__URI",
                "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND"
            ]:
                env[var] = redis_url
                os.environ[var] = redis_url

            # Set CODESTORY_TEST_PORT and related vars for backend subprocess
            # (rest of the fixture remains unchanged)

            # --- Begin Redis container log capture ---
            import threading
            from datetime import datetime
            os.makedirs("test_container_logs", exist_ok=True)
            session_id = None
            try:
                session_id = str(env.get("PORT") or env.get("CODESTORY_TEST_PORT") or int(time.time()))
            except Exception:
                session_id = str(int(time.time()))
            redis_log_path = f"test_container_logs/redis_{session_id}.log"
            _redis_log_stop = threading.Event()
            def _stream_redis_logs(container, log_path, stop_event):
                try:
                    with open(log_path, "wb") as f:
                        for chunk in container.get_wrapped_container().logs(stream=True, stdout=True, stderr=True, follow=True):
                            if stop_event.is_set():
                                break
                            f.write(chunk)
                            f.flush()
                except Exception as e:
                    print(f"[conftest ERROR] Redis log streaming failed: {e}")
            _redis_log_thread = threading.Thread(
                target=_stream_redis_logs,
                args=(redis, redis_log_path, _redis_log_stop),
                daemon=True,
            )
            _redis_log_thread.start()
            # --- End Redis container log capture ---

            # Redis health check: wait for PING to succeed
            # Wait for Redis to be ready and accepting connections on the host-mapped port
            redis_ready = False
            for attempt in range(60):
                try:
                    redis_client = redis_py.Redis.from_url(redis_url)
                    if redis_client.ping():
                        redis_ready = True
                        print(f"[conftest DEBUG] Redis is ready and accepting connections on {redis_url}.")
                        break
                except Exception as e:
                    print(f"[conftest DEBUG] Waiting for Redis to be ready on {redis_url}... ({e})")
                time.sleep(1)
            if not redis_ready:
                raise RuntimeError(f"Redis did not become ready in time on {redis_url}.")
    
            # Wait for Neo4j to be ready and accepting connections on the host-mapped port
            neo4j_ready = False
            for attempt in range(60):
                try:
                    from neo4j import GraphDatabase
                    driver = GraphDatabase.driver(neo4j_uri, auth=("neo4j", "password"))
                    with driver.session() as session:
                        result = session.run("RETURN 1 AS ready")
                        if result.single()["ready"] == 1:
                            neo4j_ready = True
                            print(f"[conftest DEBUG] Neo4j is ready and accepting connections on {neo4j_uri}.")
                            break
                except Exception as e:
                    print(f"[conftest DEBUG] Waiting for Neo4j to be ready on {neo4j_uri}... ({e})")
                time.sleep(1)
            if not neo4j_ready:
                raise RuntimeError(f"Neo4j did not become ready in time on {neo4j_uri}.")
    
            # Extra: print docker ps for debugging
            import subprocess
            print("[conftest DEBUG] Docker ps output before starting backend/worker:")
            try:
                ps_output = subprocess.check_output(["docker", "ps", "-a"], text=True)
                print(ps_output)
            except Exception as e:
                print(f"[conftest DEBUG] Could not run docker ps: {e}")

            # Set OpenAI environment variables for service/worker
            from dotenv import dotenv_values
            env_config = dotenv_values(".env")
            chat_model = env_config.get("AZURE_OPENAI_MODEL_CHAT") or env_config.get("AZURE_OPENAI__DEPLOYMENT_ID") or "gpt-4.1"
            reasoning_model = env_config.get("AZURE_OPENAI_MODEL_REASONING") or env_config.get("AZURE_OPENAI__REASONING_MODEL") or "o3"
            env["AZURE_OPENAI_ENDPOINT"] = env_config.get("AZURE_OPENAI_ENDPOINT", "https://ai-adapt-oai-eastus2.openai.azure.com/")
            env["AZURE_OPENAI_KEY"] = env_config.get("AZURE_OPENAI_KEY", "b892dc164a634fc49bd07bcbbf9d1a76")
            env["AZURE_OPENAI_API_VERSION"] = env_config.get("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
            env["AZURE_OPENAI_MODEL_CHAT"] = chat_model
            env["AZURE_OPENAI_MODEL_REASONING"] = reasoning_model
            env["AZURE_OPENAI__ENDPOINT"] = env_config.get("AZURE_OPENAI__ENDPOINT", "https://ai-adapt-oai-eastus2.openai.azure.com/")
            env["AZURE_OPENAI__API_KEY"] = env_config.get("AZURE_OPENAI__API_KEY", "b892dc164a634fc49bd07bcbbf9d1a76")
            env["AZURE_OPENAI__API_VERSION"] = env_config.get("AZURE_OPENAI__API_VERSION", "2025-01-01-preview")
            env["AZURE_OPENAI__DEPLOYMENT_ID"] = chat_model
            env["AZURE_OPENAI__REASONING_MODEL"] = reasoning_model
            env["CELERY_TASK_ALWAYS_EAGER"] = "False"
            env["CELERY_TASK_EAGER_PROPAGATES"] = "False"

            # Allocate a free port for the service
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", 0))
                svc_port = s.getsockname()[1]

            env["CODESTORY_TEST_PORT"] = str(svc_port)
            env["CODESTORY_TEST_HOST"] = "localhost"
            env["PORT"] = str(svc_port)
            env["CODESTORY_SERVICE__PORT"] = str(svc_port)
            os.environ["CODESTORY_SERVICE__PORT"] = str(svc_port)
            os.environ["PORT"] = str(svc_port)
            os.environ["CODESTORY_TEST_PORT"] = str(svc_port)
            env["CODESTORY_SERVICE_URL"] = f"http://localhost:{svc_port}/v1"
            os.environ["CODESTORY_SERVICE_URL"] = f"http://localhost:{svc_port}/v1"
            # Debug: print Redis URI just before backend launch
            print(f"[conftest DEBUG] (pre-backend) CODESTORY_REDIS__URI={env.get('CODESTORY_REDIS__URI')}, os.environ={os.environ.get('CODESTORY_REDIS__URI')}")
            print(f"[conftest DEBUG] OpenAI config: chat_model={chat_model}, reasoning_model={reasoning_model}")
            print(f"[conftest DEBUG] AZURE_OPENAI_ENDPOINT={env.get('AZURE_OPENAI_ENDPOINT')}")
            print(f"[conftest DEBUG] AZURE_OPENAI_KEY={env.get('AZURE_OPENAI_KEY')}")
            print(f"[conftest DEBUG] AZURE_OPENAI_API_VERSION={env.get('AZURE_OPENAI_API_VERSION')}")
            print(f"[conftest DEBUG] AZURE_OPENAI_MODEL_CHAT={env.get('AZURE_OPENAI_MODEL_CHAT')}")
            print(f"[conftest DEBUG] AZURE_OPENAI_MODEL_REASONING={env.get('AZURE_OPENAI_MODEL_REASONING')}")
            print(f"[conftest DEBUG] AZURE_OPENAI__ENDPOINT={env.get('AZURE_OPENAI__ENDPOINT')}")
            print(f"[conftest DEBUG] AZURE_OPENAI__API_KEY={env.get('AZURE_OPENAI__API_KEY')}")
            print(f"[conftest DEBUG] AZURE_OPENAI__API_VERSION={env.get('AZURE_OPENAI__API_VERSION')}")
            print(f"[conftest DEBUG] AZURE_OPENAI__DEPLOYMENT_ID={env.get('AZURE_OPENAI__DEPLOYMENT_ID')}")
            print(f"[conftest DEBUG] AZURE_OPENAI__REASONING_MODEL={env.get('AZURE_OPENAI__REASONING_MODEL')}")

            # ------------------------------------------------------------------
            # Launch background processes: Celery worker (ingestion) and API
            # ------------------------------------------------------------------
            service_log = f".code_story_session_logs/codestory_service_{svc_port}.log"
            worker_log = f".code_story_session_logs/codestory_worker_{svc_port}.log"
            os.makedirs(".code_story_session_logs", exist_ok=True)

            print(f"[conftest DEBUG] Redis URL: {redis_url}")
            print(f"[conftest DEBUG] Service port: {svc_port}")
            print(f"[conftest DEBUG] Worker log path: {worker_log}")

            worker_proc = None
            proc = None

            # Open log files (append mode to avoid truncation if reused)
            worker_out = open(worker_log, "a", buffering=1)
            service_out = open(service_log, "a", buffering=1)

            # Start Celery worker first so tasks can be consumed immediately
            worker_cmd = [
                sys.executable,
                "-m",
                "celery",
                "-A",
                "codestory.ingestion_pipeline.celery_app:app",
                "worker",
                "-l",
                "info",
                "-Q",
                "high,default,low",
            ]
            # Debug: print env vars for Celery worker
            print(f"[conftest DEBUG] (pre-worker) CODESTORY_REDIS__URI={env.get('CODESTORY_REDIS__URI')}, REDIS__URI={env.get('REDIS__URI')}, CELERY_BROKER_URL={env.get('CELERY_BROKER_URL')}, CELERY_RESULT_BACKEND={env.get('CELERY_RESULT_BACKEND')}")
            # Ensure no stale Celery worker processes are running
            import psutil
            for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
                try:
                    if "celery" in " ".join(proc.info["cmdline"]):
                        print(f"[conftest DEBUG] Terminating stale Celery worker process: PID={proc.info['pid']}, CMD={proc.info['cmdline']}")
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except Exception:
                            proc.kill()
                except Exception:
                    pass

            print(f"[conftest DEBUG] About to start Celery worker with:")
            print(f"  env['CELERY_BROKER_URL'] = {env.get('CELERY_BROKER_URL')}")
            print(f"  os.environ['CELERY_BROKER_URL'] = {os.environ.get('CELERY_BROKER_URL')}")
            print(f"  redis_url = {redis_url}")
            print(f"  redis_port = {redis_port}")
            worker_proc = subprocess.Popen(
                worker_cmd,
                env=env.copy(),
                stdout=worker_out,
                stderr=subprocess.STDOUT,
            )

            # Wait for Celery worker to be fully ready before starting backend
            import time
            import redis as redis_py
            print("[conftest DEBUG] Waiting for Celery worker to be ready (application-level check)...")
            celery_ready = False
            for attempt in range(60):
                try:
                    # Application-level check: try to connect to Redis and ping
                    redis_url_check = env.get("CELERY_BROKER_URL") or env.get("CODESTORY_REDIS__URI") or env.get("REDIS__URI")
                    if redis_url_check:
                        redis_client = redis_py.Redis.from_url(redis_url_check)
                        if redis_client.ping():
                            # Try to ping the Celery worker using the inspect API
                            from celery import Celery
                            celery_app = Celery(broker=redis_url_check, backend=redis_url_check)
                            i = celery_app.control.inspect(timeout=2)
                            active = i.active()
                            if active is not None:
                                celery_ready = True
                                print(f"[conftest DEBUG] Celery worker is active and responding to inspect.ping() at {redis_url_check}.")
                                break
                except Exception as e:
                    print(f"[conftest DEBUG] Waiting for Celery worker to be ready at {redis_url_check}... ({e})")
                time.sleep(1)
            if not celery_ready:
                print("[conftest ERROR] Celery worker did not become ready in time. Printing worker log for diagnosis.")
                import glob
                worker_logs = sorted(glob.glob(".code_story_session_logs/codestory_worker_*.log"), key=os.path.getmtime, reverse=True)
                if worker_logs:
                    with open(worker_logs[0], "r") as f:
                        print("[conftest ERROR] Last 100 lines of Celery worker log:")
                        lines = f.readlines()
                        for line in lines[-100:]:
                            print(line.rstrip())
                raise RuntimeError(f"Celery worker did not become ready in time at {redis_url_check}.")
            print("[conftest DEBUG] Celery worker is ready. Proceeding to start backend.")

            # Start FastAPI service via uvicorn
            service_cmd = [
                sys.executable,
                "-m",
                "uvicorn",
                "src.codestory_service.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                str(svc_port),
            ]
            print(f"[conftest DEBUG] DISABLE_OPENAI_HEALTHCHECK in env: {env.get('DISABLE_OPENAI_HEALTHCHECK')}")
            print(f"[conftest DEBUG] Full env for service: {env}")
            print(f"[conftest DEBUG] Starting service: {' '.join(service_cmd)}")
            proc = subprocess.Popen(
                service_cmd,
                env=env,
                stdout=service_out,
                stderr=subprocess.STDOUT,
            )

            # Wait for /health endpoint to become available
            health_url = f"http://localhost:{svc_port}/v1/health"
            for attempt in range(60):
                try:
                    r = requests.get(health_url, timeout=2)
                    if r.status_code == 200:
                        print("[conftest DEBUG] Service health endpoint ready.")
                        break
                except Exception:
                    pass
                time.sleep(1)
            else:
                print("[conftest ERROR] Service failed to start within timeout.")
                # Print last 100 lines of service log for diagnosis
                try:
                    with open(service_log, "r") as f:
                        lines = f.readlines()
                        print("[conftest ERROR] Last 100 lines of service log:")
                        for line in lines[-100:]:
                            print(line.rstrip())
                except Exception as e:
                    print(f"[conftest ERROR] Could not read service log: {e}")

            # Yield the dynamic service port so tests can construct base URL
            yield svc_port

            # Cleanup after test session
            if proc and proc.poll() is None:
                print("[conftest DEBUG] Terminating service process.")
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    print("[conftest DEBUG] Killing unresponsive service process.")
                    proc.kill()
            if worker_proc and worker_proc.poll() is None:
                print("[conftest DEBUG] Terminating Celery worker process.")
                worker_proc.terminate()
                try:
                    worker_proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    print("[conftest DEBUG] Killing unresponsive Celery worker process.")
                    worker_proc.kill()
    # Actually run the test fixture logic inside the RedisContainer context
    yield from _run_with_redis()

# Pytest hooks – auto-mark integration tests
from pathlib import Path
import tempfile, json, time, requests

_INTEGRATION_ROOT = Path(__file__).parent.resolve()

def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        item_path = Path(str(item.fspath)).resolve()
        if item_path.is_relative_to(_INTEGRATION_ROOT):
            item.add_marker(pytest.mark.integration)

import pytest

@pytest.fixture
def neo4j_connector():
    """Provide Neo4j connector for integration tests."""
    try:
        from codestory.graphdb.neo4j_connector import Neo4jConnector
        import os
        uri = os.environ.get("NEO4J_URI")
        if not uri:
            import pytest
            pytest.fail("NEO4J_URI must be set by the testcontainer fixture.")
        username = os.environ.get("NEO4J_USERNAME", "neo4j")
        password = os.environ.get("NEO4J_PASSWORD", "password")
        # Always use the default "neo4j" database for test consistency
        database = "neo4j"
        connector = Neo4jConnector(
            uri=uri,
            username=username,
            password=password,
            database=database
        )
        yield connector
        # Cleanup is handled by the session-scoped prepare_containerized_database fixture
    except Exception as e:
        # If Neo4j is not available, provide a mock
        from unittest.mock import MagicMock
        mock_connector = MagicMock()
        mock_connector.execute_query.return_value = []
        yield mock_connector

import pytest
import subprocess
import sys
@pytest.fixture(scope="session", autouse=True)
def preflight_container_checks():
    """
    Preflight check for Docker, Redis, Neo4j, and orphaned containers.
    Fails the test session early with a clear diagnostic if any critical dependency is missing.
    """
    # 1. Check Docker daemon
    try:
        import docker
        client = docker.from_env()
        client.ping()
    except Exception as e:
        pytest.exit(f"FATAL: Docker is not available or not running: {e}", returncode=1)

    # 2. Check for Docker credential helper
    cred_helper = os.environ.get("DOCKER_CREDENTIAL_HELPER", "docker-credential-desktop")
    if not shutil.which(cred_helper):
        print(f"WARNING: Docker credential helper '{cred_helper}' not found in PATH. Some image pulls may fail.")

    # 3. Check for orphaned containers/volumes
    try:
        # List all containers with names matching known test containers
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}"],
            capture_output=True, text=True, check=True
        )
        names = result.stdout.splitlines()
        test_names = [
            "codestory-service", "codestory-worker", "codestory-neo4j", "codestory-redis",
            "codestory-blarify-test"
        ]
        orphans = [n for n in names if n in test_names]
        if orphans:
            print(f"WARNING: Found orphaned containers: {orphans}. Attempting to remove them...")
            for n in orphans:
                subprocess.run(["docker", "rm", "-f", n], capture_output=True)
    except Exception as e:
        print(f"WARNING: Could not check or cleanup orphaned containers: {e}")

    # 4. Check for orphaned Docker Compose projects
    try:
        subprocess.run(
            ["docker-compose", "down", "-v", "--remove-orphans"],
            capture_output=True, text=True
        )
    except Exception as e:
        print(f"WARNING: Could not run 'docker-compose down': {e}")

    # 5. Check for Redis and Neo4j testcontainers health (will be managed by testcontainer fixtures)
    # No-op here; actual health checks are performed in the testcontainer fixtures.

    print("Preflight container checks passed. All critical dependencies are available.")







@pytest.fixture(scope="session", autouse=True)
def aggressive_docker_cleanup():
    """
    Aggressively clean up all containers, volumes, and networks matching the test project prefix.
    Fail the test session if any cannot be removed.
    """
    import subprocess
    import sys

    # Remove all containers matching known test/project prefixes
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}"],
            capture_output=True, text=True, check=True
        )
        names = result.stdout.splitlines()
        test_prefixes = ["codestory-", "csnet_", "code-story_"]
        to_remove = [n for n in names if any(n.startswith(p) for p in test_prefixes)]
        if to_remove:
            print(f"AGGRESSIVE CLEANUP: Removing containers: {to_remove}")
            for n in to_remove:
                rm_result = subprocess.run(["docker", "rm", "-f", n], capture_output=True)
                if rm_result.returncode != 0:
                    print(f"FATAL: Could not remove container {n}: {rm_result.stderr}")
                    pytest.exit(f"FATAL: Could not remove container {n}", returncode=1)
    except Exception as e:
        print(f"FATAL: Could not list/remove containers: {e}")
        pytest.exit(f"FATAL: Could not list/remove containers: {e}", returncode=1)

    # Remove all volumes matching test/project prefixes
    try:
        result = subprocess.run(
            ["docker", "volume", "ls", "--format", "{{.Name}}"],
            capture_output=True, text=True, check=True
        )
        volumes = result.stdout.splitlines()
        to_remove = [v for v in volumes if any(v.startswith(p) for p in test_prefixes)]
        if to_remove:
            print(f"AGGRESSIVE CLEANUP: Removing volumes: {to_remove}")
            for v in to_remove:
                rm_result = subprocess.run(["docker", "volume", "rm", "-f", v], capture_output=True)
                if rm_result.returncode != 0:
                    print(f"FATAL: Could not remove volume {v}: {rm_result.stderr}")
                    pytest.exit(f"FATAL: Could not remove volume {v}", returncode=1)
    except Exception as e:
        print(f"FATAL: Could not list/remove volumes: {e}")
        pytest.exit(f"FATAL: Could not list/remove volumes: {e}", returncode=1)

    # Remove all networks matching test/project prefixes
    try:
        result = subprocess.run(
            ["docker", "network", "ls", "--format", "{{.Name}}"],
            capture_output=True, text=True, check=True
        )
        networks = result.stdout.splitlines()
        to_remove = [n for n in networks if any(n.startswith(p) for p in test_prefixes)]
        if to_remove:
            print(f"AGGRESSIVE CLEANUP: Removing networks: {to_remove}")
            for n in to_remove:
                rm_result = subprocess.run(["docker", "network", "rm", n], capture_output=True)
                # Don't fail on network removal errors (may be in use)
    except Exception as e:
        print(f"WARNING: Could not list/remove networks: {e}")

    print("AGGRESSIVE CLEANUP: Complete. All test containers, volumes, and networks removed.")

@pytest.fixture(scope="session", autouse=True)
def aggressive_docker_cleanup_with_retry():
    """
    Aggressively clean up all containers, volumes, and networks matching the test project prefix.
    Retry removal for containers in "removing" state. Run docker-compose down for all known files.
    Fail the test session if any cannot be removed.
    """
    import subprocess
    import sys
    import time

    test_prefixes = ["codestory-", "csnet_", "code-story_"]
    compose_files = [
        "docker-compose.yml",
        "docker-compose.test.yml",
    ]
    max_retries = 5

    # Remove all containers matching known test/project prefixes, with retry
    for attempt in range(max_retries):
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}} {{.Status}}"],
            capture_output=True, text=True, check=True
        )
        lines = result.stdout.splitlines()
        to_remove = []
        for line in lines:
            parts = line.split(" ", 1)
            if not parts:
                continue
            name = parts[0]
            status = parts[1] if len(parts) > 1 else ""
            if any(name.startswith(p) for p in test_prefixes):
                to_remove.append((name, status))
        if not to_remove:
            break
        print(f"AGGRESSIVE CLEANUP: Attempt {attempt+1}: Removing containers: {to_remove}")
        for name, status in to_remove:
            rm_result = subprocess.run(["docker", "rm", "-f", name], capture_output=True)
            if rm_result.returncode != 0:
                print(f"WARNING: Could not remove container {name}: {rm_result.stderr}")
        # Wait for "removing" containers to disappear
        time.sleep(2)
    # Final check
    result = subprocess.run(
        ["docker", "ps", "-a", "--format", "{{.Names}}"],
        capture_output=True, text=True, check=True
    )
    names = result.stdout.splitlines()
    still_present = [n for n in names if any(n.startswith(p) for p in test_prefixes)]
    if still_present:
        print(f"FATAL: Could not remove containers: {still_present}")
        pytest.exit(f"FATAL: Could not remove containers: {still_present}", returncode=1)

    # Remove all volumes matching test/project prefixes
    result = subprocess.run(
        ["docker", "volume", "ls", "--format", "{{.Name}}"],
        capture_output=True, text=True, check=True
    )
    volumes = result.stdout.splitlines()
    to_remove = [v for v in volumes if any(v.startswith(p) for p in test_prefixes)]
    if to_remove:
        print(f"AGGRESSIVE CLEANUP: Removing volumes: {to_remove}")
        for v in to_remove:
            rm_result = subprocess.run(["docker", "volume", "rm", "-f", v], capture_output=True)
            if rm_result.returncode != 0:
                print(f"FATAL: Could not remove volume {v}: {rm_result.stderr}")
                pytest.exit(f"FATAL: Could not remove volume {v}", returncode=1)

    # Remove all networks matching test/project prefixes
    result = subprocess.run(
        ["docker", "network", "ls", "--format", "{{.Name}}"],
        capture_output=True, text=True, check=True
    )
    networks = result.stdout.splitlines()
    to_remove = [n for n in networks if any(n.startswith(p) for p in test_prefixes)]
    if to_remove:
        print(f"AGGRESSIVE CLEANUP: Removing networks: {to_remove}")
        for n in to_remove:
            subprocess.run(["docker", "network", "rm", n], capture_output=True)

    # Run docker-compose down for all known files and project names
    for compose_file in compose_files:
        if not os.path.exists(compose_file):
            continue
        for prefix in test_prefixes:
            project_name = prefix.strip("-_")
            try:
                subprocess.run(
                    ["docker-compose", "-p", project_name, "-f", compose_file, "down", "-v", "--remove-orphans"],
                    capture_output=True, text=True
                )
            except Exception as e:
                print(f"WARNING: Could not run docker-compose down for {compose_file} project {project_name}: {e}")

    print("AGGRESSIVE CLEANUP: Complete. All test containers, volumes, and networks removed.")
