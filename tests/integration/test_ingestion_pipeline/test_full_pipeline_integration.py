"""Integration tests for the full ingestion pipeline.

These tests verify that the complete ingestion pipeline can process a
repository through all workflow steps correctly using real services.
"""

import os

# Determine Neo4j port based on CI environment
ci_env = os.environ.get("CI") == "true"
neo4j_port = "7687" if ci_env else "7688"
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
import logging
import psutil

import pytest

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from codestory.config.settings import Settings
from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.ingestion_pipeline.step import PipelineStep, StepStatus
from codestory.ingestion_pipeline.manager import PipelineManager


def ensure_services_running():
    """Ensure Neo4j and Redis services are running, start them if not."""
    # Check and start Neo4j if needed
    try:
        # Try to connect to Neo4j
        connector = Neo4jConnector(
            uri=f"bolt://localhost:{neo4j_port}",
            username="neo4j",
            password="password",
            database="testdb",
        )
        connector.execute_query("RETURN 1 as test")
        connector.close()
        logger.info("Neo4j is running")
    except Exception as e:
        logger.error(f"Neo4j is not running: {e}")
        logger.info("Starting Neo4j container...")

        # Start Neo4j container
        subprocess.run(["docker-compose", "-f", "docker-compose.test.yml", "up", "-d", "neo4j"])

        # Wait for Neo4j to be ready
        max_attempts = 30
        for i in range(max_attempts):
            try:
                connector = Neo4jConnector(
                    uri=f"bolt://localhost:{neo4j_port}",
                    username="neo4j",
                    password="password",
                    database="testdb",
                )
                connector.execute_query("RETURN 1 as test")
                connector.close()
                logger.info("Neo4j is now running")
                break
            except Exception:
                logger.info(f"Waiting for Neo4j to start (attempt {i+1}/{max_attempts})...")
                time.sleep(2)
        else:
            raise RuntimeError("Failed to start Neo4j container after multiple attempts")

    # Check and start Redis if needed
    try:
        import redis
        client = redis.from_url("redis://localhost:6380/0")
        client.ping()
        logger.info("Redis is running")
    except Exception as e:
        logger.error(f"Redis is not running: {e}")
        logger.info("Starting Redis container...")

        # Start Redis container
        subprocess.run(["docker-compose", "-f", "docker-compose.test.yml", "up", "-d", "redis"])

        # Wait for Redis to be ready
        max_attempts = 15
        for i in range(max_attempts):
            try:
                client = redis.from_url("redis://localhost:6380/0")
                client.ping()
                logger.info("Redis is now running")
                break
            except Exception:
                logger.info(f"Waiting for Redis to start (attempt {i+1}/{max_attempts})...")
                time.sleep(2)
        else:
            raise RuntimeError("Failed to start Redis container after multiple attempts")


class TestFullPipelineIntegration(unittest.TestCase):
    """Test the full ingestion pipeline with real services."""

    @classmethod
    def setUpClass(cls):
        """Set up the test environment and start required services."""
        # Ensure required services are running (Neo4j, Redis, Celery)
        ensure_services_running()

        # Configure settings for the test
        os.environ["NEO4J_URI"] = f"bolt://localhost:{neo4j_port}"
        os.environ["NEO4J__URI"] = f"bolt://localhost:{neo4j_port}"
        os.environ["NEO4J_USERNAME"] = "neo4j"
        os.environ["NEO4J_PASSWORD"] = "password"
        os.environ["NEO4J__USERNAME"] = "neo4j"
        os.environ["NEO4J__PASSWORD"] = "password"

        # Configure Redis for Celery
        os.environ["REDIS_URI"] = "redis://localhost:6380/0"
        os.environ["REDIS__URI"] = "redis://localhost:6380/0"

        # Create a test repository
        cls.repo_dir = cls._create_test_repo()
        cls.settings = Settings()

        # Create Neo4j connector for the test
        cls.neo4j_connector = Neo4jConnector(
            uri=f"bolt://localhost:{neo4j_port}",
            username="neo4j",
            password="password",
            database="testdb"
        )

        # Start a Celery worker for the tests if needed
        cls.celery_worker_process = cls._ensure_celery_worker_running()

        # Create a basic config file for the PipelineManager
        cls.config_file_path = cls._create_pipeline_config_file()
        
        # Create PipelineManager with the test config file
        cls.pipeline_manager = PipelineManager(config_path=cls.config_file_path)

        # Wait for Neo4j to be ready
        cls._wait_for_neo4j(cls.neo4j_connector)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test resources and stop services."""
        # Clean up the test repository
        if hasattr(cls, 'repo_dir') and cls.repo_dir and os.path.exists(cls.repo_dir):
            shutil.rmtree(cls.repo_dir)
        
        # Clean up temporary config file
        if hasattr(cls, 'config_file_path') and cls.config_file_path and os.path.exists(cls.config_file_path):
            os.unlink(cls.config_file_path)

        # Clean up Neo4j database
        if hasattr(cls, 'neo4j_connector') and cls.neo4j_connector:
            try:
                cls.neo4j_connector.execute_query("MATCH (n) DETACH DELETE n")
                cls.neo4j_connector.close()
            except Exception as e:
                print(f"Error cleaning up Neo4j: {e}")

        # Stop Celery worker if we started it
        if hasattr(cls, 'celery_worker_process') and cls.celery_worker_process:
            cls.celery_worker_process.terminate()
            cls.celery_worker_process.wait(timeout=5)
    
    @classmethod
    def _create_pipeline_config_file(cls):
        """Create a pipeline configuration file for testing."""
        config_content = """
steps:
  - name: filesystem
    concurrency: 1
    ignore_patterns:
      - ".git/"
      - "__pycache__/"
  - name: blarify
    concurrency: 1
  - name: summarizer
    concurrency: 1
    max_tokens_per_file: 4000
  - name: documentation_grapher
    concurrency: 1
    parse_docstrings: true
    
dependencies:
  filesystem: []
  blarify: ["filesystem"]
  summarizer: ["filesystem", "blarify"]
  documentation_grapher: ["filesystem", "summarizer"]

retry:
  max_retries: 2
  back_off_seconds: 1
"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(config_content)
            return f.name

    @classmethod
    def _ensure_celery_worker_running(cls):
        """Start a Celery worker for the tests if one is not already running."""
        # Check if there's a Celery worker already running
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and 'celery' in cmdline and '-A' in cmdline and 'worker' in cmdline:
                    logger.info(f"Found existing Celery worker: {' '.join(cmdline)}")
                    return None
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Start a Celery worker
        logger.info("Starting Celery worker for tests...")
        worker_env = os.environ.copy()
        worker_env["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        process = subprocess.Popen([
            "celery", "-A", "codestory.ingestion_pipeline.celery_app", "worker",
            "--loglevel=info", "--concurrency=2", "-Q", "ingestion,celery"
        ], env=worker_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a bit for the worker to initialize
        time.sleep(5)
        
        # Check if the worker is running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            logger.error(f"Failed to start Celery worker: {stderr.decode()}")
            raise RuntimeError("Failed to start Celery worker")
        
        logger.info("Celery worker started successfully")
        return process

    @staticmethod
    def _is_port_in_use(port):
        """Check if a port is in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    @classmethod
    def _create_test_repo(cls):
        """Create a test repository with some files."""
        repo_dir = tempfile.mkdtemp()
        
        # Create sample Python files
        os.makedirs(os.path.join(repo_dir, "src/package"), exist_ok=True)
        
        # Create __init__.py files
        Path(os.path.join(repo_dir, "src/package/__init__.py")).touch()
        
        # Create a module file
        with open(os.path.join(repo_dir, "src/package/module.py"), "w") as f:
            f.write("""
def hello_world():
    \"\"\"Print hello world.
    
    Returns:
        str: A greeting
    \"\"\"
    return "Hello, world!"

class Calculator:
    \"\"\"A simple calculator class.\"\"\"
    
    def add(self, a, b):
        \"\"\"Add two numbers.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            The sum of a and b
        \"\"\"
        return a + b
""")
        
        # Create a README
        with open(os.path.join(repo_dir, "README.md"), "w") as f:
            f.write("""# Test Repository
            
This is a test repository for pipeline integration tests.

## Features

- Module with functions and classes
- Documentation in docstrings
- Simple README
""")
        
        return repo_dir
    
    @classmethod
    def _wait_for_neo4j(cls, connector, max_attempts=30):
        """Wait for Neo4j to be ready."""
        for i in range(max_attempts):
            try:
                # Try a simple query
                connector.execute_query("RETURN 1 AS n")
                return True
            except Exception as e:
                print(f"Waiting for Neo4j (attempt {i+1}/{max_attempts}): {e}")
                time.sleep(1)
        
        raise RuntimeError("Neo4j not ready after maximum wait time")

    def test_full_pipeline_execution(self):
        """Test that the full pipeline executes successfully using the real services."""
        # Start the pipeline job using the real pipeline manager
        job_id = self.pipeline_manager.start_job(repository_path=self.repo_dir)

        logger.info(f"Started pipeline job with ID: {job_id}")

        # Wait for job to complete with a timeout (real services might take longer)
        timeout = 180  # 3 minutes
        start_time = time.time()
        job_status = None

        while time.time() - start_time < timeout:
            job_status = self.pipeline_manager.status(job_id)
            logger.info(f"Job status: {job_status.get('status')}")
            
            if job_status.get('status') in [StepStatus.COMPLETED, StepStatus.FAILED]:
                break
                
            time.sleep(5)  # Check every 5 seconds
        
        self.assertIsNotNone(job_status, "Failed to get job status")
        
        # If the job is still running, the test will fail, which is what we want
        self.assertEqual(job_status.get('status'), StepStatus.COMPLETED, 
                        f"Pipeline job failed or timed out: {job_status}")

        # Verify data in Neo4j
        query = """
        MATCH (n)
        RETURN count(n) as node_count
        """
        result = self.neo4j_connector.execute_query(query)
        self.assertGreater(result[0]["node_count"], 0, "No nodes created in Neo4j")
        
        # Check for specific node types
        query = """
        MATCH (f:File)
        RETURN count(f) as file_count
        """
        result = self.neo4j_connector.execute_query(query)
        self.assertGreater(result[0]["file_count"], 0, "No File nodes created")
        
        # Check for the README file specifically
        query = """
        MATCH (f:File {name: "README.md"})
        RETURN f
        """
        result = self.neo4j_connector.execute_query(query)
        self.assertEqual(len(result), 1, "README.md not found in graph")

    def test_pipeline_with_empty_repo(self):
        """Test the pipeline with an empty repository."""
        # Create an empty repository
        empty_repo_dir = tempfile.mkdtemp()

        try:
            # Start the pipeline job
            job_id = self.pipeline_manager.start_job(repository_path=empty_repo_dir)
            
            # Wait for job to complete with timeout
            timeout = 60  # 1 minute (should be faster for empty repo)
            start_time = time.time()
            job_status = None
            
            while time.time() - start_time < timeout:
                job_status = self.pipeline_manager.status(job_id)
                logger.info(f"Empty repo job status: {job_status.get('status')}")
                
                if job_status.get('status') in [StepStatus.COMPLETED, StepStatus.FAILED]:
                    break
                    
                time.sleep(2)
            
            # For an empty repo, we don't assert overall success since some steps might fail
            # due to having no content to process, but the filesystem step should still succeed
            
            # Verify the filesystem step worked even for an empty repo
            # We check by querying Neo4j directly since the step statuses might be complex
            query = """
            MATCH (r:Repository)
            RETURN count(r) as repo_count
            """
            result = self.neo4j_connector.execute_query(query)
            self.assertGreater(result[0]["repo_count"], 0, "No Repository node created for empty repo")
            
        finally:
            # Clean up
            shutil.rmtree(empty_repo_dir)

    def test_pipeline_error_handling(self):
        """Test that the pipeline handles errors correctly when steps fail."""
        # Use a non-existent repository path to trigger an error
        non_existent_path = "/path/that/does/not/exist"
        
        try:
            # Start the pipeline job
            job_id = self.pipeline_manager.start_job(repository_path=non_existent_path)
            
            # Wait for job to complete with timeout
            timeout = 60  # 1 minute
            start_time = time.time()
            job_status = None
            
            while time.time() - start_time < timeout:
                job_status = self.pipeline_manager.status(job_id)
                logger.info(f"Error handling job status: {job_status.get('status')}")
                
                if job_status.get('status') in [StepStatus.COMPLETED, StepStatus.FAILED]:
                    break
                    
                time.sleep(2)
            
            self.assertIsNotNone(job_status, "Failed to get job status")
            
            # The pipeline should have failed due to the non-existent repository path
            self.assertEqual(job_status.get('status'), StepStatus.FAILED, 
                           "Pipeline should have failed with non-existent repository path")
        except ValueError:
            # It's also acceptable if the pipeline manager refuses to start a job with an invalid path
            pass