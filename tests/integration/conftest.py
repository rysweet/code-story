import multiprocessing
multiprocessing.set_start_method("fork", force=True)
import os

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

@pytest.fixture(scope="session", autouse=True)
def test_containers_and_service():
    """
    Start Neo4j and Redis using testcontainers, configure environment, and launch the Code Story service and worker for integration tests.
    """
    with Neo4jContainer("neo4j:community") as neo4j:
        bolt_url = f"bolt://{neo4j.get_container_host_ip()}:{neo4j.get_exposed_port(7687)}"
        os.environ["NEO4J_URI"] = bolt_url
        os.environ["NEO4J_USERNAME"] = "neo4j"
        os.environ["NEO4J_PASSWORD"] = "password"
        os.environ["NEO4J_DATABASE"] = "neo4j"
        # Also set the settings-compatible env vars for all subprocesses
        os.environ["CODESTORY_NEO4J__URI"] = bolt_url
        os.environ["CODESTORY_NEO4J__USERNAME"] = "neo4j"
        os.environ["CODESTORY_NEO4J__PASSWORD"] = "password"
        os.environ["CODESTORY_NEO4J__DATABASE"] = "neo4j"
        print(f"[conftest DEBUG] Set CODESTORY_NEO4J__URI={os.environ['CODESTORY_NEO4J__URI']}")
        with RedisContainer("redis:7.2.4-alpine") as redis:
            redis_url = f"redis://{redis.get_container_host_ip()}:{redis.get_exposed_port(6379)}/0"
            os.environ["REDIS__URI"] = redis_url
            os.environ["CELERY_BROKER_URL"] = redis_url
            os.environ["CELERY_RESULT_BACKEND"] = redis_url
            # Set OpenAI environment variables for service/worker
            # Set both single-underscore and double-underscore OpenAI env vars for compatibility
            os.environ["AZURE_OPENAI_ENDPOINT"] = "https://ai-adapt-oai-eastus2.openai.azure.com/"
            os.environ["AZURE_OPENAI_KEY"] = "b892dc164a634fc49bd07bcbbf9d1a76"
            os.environ["AZURE_OPENAI_API_VERSION"] = "2025-01-01-preview"
            os.environ["AZURE_OPENAI_MODEL_CHAT"] = "o3"
            os.environ["AZURE_OPENAI_MODEL_REASONING"] = "o3"
            os.environ["AZURE_OPENAI__ENDPOINT"] = "https://ai-adapt-oai-eastus2.openai.azure.com/"
            os.environ["AZURE_OPENAI__API_KEY"] = "b892dc164a634fc49bd07bcbbf9d1a76"
            os.environ["AZURE_OPENAI__API_VERSION"] = "2025-01-01-preview"
            os.environ["AZURE_OPENAI__DEPLOYMENT_ID"] = "o3"
            os.environ["AZURE_OPENAI__REASONING_MODEL"] = "o3"
            # Enable synchronous Celery execution for tests
            os.environ["CELERY_TASK_ALWAYS_EAGER"] = "False"
            os.environ["CELERY_TASK_EAGER_PROPAGATES"] = "False"

            # Allocate a free port for the service
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", 0))
                svc_port = s.getsockname()[1]

            os.environ["CODESTORY_TEST_PORT"] = str(svc_port)
            os.environ["CODESTORY_TEST_HOST"] = "localhost"
            os.environ["PORT"] = str(svc_port)

            # Start the Code Story service as a subprocess using uvicorn
            service_log = f".code_story_session_logs/codestory_service_{svc_port}.log"
            os.makedirs(".code_story_session_logs", exist_ok=True)
            # Start the ingestion worker as a subprocess BEFORE the service
            print(f"[conftest DEBUG] Redis URL: {redis_url}")
            print(f"[conftest DEBUG] Service port: {svc_port}")
            worker_log = f".code_story_session_logs/codestory_worker_{svc_port}.log"
            print(f"[conftest DEBUG] Worker log path: {worker_log}")
            worker_proc = subprocess.Popen(
                [
                    "celery", "-A", "src.codestory.ingestion_pipeline.celery_app", "worker",
                    "--loglevel=INFO",
                    "--concurrency=1",
                    "--queues=ingestion",
                    "--hostname=worker@%h",
                    "--pool=solo",
                ],
                env=os.environ.copy(),
                stdout=open(worker_log, "w"),
                stderr=subprocess.STDOUT,
                start_new_session=True,
                close_fds=True,
                stdin=subprocess.DEVNULL,
            )

            # Wait longer for the worker to be ready and log status
            print("[conftest DEBUG] Waiting for ingestion worker to start...")
            for i in range(20):
                if worker_proc.poll() is not None:
                    print(f"[conftest ERROR] Worker process exited early with code {worker_proc.returncode}")
                    break
                time.sleep(1)
            print("[conftest DEBUG] Worker startup wait complete.")

            # Now start the Code Story service as a subprocess using uvicorn
            proc = subprocess.Popen(
                [
                    sys.executable, "-m", "uvicorn",
                    "src.codestory_service.main:app",
                    "--host", "0.0.0.0",
                    "--port", str(svc_port),
                ],
                env=os.environ.copy(),
                stdout=open(service_log, "w"),
                stderr=subprocess.STDOUT,
            )

            # Wait for the service to become healthy
            health_url = f"http://localhost:{svc_port}/health"
            for _ in range(60):
                try:
                    resp = requests.get(health_url, timeout=1)
                    if resp.status_code == 200:
                        break
                except Exception:
                    time.sleep(0.5)
            else:
                proc.terminate()
                proc.wait()
                raise RuntimeError(f"Code Story service did not become healthy on {health_url}")

            yield

            # After test run, check for worker log existence
            if not os.path.exists(worker_log):
                print(f"[conftest ERROR] Worker log file not found: {worker_log}")

            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:
                proc.kill()

            worker_proc.terminate()
            try:
                worker_proc.wait(timeout=10)
            except Exception:
                worker_proc.kill()

# Pytest hooks – auto-mark integration tests
from pathlib import Path
import tempfile, json, time, requests

_INTEGRATION_ROOT = Path(__file__).parent.resolve()

def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        item_path = Path(str(item.fspath)).resolve()
        if item_path.is_relative_to(_INTEGRATION_ROOT):
            item.add_marker(pytest.mark.integration)
