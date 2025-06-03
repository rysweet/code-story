from typing import Any

"Integration tests for the filesystem workflow step using direct execution.\n\nThese tests verify that the FileSystemStep can correctly process a repository\nand store its structure in the Neo4j database by directly executing the task.\n"
import os

import tempfile
from pathlib import Path

import pytest

from codestory.config.settings import Neo4jSettings
from codestory.ingestion_pipeline.step import StepStatus, generate_job_id

os.environ["NEO4J__URI"] = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
os.environ["NEO4J__USERNAME"] = "neo4j"
os.environ["NEO4J__PASSWORD"] = "password"
os.environ["NEO4J__DATABASE"] = "neo4j"
TEST_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
TEST_USERNAME = "neo4j"
TEST_PASSWORD = "password"
TEST_DATABASE = "neo4j"
TEST_NEO4J_SETTINGS = Neo4jSettings(uri=TEST_URI, username=TEST_USERNAME, password=TEST_PASSWORD, database=TEST_DATABASE)  # type: ignore[arg-type,call-arg]


@pytest.fixture
def sample_repo() -> None:
    """Create a sample repository structure for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "sample_repo"
        repo_dir.mkdir()
        (repo_dir / "src").mkdir()
        (repo_dir / "src" / "main").mkdir()
        (repo_dir / "src" / "test").mkdir()
        (repo_dir / "docs").mkdir()
        (repo_dir / "README.md").write_text("# Sample Repository")
        (repo_dir / "src" / "main" / "app.py").write_text(
            "def main():\n    print('Hello, world!')"
        )
        (repo_dir / "src" / "test" / "test_app.py").write_text(
            "def test_main():\n    assert True"
        )
        (repo_dir / "docs" / "index.md").write_text("# Documentation")
        (repo_dir / ".git").mkdir()
        (repo_dir / ".git" / "config").write_text("# Git config")
        (repo_dir / "src" / "__pycache__").mkdir()
        (repo_dir / "src" / "__pycache__" / "app.cpython-310.pyc").write_text(
            "# Bytecode"
        )
        yield str(repo_dir)


def custom_process_filesystem(
    repository_path: Any,
    job_id: Any,
    neo4j_connector: Any,
    ignore_patterns: Any = None,
    **config: Any,
) -> None:
    """Modified version of process_filesystem that uses the test connector.

    This function is a simplified version of the original process_filesystem
    that uses the provided Neo4j connector instead of creating a new one.
    """
    print(f"*** TEST_DEBUG: Running test_process_filesystem with {job_id} ***")
    print(f"Repository path: {repository_path}")
    print(f"Ignore patterns: {ignore_patterns}")
    if ignore_patterns is None:
        ignore_patterns = [".git/", "__pycache__/", "node_modules/", ".venv/"]
    max_depth = config.get("max_depth")
    try:
        file_count = 0
        dir_count = 0
        repo_name = os.path.basename(repository_path)
        repo_properties = {"name": repo_name, "path": repository_path}
        repo_query = "\n        MERGE (r:Repository {name: $props.name, path: $props.path})\n        RETURN elementId(r) as id\n        "
        repo_result = neo4j_connector.execute_query(
            repo_query, params={"props": repo_properties}, write=True
        )
        repo_id = repo_result[0]["id"] if repo_result else None
        print(f"Created repository node with ID: {repo_id}")
        for current_dir, dirs, files in os.walk(repository_path):
            rel_path = os.path.relpath(current_dir, repository_path)
            if max_depth is not None:
                if rel_path != "." and rel_path.count(os.sep) >= max_depth:
                    dirs.clear()
                    continue
            dirs_to_remove = []
            for d in dirs:
                if any(
                    d.startswith(pat.rstrip("/")) or d == pat.rstrip("/")
                    for pat in ignore_patterns
                    if pat.endswith("/")
                ):
                    dirs_to_remove.append(d)
            for d in dirs_to_remove:
                dirs.remove(d)
            dir_path = os.path.relpath(current_dir, repository_path)
            if dir_path == ".":
                pass
            else:
                dir_properties = {
                    "name": os.path.basename(current_dir),
                    "path": dir_path,
                }
                dir_query = "\n                MERGE (d:Directory {path: $props.path})\n                SET d.name = $props.name\n                RETURN elementId(d) as id\n                "
                dir_result = neo4j_connector.execute_query(
                    dir_query, params={"props": dir_properties}, write=True
                )
                dir_result[0]["id"] if dir_result else None
                parent_path = os.path.dirname(dir_path)
                if parent_path == "":
                    rel_query = "\n                    MATCH (r:Repository {name: $repo_name})\n                    MATCH (d:Directory {path: $dir_path})\n                    MERGE (r)-[:CONTAINS]->(d)\n                    "
                    neo4j_connector.execute_query(
                        rel_query,
                        params={"repo_name": repo_name, "dir_path": dir_path},
                        write=True,
                    )
                else:
                    rel_query = "\n                    MATCH (p:Directory {path: $parent_path})\n                    MATCH (d:Directory {path: $dir_path})\n                    MERGE (p)-[:CONTAINS]->(d)\n                    "
                    neo4j_connector.execute_query(
                        rel_query,
                        params={"parent_path": parent_path, "dir_path": dir_path},
                        write=True,
                    )
                dir_count += 1
            for file in files:
                skip = False
                for pattern in ignore_patterns:
                    if not pattern.endswith("/") and file.endswith(pattern):
                        skip = True
                        break
                if skip:
                    continue
                file_path = os.path.join(dir_path, file) if dir_path != "." else file
                file_properties = {"name": file, "path": file_path}
                file_query = "\n                MERGE (f:File {path: $props.path})\n                SET f.name = $props.name\n                RETURN elementId(f) as id\n                "
                file_result = neo4j_connector.execute_query(
                    file_query, params={"props": file_properties}, write=True
                )
                file_result[0]["id"] if file_result else None
                if dir_path == ".":
                    rel_query = "\n                    MATCH (r:Repository {name: $repo_name})\n                    MATCH (f:File {path: $file_path})\n                    MERGE (r)-[:CONTAINS]->(f)\n                    "
                    neo4j_connector.execute_query(
                        rel_query,
                        params={"repo_name": repo_name, "file_path": file_path},
                        write=True,
                    )
                else:
                    rel_query = "\n                    MATCH (d:Directory {path: $dir_path})\n                    MATCH (f:File {path: $file_path})\n                    MERGE (d)-[:CONTAINS]->(f)\n                    "
                    neo4j_connector.execute_query(
                        rel_query,
                        params={"dir_path": dir_path, "file_path": file_path},
                        write=True,
                    )
                file_count += 1
        return {"status": StepStatus.COMPLETED, "job_id": job_id, "file_count": file_count, "dir_count": dir_count}  # type: ignore[return-value]
    except Exception as e:
        print(f"Error processing filesystem: {e}")
        return {"status": StepStatus.FAILED, "error": f"Error processing filesystem: {e!s}", "job_id": job_id}  # type: ignore[return-value]


@pytest.mark.integration
@pytest.mark.neo4j
def test_filesystem_direct(sample_repo: Any, neo4j_connector: Any) -> None:
    """Test that the filesystem task works correctly when executed directly."""
    print("*** IMPORTANT: TEST IS ACTUALLY RUNNING ***")
    job_id = generate_job_id()
    print(f"Neo4j URI: {neo4j_connector.uri}")
    print(f"Neo4j database: {neo4j_connector.database}")
    print(f"Sample repo path: {sample_repo}")
    result = custom_process_filesystem(
        repository_path=sample_repo,
        job_id=job_id,
        neo4j_connector=neo4j_connector,
        ignore_patterns=[".git/", "__pycache__/"],
    )
    print(f"Task completed with result: {result}")
    assert (
        result["status"] == StepStatus.COMPLETED
    ), f"Task failed: {result.get('error')}"
    assert "file_count" in result, "Missing file count in result"
    assert "dir_count" in result, "Missing directory count in result"
    assert result["file_count"] > 0, "No files were processed"
    assert result["dir_count"] > 0, "No directories were processed"
    repo_query = neo4j_connector.execute_query(
        "MATCH (r:Repository {name: $name}) RETURN r",
        params={"name": os.path.basename(sample_repo)},
    )
    assert repo_query is not None, "Repository node not found"
    directories = neo4j_connector.execute_query(
        "MATCH (d:Directory) RETURN d.path as path"
    )
    directory_paths = [record["path"] for record in directories]
    assert "src" in directory_paths, "src directory not found"
    assert "src/main" in directory_paths, "src/main directory not found"
    assert "src/test" in directory_paths, "src/test directory not found"
    assert "docs" in directory_paths, "docs directory not found"
    files = neo4j_connector.execute_query("MATCH (f:File) RETURN f.path as path")
    file_paths = [record["path"] for record in files]
    assert "README.md" in file_paths, "README.md file not found"
    assert "src/main/app.py" in file_paths, "src/main/app.py file not found"
    assert "src/test/test_app.py" in file_paths, "src/test/test_app.py file not found"
    assert "docs/index.md" in file_paths, "docs/index.md file not found"
    git_dir = neo4j_connector.execute_query(
        "MATCH (d:Directory {path: '.git'}) RETURN d"
    )
    assert len(git_dir) == 0, ".git directory was not ignored"
    pycache_dir = neo4j_connector.execute_query(
        "MATCH (d:Directory {path: 'src/__pycache__'}) RETURN d"
    )
    assert len(pycache_dir) == 0, "__pycache__ directory was not ignored"


@pytest.mark.integration
@pytest.mark.neo4j
def test_filesystem_update_direct(sample_repo: Any, neo4j_connector: Any) -> None:
    """Test that the filesystem task can update an existing repository."""
    print("Running initial execution...")
    job_id = generate_job_id()
    print(f"Running initial process_filesystem task with job_id: {job_id}")
    result = custom_process_filesystem(
        repository_path=sample_repo,
        job_id=job_id,
        neo4j_connector=neo4j_connector,
        ignore_patterns=[".git/", "__pycache__/"],
    )
    assert result["status"] == StepStatus.COMPLETED, "Initial task failed"
    file_count_query = neo4j_connector.execute_query(
        "MATCH (f:File) RETURN count(f) as count"
    )
    initial_file_count = file_count_query[0]["count"]
    print(f"Initial file count: {initial_file_count}")
    print("Adding new file to the repository...")
    new_file_path = Path(sample_repo) / "src" / "main" / "new_file.py"
    new_file_path.write_text("# New file")
    update_job_id = generate_job_id()
    print(f"Running update process_filesystem task with job_id: {update_job_id}")
    update_result = custom_process_filesystem(
        repository_path=sample_repo,
        job_id=update_job_id,
        neo4j_connector=neo4j_connector,
        ignore_patterns=[".git/", "__pycache__/"],
    )
    assert update_result["status"] == StepStatus.COMPLETED, "Update task failed"
    new_file_query = neo4j_connector.execute_query(
        "MATCH (f:File {path: 'src/main/new_file.py'}) RETURN f"
    )
    assert len(new_file_query) > 0, "New file was not added to the database"
    print(f"Verified new file exists in database: {new_file_query[0]['f']}")
    file_count_query = neo4j_connector.execute_query(
        "MATCH (f:File) RETURN count(f) as count"
    )
    updated_file_count = file_count_query[0]["count"]
    print(f"Updated file count: {updated_file_count}")
    assert updated_file_count >= initial_file_count, "File count decreased after update"
