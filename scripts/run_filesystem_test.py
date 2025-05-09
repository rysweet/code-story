#!/usr/bin/env python
"""
Script to directly run the filesystem integration test.
"""

import os
import sys
import tempfile
import time
from pathlib import Path

# Add project root to Python path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)

from codestory.config.settings import get_settings
from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.ingestion_pipeline.step import StepStatus
from codestory_filesystem.step import FileSystemStep


def run_test():
    """Run the filesystem step test directly."""
    print("Starting filesystem step test...")
    
    # Create a sample repository
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a simple directory structure
        repo_dir = Path(temp_dir) / "sample_repo"
        repo_dir.mkdir()
        
        # Create some directories
        (repo_dir / "src").mkdir()
        (repo_dir / "src" / "main").mkdir()
        (repo_dir / "src" / "test").mkdir()
        (repo_dir / "docs").mkdir()
        
        # Create some files
        (repo_dir / "README.md").write_text("# Sample Repository")
        (repo_dir / "src" / "main" / "app.py").write_text("def main():\n    print('Hello, world!')")
        (repo_dir / "src" / "test" / "test_app.py").write_text(
            "def test_main():\n    assert True"
        )
        (repo_dir / "docs" / "index.md").write_text("# Documentation")
        
        # Add some files that should be ignored
        (repo_dir / ".git").mkdir()
        (repo_dir / ".git" / "config").write_text("# Git config")
        (repo_dir / "src" / "__pycache__").mkdir()
        (repo_dir / "src" / "__pycache__" / "app.cpython-310.pyc").write_text("# Bytecode")
        
        sample_repo = str(repo_dir)
        print(f"Created sample repository at: {sample_repo}")
        
        # Connect to Neo4j
        try:
            # Use direct connection parameters to connect to the test Neo4j instance
            neo4j_connector = Neo4jConnector(
                uri="bolt://localhost:7688",  # Port defined in docker-compose.test.yml
                username="neo4j",
                password="password",
                database="codestory-test",  # Database defined in docker-compose.test.yml
            )
            
            # Clear the database before each test - this is a WRITE operation
            try:
                neo4j_connector.execute_query("MATCH (n) DETACH DELETE n", write=True)
                print("Successfully connected to Neo4j and cleared the database")
            except Exception as e:
                print(f"Failed to connect to Neo4j: {str(e)}")
                return
                
            # Create the step
            step = FileSystemStep()
            print(f"Step created")
            
            # Print configuration for debugging
            print(f"Neo4j URI: {neo4j_connector.uri}")
            print(f"Neo4j database: {neo4j_connector.database}")
            print(f"Sample repo path: {sample_repo}")
            
            # Check if Celery worker is running and get detailed information
            from celery.app.control import Control
            from codestory.ingestion_pipeline.celery_app import app
            control = Control(app)
            
            # Try to get worker info with various methods
            print("Checking Celery worker status...")
            try:
                response = control.ping(timeout=2.0)
                print(f"Celery workers ping: {response}")
                
                # Check registered tasks
                i = app.control.inspect()
                print(f"Registered tasks: {i.registered()}")
                print(f"Active queues: {i.active_queues()}")
                print(f"Active tasks: {i.active()}")
                print(f"Reserved tasks: {i.reserved()}")
                print(f"Scheduled tasks: {i.scheduled()}")
                
                # Check if our specific task is registered
                all_tasks = []
                registered = i.registered() or {}
                for worker, tasks in registered.items():
                    all_tasks.extend(tasks)
                
                task_name = "filesystem.run"
                if task_name in all_tasks:
                    print(f"✅ Task '{task_name}' is registered!")
                else:
                    print(f"❌ Task '{task_name}' is NOT registered. Available tasks: {all_tasks}")
            except Exception as e:
                print(f"Error inspecting Celery: {e}")
            
            print("*** END DEBUG ***\n")
            
            # Run the step
            try:
                # First, let's try importing and running the task directly without the step
                # This helps us debug if the issue is with the task registration or the step
                print("Trying to import process_filesystem task directly...")
                from codestory_filesystem.step import process_filesystem
                print(f"Task imported: {process_filesystem}")
                
                # Verify task is registered with Celery
                print(f"Task registered with app? {process_filesystem.name in app.tasks}")
                
                # Now run the step through the regular interface
                print("Running the FileSystemStep.run method...")
                job_id = step.run(
                    repository_path=sample_repo,
                    ignore_patterns=[".git/", "__pycache__/"]
                )
                print(f"Got job_id: {job_id}")
                
            except Exception as e:
                print(f"Error running step: {e}")
                import traceback
                traceback.print_exc()
                raise
            
            # Wait for the step to complete (poll for status)
            max_wait_time = 90  # Much longer timeout for task completion
            start_time = time.time()
            status = {"status": StepStatus.RUNNING}
            
            print("\n*** POLLING STATUS ***")
            print(f"Waiting for job {job_id} to complete (timeout: {max_wait_time}s)...")
            
            # Poll more frequently and for longer to give the task time to complete
            poll_count = 0
            poll_interval = 2  # Poll every 2 seconds
            
            while time.time() - start_time < max_wait_time:
                poll_count += 1
                try:
                    print(f"\nPoll {poll_count}:")
                    status = step.status(job_id)
                    print(f"Job status: {status['status']} - {status.get('message', '')}")
                    
                    if status["status"] in (StepStatus.COMPLETED, StepStatus.FAILED):
                        print(f"Job reached terminal state: {status['status']}")
                        break
                        
                except Exception as e:
                    print(f"Error checking status: {e}")
                
                # Sleep between polls
                time.sleep(poll_interval)
            
            print("\n*** TEST SUMMARY ***")
            print(f"Final status: {status}")
            
            # Final checks for repository data in Neo4j
            print("\n*** CHECKING NEO4J DATA ***")
            repo_name = os.path.basename(sample_repo)
            repo_query = neo4j_connector.execute_query(
                "MATCH (r:Repository {name: $name}) RETURN r",
                params={"name": repo_name}
            )
            if repo_query:
                print(f"✅ Repository node found in Neo4j: {repo_query}")
            else:
                print("❌ Repository node not found in Neo4j")
                
            # Close Neo4j connection
            neo4j_connector.close()
            
        except Exception as e:
            print(f"Test failed with error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    run_test()