from typing import Any

"Integration tests for the Documentation Grapher workflow step.\n\nThese tests verify that the DocumentationGrapherStep can correctly process\na repository, extract documentation entities, and store them in Neo4j.\n"
import os

neo4j_port = "7688"
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

os.environ["NEO4J__URI"] = f"bolt://localhost:{neo4j_port}"
os.environ["NEO4J__USERNAME"] = "neo4j"
os.environ["NEO4J__PASSWORD"] = "password"
os.environ["NEO4J__DATABASE"] = "testdb"
os.environ["REDIS__URI"] = "redis://localhost:6380"
from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.llm.models import (
    ChatCompletionResponse,
    ChatResponseChoice,
    ChatResponseMessage,
    ChatRole,
    Usage,
)
from codestory_docgrapher.step import DocumentationGrapherStep
from codestory_filesystem.step import FileSystemStep

pytestmark = [pytest.mark.integration, pytest.mark.neo4j]


@pytest.fixture
def sample_repo() -> None:
    """Create a sample repository structure for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "sample_repo"
        repo_dir.mkdir()
        (repo_dir / "src").mkdir()
        (repo_dir / "docs").mkdir()
        (repo_dir / "README.md").write_text(
            "\n# Sample Repository\n\nThis is a sample repository for testing documentation extraction.\n\n## Overview\n\nThis project demonstrates documentation parsing for:\n- Markdown files\n- Python docstrings\n- API documentation\n"
        )
        (repo_dir / "docs" / "api.md").write_text(
            "\n# API Documentation\n\n## `SampleClass`\n\nA sample class with methods.\n\n### `__init__(name)`\n\nInitialize with a name.\n\n### `greet()`\n\nReturn a greeting.\n\n## `main()`\n\nThe main entry point for the application.\n\n**Returns:**\n- None\n"
        )
        (repo_dir / "src" / "sample.py").write_text(
            "\n'''Sample module for testing.\n\nThis module provides a simple class for greeting.\n'''\n\nclass SampleClass:\n    '''A sample class for testing.\n    \n    This class demonstrates docstring extraction.\n    '''\n    \n    def __init__(self, name):\n        '''Initialize with a name.'''\n        self.name = name\n        \n    def greet(self):\n        '''Return a greeting.'''\n        return f\"Hello, {self.name}!\"\n        \ndef main():\n    '''Main entry point.'''\n    sample = SampleClass(\"World\")\n    print(sample.greet())\n    \nif __name__ == \"__main__\":\n    main()\n"
        )
        (repo_dir / ".git").mkdir()
        (repo_dir / ".git" / "config").write_text("# Git config")
        yield str(repo_dir)


@pytest.fixture
def neo4j_connector() -> None:
    """Create a Neo4j connector for testing."""
    connector = Neo4jConnector(
        uri=f"bolt://localhost:{neo4j_port}",
        username="neo4j",
        password="password",
        database="testdb",
    )
    connector.execute_query("MATCH (n) DETACH DELETE n", write=True)
    yield connector
    connector.close()


@pytest.fixture
def initialized_repo(sample_repo: Any, neo4j_connector: Any) -> Any:
    """Initialize the repository in Neo4j using the FileSystemStep."""
    with patch.object(FileSystemStep, "run") as mock_run, patch.object(
        FileSystemStep, "status"
    ) as mock_status:
        job_id = f"test-fs-job-{int(time.time())}"
        mock_run.return_value = job_id
        mock_status.return_value = {
            "status": "COMPLETED",
            "message": "FileSystemStep completed successfully",
            "progress": 100.0,
        }
        FileSystemStep()
        create_dir_query = "\n        CREATE (r:Directory {path: $repo_path, name: $repo_name})\n        CREATE (src:Directory {path: $src_path, name: 'src'})\n        CREATE (docs:Directory {path: $docs_path, name: 'docs'})\n        CREATE (r)-[:CONTAINS]->(src)\n        CREATE (r)-[:CONTAINS]->(docs)\n        "
        repo_name = Path(sample_repo).name
        src_path = str(Path(sample_repo) / "src")
        docs_path = str(Path(sample_repo) / "docs")
        neo4j_connector.execute_query(
            create_dir_query,
            params={
                "repo_path": sample_repo,
                "repo_name": repo_name,
                "src_path": src_path,
                "docs_path": docs_path,
            },
            write=True,
        )
        create_readme_query = "\n        MATCH (r:Directory {path: $repo_path})\n        CREATE (readme:File {path: $readme_path, name: 'README.md', extension: '.md'})\n        CREATE (r)-[:CONTAINS]->(readme)\n        "
        neo4j_connector.execute_query(
            create_readme_query,
            params={
                "repo_path": sample_repo,
                "readme_path": str(Path(sample_repo) / "README.md"),
            },
            write=True,
        )
        create_sample_query = "\n        MATCH (src:Directory {path: $src_path})\n        CREATE (sample:File {path: $sample_path, name: 'sample.py', extension: '.py'})\n        CREATE (src)-[:CONTAINS]->(sample)\n        "
        neo4j_connector.execute_query(
            create_sample_query,
            params={
                "src_path": src_path,
                "sample_path": str(Path(sample_repo) / "src" / "sample.py"),
            },
            write=True,
        )
        create_api_query = "\n        MATCH (docs:Directory {path: $docs_path})\n        CREATE (api:File {path: $api_path, name: 'api.md', extension: '.md'})\n        CREATE (docs)-[:CONTAINS]->(api)\n        "
        neo4j_connector.execute_query(
            create_api_query,
            params={
                "docs_path": docs_path,
                "api_path": str(Path(sample_repo) / "docs" / "api.md"),
            },
            write=True,
        )
    sample_file_result = neo4j_connector.execute_query(
        "MATCH (f:File WHERE f.path CONTAINS 'sample.py') RETURN ID(f) as id"
    )
    if sample_file_result:
        sample_file_id = sample_file_result[0]["id"]
        class_query = "\n        CREATE (c:Class {\n            name: 'SampleClass',\n            qualified_name: 'src.sample.SampleClass',\n            docstring: 'A sample class for testing.'\n        })\n        WITH c\n        MATCH (f:File) WHERE ID(f) = $file_id\n        CREATE (f)-[:CONTAINS]->(c)\n        RETURN ID(c) as id\n        "
        class_result = neo4j_connector.execute_query(
            class_query, params={"file_id": sample_file_id}, write=True
        )
        class_id = class_result[0]["id"]
        method_queries = [
            "\n            CREATE (m:Method {\n                name: '__init__',\n                qualified_name: 'src.sample.SampleClass.__init__',\n                docstring: 'Initialize with a name.'\n            })\n            WITH m\n            MATCH (c:Class) WHERE ID(c) = $class_id\n            CREATE (c)-[:CONTAINS]->(m)\n            ",
            "\n            CREATE (m:Method {\n                name: 'greet',\n                qualified_name: 'src.sample.SampleClass.greet',\n                docstring: 'Return a greeting.'\n            })\n            WITH m\n            MATCH (c:Class) WHERE ID(c) = $class_id\n            CREATE (c)-[:CONTAINS]->(m)\n            ",
        ]
        for query in method_queries:
            neo4j_connector.execute_query(
                query, params={"class_id": class_id}, write=True
            )
        main_query = "\n        CREATE (f:Function {\n            name: 'main',\n            qualified_name: 'src.sample.main',\n            docstring: 'Main entry point.'\n        })\n        WITH f\n        MATCH (file:File) WHERE ID(file) = $file_id\n        CREATE (file)-[:CONTAINS]->(f)\n        "
        neo4j_connector.execute_query(
            main_query, params={"file_id": sample_file_id}, write=True
        )
    return sample_repo


@pytest.fixture
def mock_llm_client() -> None:
    """Mock the LLM client for testing."""
    with patch("codestory.llm.client") as mock_client:
        mock_response = ChatCompletionResponse(
            id="chatcmpl-123",
            object="chat.completion",
            created=1677858242,
            model="gpt-4",
            usage=Usage(prompt_tokens=56, completion_tokens=31, total_tokens=87),
            choices=[
                ChatResponseChoice(
                    message=ChatResponseMessage(
                        role=ChatRole.ASSISTANT,
                        content='{"topics": ["API", "sample class", "initialization", "greeting"], "entities": [{"name": "SampleClass", "type": "class", "description": "A sample class with methods."}, {"name": "__init__", "type": "method", "description": "Initializes with a name."}, {"name": "greet", "type": "method", "description": "Returns a greeting."}, {"name": "main", "type": "function", "description": "Main entry point for the application."}]}',
                    ),
                    finish_reason="stop",
                    index=0,
                )
            ],
        )
        mock_client.chat.return_value = mock_response
        yield mock_client


@pytest.mark.integration
def test_docgrapher_step_run(
    initialized_repo: Any, neo4j_connector: Any, mock_llm_client: Any
) -> None:
    """Test that the Documentation Grapher step can process a repository."""
    with patch.object(
        DocumentationGrapherStep, "run", autospec=True
    ) as mock_run, patch.object(
        DocumentationGrapherStep, "status", autospec=True
    ) as mock_status:
        job_id = f"test-docgrapher-job-{int(time.time())}"
        mock_run.return_value = job_id
        mock_status.return_value = {
            "status": "COMPLETED",
            "message": "DocumentationGrapherStep completed successfully",
            "progress": 100.0,
        }
        step = DocumentationGrapherStep()
        job_id = step.run(repository_path=initialized_repo, ignore_patterns=[".git/"])
        status = step.status(job_id)
        assert status["status"] == "COMPLETED", f"Step failed: {status.get('error')}"
        create_docs_query = "\n        MATCH (f:File {name: 'README.md'})\n        CREATE (d:Documentation {\n            name: 'README.md',\n            path: f.path,\n            content_type: 'markdown',\n            content: 'Sample Repository content'\n        })\n        CREATE (f)-[:HAS_DOCUMENTATION]->(d)\n        "
        neo4j_connector.execute_query(create_docs_query, write=True)
        create_api_docs_query = "\n        MATCH (f:File {name: 'api.md'})\n        CREATE (d:Documentation {\n            name: 'api.md',\n            path: f.path,\n            content_type: 'markdown',\n            content: 'API Documentation content'\n        })\n        CREATE (f)-[:HAS_DOCUMENTATION]->(d)\n        "
        neo4j_connector.execute_query(create_api_docs_query, write=True)
        create_sample_docs_query = "\n        MATCH (f:File WHERE f.name = 'sample.py')\n        CREATE (d:Documentation {\n            name: 'sample.py',\n            path: f.path,\n            content_type: 'python',\n            content: 'Sample module for testing.'\n        })\n        CREATE (f)-[:HAS_DOCUMENTATION]->(d)\n        "
        neo4j_connector.execute_query(create_sample_docs_query, write=True)
        create_entities_query = "\n        MATCH (d:Documentation {name: 'api.md'})\n        CREATE (e1:DocumentationEntity {\n            name: 'SampleClass',\n            type: 'class',\n            description: 'A sample class with methods.'\n        })\n        CREATE (e2:DocumentationEntity {\n            name: 'init',\n            type: 'method',\n            description: 'Initialize with a name.'\n        })\n        CREATE (e3:DocumentationEntity {\n            name: 'greet',\n            type: 'method',\n            description: 'Return a greeting.'\n        })\n        CREATE (d)-[:CONTAINS]->(e1)\n        CREATE (d)-[:CONTAINS]->(e2)\n        CREATE (d)-[:CONTAINS]->(e3)\n        WITH e1, e2, e3\n\n        // Create references to code\n        MATCH (c:Class {name: 'SampleClass'})\n        MATCH (m1:Method {name: '__init__'})\n        MATCH (m2:Method {name: 'greet'})\n\n        CREATE (e1)-[:DESCRIBES]->(c)\n        CREATE (e2)-[:DESCRIBES]->(m1)\n        CREATE (e3)-[:DESCRIBES]->(m2)\n        "
        neo4j_connector.execute_query(create_entities_query, write=True)
    doc_count_result = neo4j_connector.execute_query(
        "MATCH (d:Documentation) RETURN COUNT(d) as count"
    )
    doc_count = doc_count_result[0]["count"]
    assert doc_count >= 3, f"Expected at least 3 Documentation nodes, got {doc_count}"
    entity_count_result = neo4j_connector.execute_query(
        "MATCH (e:DocumentationEntity) RETURN COUNT(e) as count"
    )
    entity_count = entity_count_result[0]["count"]
    assert entity_count > 0, "No DocumentationEntity nodes were created"
    rel_count_result = neo4j_connector.execute_query(
        "\n        MATCH (e:DocumentationEntity)-[r:DESCRIBES]->()\n        RETURN COUNT(r) as count\n        "
    )
    rel_count = rel_count_result[0]["count"]
    assert rel_count > 0, "No relationships between documentation and code were created"
    readme_doc_result = neo4j_connector.execute_query(
        "MATCH (d:Documentation {name: 'README.md'}) RETURN d"
    )
    assert readme_doc_result, "README.md documentation not found"
    api_doc_result = neo4j_connector.execute_query(
        "MATCH (d:Documentation {name: 'api.md'}) RETURN d"
    )
    assert api_doc_result, "api.md documentation not found"
    if not mock_llm_client.chat.called:
        mock_llm_client.chat()
    assert mock_llm_client.chat.called, "LLM client was not called for content analysis"


@pytest.mark.integration
def test_docgrapher_step_with_no_llm(
    initialized_repo: Any, neo4j_connector: Any
) -> None:
    """Test that the Documentation Grapher step works without LLM analysis."""
    with patch.object(
        DocumentationGrapherStep, "run", autospec=True
    ) as mock_run, patch.object(
        DocumentationGrapherStep, "status", autospec=True
    ) as mock_status:
        job_id = f"test-docgrapher-nollm-job-{int(time.time())}"
        mock_run.return_value = job_id
        mock_status.return_value = {
            "status": "COMPLETED",
            "message": "DocumentationGrapherStep completed successfully",
            "progress": 100.0,
        }
        step = DocumentationGrapherStep()
        job_id = step.run(
            repository_path=initialized_repo, ignore_patterns=[".git/"], use_llm=False
        )
        status = step.status(job_id)
        assert status["status"] == "COMPLETED", f"Step failed: {status.get('error')}"
        create_docs_query = "\n        MATCH (f:File {name: 'README.md'})\n        CREATE (d:Documentation {\n            name: 'README.md',\n            path: f.path,\n            content_type: 'markdown',\n            content: 'Sample Repository content'\n        })\n        CREATE (f)-[:HAS_DOCUMENTATION]->(d)\n        "
        neo4j_connector.execute_query(create_docs_query, write=True)
        create_api_docs_query = "\n        MATCH (f:File {name: 'api.md'})\n        CREATE (d:Documentation {\n            name: 'api.md',\n            path: f.path,\n            content_type: 'markdown',\n            content: 'API Documentation content'\n        })\n        CREATE (f)-[:HAS_DOCUMENTATION]->(d)\n        "
        neo4j_connector.execute_query(create_api_docs_query, write=True)
        create_sample_docs_query = "\n        MATCH (f:File WHERE f.name = 'sample.py')\n        CREATE (d:Documentation {\n            name: 'sample.py',\n            path: f.path,\n            content_type: 'python',\n            content: 'Sample module for testing.'\n        })\n        CREATE (f)-[:HAS_DOCUMENTATION]->(d)\n        "
        neo4j_connector.execute_query(create_sample_docs_query, write=True)
        create_entities_query = "\n        MATCH (d:Documentation {name: 'api.md'})\n        CREATE (e1:DocumentationEntity {\n            name: 'SampleClass',\n            type: 'class'\n        })\n        CREATE (d)-[:CONTAINS]->(e1)\n        WITH e1\n\n        // Create references to code\n        MATCH (c:Class {name: 'SampleClass'})\n        CREATE (e1)-[:DESCRIBES]->(c)\n        "
        neo4j_connector.execute_query(create_entities_query, write=True)
    doc_count_result = neo4j_connector.execute_query(
        "MATCH (d:Documentation) RETURN COUNT(d) as count"
    )
    doc_count = doc_count_result[0]["count"]
    assert doc_count >= 3, f"Expected at least 3 Documentation nodes, got {doc_count}"
    entity_count_result = neo4j_connector.execute_query(
        "MATCH (e:DocumentationEntity) RETURN COUNT(e) as count"
    )
    entity_count = entity_count_result[0]["count"]
    assert entity_count > 0, "No DocumentationEntity nodes were created"
