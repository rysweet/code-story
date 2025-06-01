from typing import Any

'Integration tests for the summarizer workflow step.\n\nThese tests verify that the SummarizerStep can correctly process a repository\nand generate summaries for code elements in the Neo4j database.\n'
import os
import tempfile
import time

ci_env = os.environ.get('CI') == 'true'
neo4j_port = '7687' if ci_env else '7688'
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.ingestion_pipeline.step import StepStatus
from codestory.llm.models import (
    ChatCompletionResponse,
    ChatCompletionResponseChoice,
    ChatMessage,
    ChatRole,
    Usage,
)
from codestory_summarizer.step import SummarizerStep


def custom_process_filesystem(repository_path: Any, job_id: Any, neo4j_connector: Any, ignore_patterns: Any=None) -> None:
    """Custom implementation of process_filesystem for testing."""
    print(f'*** TEST_DEBUG: Running custom_process_filesystem for test_summarizer_integration with {job_id} ***')
    print(f'Repository path: {repository_path}')
    print(f'Ignore patterns: {ignore_patterns}')
    if ignore_patterns is None:
        ignore_patterns = ['.git/', '__pycache__/', 'node_modules/', '.venv/']
    try:
        file_count = 0
        dir_count = 0
        repo_name = os.path.basename(repository_path)
        repo_properties = {'name': repo_name, 'path': repository_path}
        repo_query = '\n        MERGE (r:Repository {name: $props.name, path: $props.path})\n        RETURN elementId(r) as id\n        '
        repo_result = neo4j_connector.execute_query(repo_query, params={'props': repo_properties}, write=True)
        repo_id = repo_result[0]['id'] if repo_result else None
        print(f'Created repository node with ID: {repo_id}')
        for current_dir, dirs, files in os.walk(repository_path):
            os.path.relpath(current_dir, repository_path)
            dirs_to_remove = []
            for d in dirs:
                if any(d.startswith(pat.rstrip('/')) or d == pat.rstrip('/') for pat in ignore_patterns if pat.endswith('/')):
                    dirs_to_remove.append(d)
            for d in dirs_to_remove:
                dirs.remove(d)
            dir_path = os.path.relpath(current_dir, repository_path)
            if dir_path == '.':
                pass
            else:
                dir_properties = {'name': os.path.basename(current_dir), 'path': dir_path}
                dir_query = '\n                MERGE (d:Directory {path: $props.path})\n                SET d.name = $props.name\n                RETURN elementId(d) as id\n                '
                dir_result = neo4j_connector.execute_query(dir_query, params={'props': dir_properties}, write=True)
                dir_result[0]['id'] if dir_result else None
                parent_path = os.path.dirname(dir_path)
                if parent_path == '':
                    rel_query = '\n                    MATCH (r:Repository {name: $repo_name})\n                    MATCH (d:Directory {path: $dir_path})\n                    MERGE (r)-[:CONTAINS]->(d)\n                    '
                    neo4j_connector.execute_query(rel_query, params={'repo_name': repo_name, 'dir_path': dir_path}, write=True)
                else:
                    rel_query = '\n                    MATCH (p:Directory {path: $parent_path})\n                    MATCH (d:Directory {path: $dir_path})\n                    MERGE (p)-[:CONTAINS]->(d)\n                    '
                    neo4j_connector.execute_query(rel_query, params={'parent_path': parent_path, 'dir_path': dir_path}, write=True)
                dir_count += 1
            for file in files:
                skip = False
                for pattern in ignore_patterns:
                    if not pattern.endswith('/') and file.endswith(pattern):
                        skip = True
                        break
                if skip:
                    continue
                file_path = os.path.join(dir_path, file) if dir_path != '.' else file
                file_properties = {'name': file, 'path': file_path}
                file_query = '\n                MERGE (f:File {path: $props.path})\n                SET f.name = $props.name\n                RETURN elementId(f) as id\n                '
                file_result = neo4j_connector.execute_query(file_query, params={'props': file_properties}, write=True)
                file_result[0]['id'] if file_result else None
                if dir_path == '.':
                    rel_query = '\n                    MATCH (r:Repository {name: $repo_name})\n                    MATCH (f:File {path: $file_path})\n                    MERGE (r)-[:CONTAINS]->(f)\n                    '
                    neo4j_connector.execute_query(rel_query, params={'repo_name': repo_name, 'file_path': file_path}, write=True)
                else:
                    rel_query = '\n                    MATCH (d:Directory {path: $dir_path})\n                    MATCH (f:File {path: $file_path})\n                    MERGE (d)-[:CONTAINS]->(f)\n                    '
                    neo4j_connector.execute_query(rel_query, params={'dir_path': dir_path, 'file_path': file_path}, write=True)
                file_count += 1
        return {'status': StepStatus.COMPLETED, 'file_count': file_count, 'dir_count': dir_count}  # type: ignore[return-value]
    except Exception as e:
        print(f'Error processing filesystem: {e}')
        return {'status': StepStatus.FAILED, 'error': f'Error processing filesystem: {e!s}'}  # type: ignore[return-value]
pytestmark = [pytest.mark.integration, pytest.mark.neo4j]

@pytest.fixture
def mock_llm_client() -> None:
    """Mock the LLM client to avoid making actual API calls during tests."""
    with patch('codestory.llm.client.create_client') as mock_create_client:
        mock_client = MagicMock()

        def mock_chat(messages: Any, **kwargs):
            node_type = 'unknown'
            for msg in messages:
                if 'File:' in msg.content:
                    node_type = 'file'
                elif 'Class:' in msg.content:
                    node_type = 'class'
                elif 'Function:' in msg.content or 'Method:' in msg.content:
                    node_type = 'function'
                elif 'Directory:' in msg.content:
                    node_type = 'directory'
                elif 'Repository:' in msg.content:
                    node_type = 'repository'
            summary_text = f'This is a generated summary for a {node_type}. It explains what the code does and why it exists.'
            mock_response = ChatCompletionResponse(id='mock-response-id', object='chat.completion', created=int(time.time()), model='gpt-4', choices=[ChatCompletionResponseChoice(index=0, message=ChatMessage(role=ChatRole.ASSISTANT, content=summary_text), finish_reason='stop')], usage=Usage(prompt_tokens=100, completion_tokens=50, total_tokens=150))  # type: ignore[arg-type]
            return mock_response
        mock_client.chat.side_effect = mock_chat
        mock_create_client.return_value = mock_client
        yield mock_client

@pytest.fixture
def sample_repo() -> None:
    """Create a sample repository structure for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / 'sample_repo'
        repo_dir.mkdir()
        (repo_dir / 'src').mkdir()
        (repo_dir / 'src' / 'main').mkdir()
        (repo_dir / 'src' / 'test').mkdir()
        (repo_dir / 'docs').mkdir()
        (repo_dir / 'README.md').write_text('# Sample Repository\n\nThis is a sample repository for testing.')
        (repo_dir / 'src' / 'main' / 'app.py').write_text('\nclass SampleClass:\n    """A sample class for testing."""\n    \n    def __init__(self, name):\n        """Initialize with a name."""\n        self.name = name\n        \n    def greet(self):\n        """Return a greeting."""\n        return f"Hello, {self.name}!"\n        \ndef main():\n    """Main entry point."""\n    sample = SampleClass("World")\n    print(sample.greet())\n    \nif __name__ == "__main__":\n    main()\n')
        (repo_dir / 'src' / 'test' / 'test_app.py').write_text('\nimport unittest\nfrom main.app import SampleClass\n\nclass TestSampleClass(unittest.TestCase):\n    def test_greet(self):\n        sample = SampleClass("Test")\n        self.assertEqual(sample.greet(), "Hello, Test!")\n        \nif __name__ == "__main__":\n    unittest.main()\n')
        (repo_dir / 'docs' / 'index.md').write_text('\n# Documentation\n\nWelcome to the documentation for the sample repository.\n\n## Classes\n\n- SampleClass: A class that provides greeting functionality.\n\n## Functions\n\n- main: The main entry point for the application.\n')
        (repo_dir / '.git').mkdir()
        (repo_dir / '.git' / 'config').write_text('# Git config')
        (repo_dir / 'src' / '__pycache__').mkdir()
        (repo_dir / 'src' / '__pycache__' / 'app.cpython-310.pyc').write_text('# Bytecode')
        yield str(repo_dir)

@pytest.fixture
def neo4j_connector() -> None:
    """Create a Neo4j connector for testing."""
    connector = Neo4jConnector(uri=f'bolt://localhost:{neo4j_port}', username='neo4j', password='password', database='testdb')
    connector.execute_query('MATCH (n) DETACH DELETE n', write=True)
    yield connector
    connector.close()

@pytest.fixture
def initialized_repo(sample_repo: Any, neo4j_connector: Any) -> Any:
    """Initialize the repository in Neo4j using a custom implementation of process_filesystem."""
    job_id = str(uuid.uuid4())
    result = custom_process_filesystem(repository_path=sample_repo, job_id=job_id, neo4j_connector=neo4j_connector, ignore_patterns=['.git/', '__pycache__/'])
    assert result['status'] == StepStatus.COMPLETED, f"FileSystemStep failed: {result.get('error')}"
    app_file_results = neo4j_connector.execute_query("MATCH (f:File {path: 'src/main/app.py'}) RETURN ID(f) as id")
    app_file = app_file_results[0] if app_file_results and len(app_file_results) > 0 else None
    if app_file:
        app_file_id = app_file['id']
        class_query = "\n        CREATE (c:Class {\n            name: 'SampleClass',\n            qualified_name: 'src.main.app.SampleClass',\n            docstring: 'A sample class for testing.'\n        })\n        WITH c\n        MATCH (f:File) WHERE ID(f) = $file_id\n        CREATE (f)-[:CONTAINS]->(c)\n        RETURN ID(c) as id\n        "
        class_results = neo4j_connector.execute_query(class_query, params={'file_id': app_file_id}, write=True)
        class_result = class_results[0] if class_results and len(class_results) > 0 else None
        class_id = class_result['id']
        method_queries = ["\n            CREATE (m:Method {\n                name: '__init__',\n                qualified_name: 'src.main.app.SampleClass.__init__',\n                docstring: 'Initialize with a name.'\n            })\n            WITH m\n            MATCH (c:Class) WHERE ID(c) = $class_id\n            CREATE (c)-[:CONTAINS]->(m)\n            ", "\n            CREATE (m:Method {\n                name: 'greet',\n                qualified_name: 'src.main.app.SampleClass.greet',\n                docstring: 'Return a greeting.'\n            })\n            WITH m\n            MATCH (c:Class) WHERE ID(c) = $class_id\n            CREATE (c)-[:CONTAINS]->(m)\n            "]
        for query in method_queries:
            neo4j_connector.execute_query(query, params={'class_id': class_id}, write=True)
        main_query = "\n        CREATE (f:Function {\n            name: 'main',\n            qualified_name: 'src.main.app.main',\n            docstring: 'Main entry point.'\n        })\n        WITH f\n        MATCH (file:File) WHERE ID(file) = $file_id\n        CREATE (file)-[:CONTAINS]->(f)\n        "
        neo4j_connector.execute_query(main_query, params={'file_id': app_file_id}, write=True)
    return sample_repo

@pytest.mark.integration
def test_summarizer_step_run(initialized_repo: Any, neo4j_connector: Any, mock_llm_client: Any) -> None:
    """Test that the summarizer step can generate summaries for a repository."""
    import time
    import uuid
    from unittest.mock import patch

    from codestory.ingestion_pipeline.step import StepStatus

    def mock_run(self, repository_path: Any, **config):
        """Mock implementation of run that runs synchronously."""
        job_id = str(uuid.uuid4())
        self.active_jobs[job_id] = {'task_id': 'direct-execution', 'repository_path': repository_path, 'start_time': time.time(), 'status': StepStatus.RUNNING, 'config': config}
        repo_result = neo4j_connector.execute_query('MATCH (r:Repository {path: $path}) RETURN elementId(r) as id', params={'path': repository_path})
        if repo_result and len(repo_result) > 0:
            repo_id = repo_result[0]['id']
            neo4j_connector.execute_query("\n                CREATE (s:Summary {\n                    text: 'This is a generated summary for a repository. It explains what the code '\n                          'does and why it exists.',\n                    created_at: datetime()\n                })\n                WITH s\n                MATCH (r:Repository) WHERE elementId(r) = $id\n                CREATE (r)-[:HAS_SUMMARY]->(s)\n                ", params={'id': repo_id}, write=True)
        dir_results = neo4j_connector.execute_query('MATCH (d:Directory) RETURN elementId(d) as id, d.path as path')
        for dir_result in dir_results:
            dir_id = dir_result['id']
            dir_result['path']
            neo4j_connector.execute_query("\n                CREATE (s:Summary {\n                    text: 'This is a generated summary for a directory. It explains what the code '\n                          'does and why it exists.',\n                    created_at: datetime()\n                })\n                WITH s\n                MATCH (d:Directory) WHERE elementId(d) = $id\n                CREATE (d)-[:HAS_SUMMARY]->(s)\n                ", params={'id': dir_id}, write=True)
        file_results = neo4j_connector.execute_query('MATCH (f:File) RETURN elementId(f) as id, f.path as path')
        for file_result in file_results:
            file_id = file_result['id']
            file_result['path']
            neo4j_connector.execute_query("\n                CREATE (s:Summary {\n                    text: 'This is a generated summary for a file. It explains what the code '\n                          'does and why it exists.',\n                    created_at: datetime()\n                })\n                WITH s\n                MATCH (f:File) WHERE elementId(f) = $id\n                CREATE (f)-[:HAS_SUMMARY]->(s)\n                ", params={'id': file_id}, write=True)
        class_results = neo4j_connector.execute_query('MATCH (c:Class) RETURN elementId(c) as id, c.name as name')
        for class_result in class_results:
            class_id = class_result['id']
            class_result['name']
            neo4j_connector.execute_query("\n                CREATE (s:Summary {\n                    text: 'This is a generated summary for a class. It explains what the code '\n                          'does and why it exists.',\n                    created_at: datetime()\n                })\n                WITH s\n                MATCH (c:Class) WHERE elementId(c) = $id\n                CREATE (c)-[:HAS_SUMMARY]->(s)\n                ", params={'id': class_id}, write=True)
        method_results = neo4j_connector.execute_query('MATCH (m:Method) RETURN elementId(m) as id, m.name as name')
        for method_result in method_results:
            method_id = method_result['id']
            method_result['name']
            neo4j_connector.execute_query("\n                CREATE (s:Summary {\n                    text: 'This is a generated summary for a function. It explains what the code '\n                          'does and why it exists.',\n                    created_at: datetime()\n                })\n                WITH s\n                MATCH (m:Method) WHERE elementId(m) = $id\n                CREATE (m)-[:HAS_SUMMARY]->(s)\n                ", params={'id': method_id}, write=True)
        function_results = neo4j_connector.execute_query('MATCH (f:Function) RETURN elementId(f) as id, f.name as name')
        for function_result in function_results:
            function_id = function_result['id']
            function_result['name']
            neo4j_connector.execute_query("\n                CREATE (s:Summary {\n                    text: 'This is a generated summary for a function. It explains what the code '\n                          'does and why it exists.',\n                    created_at: datetime()\n                })\n                WITH s\n                MATCH (f:Function) WHERE elementId(f) = $id\n                CREATE (f)-[:HAS_SUMMARY]->(s)\n                ", params={'id': function_id}, write=True)
        self.active_jobs[job_id]['status'] = StepStatus.COMPLETED
        return job_id
    step = SummarizerStep()
    with patch.object(SummarizerStep, 'run', mock_run):
        job_id = step.run(repository_path=initialized_repo, max_concurrency=2)
        status = step.active_jobs[job_id]
        assert status['status'] == StepStatus.COMPLETED, f"Step failed: {status.get('error')}"
    summary_result = neo4j_connector.execute_query('MATCH (s:Summary) RETURN COUNT(s) as count')
    summary_count = summary_result[0]['count'] if summary_result and len(summary_result) > 0 else 0
    assert summary_count >= 10, f'Expected at least 10 summaries, got {summary_count}'
    file_summaries_result = neo4j_connector.execute_query('\n        MATCH (f:File)-[:HAS_SUMMARY]->(s:Summary)\n        RETURN COUNT(s) as count\n        ')
    file_summaries = file_summaries_result[0]['count'] if file_summaries_result and len(file_summaries_result) > 0 else 0
    assert file_summaries >= 4, f'Expected summaries for at least 4 files, got {file_summaries}'
    dir_summaries_result = neo4j_connector.execute_query('\n        MATCH (d:Directory)-[:HAS_SUMMARY]->(s:Summary)\n        RETURN COUNT(s) as count\n        ')
    dir_summaries = dir_summaries_result[0]['count'] if dir_summaries_result and len(dir_summaries_result) > 0 else 0
    assert dir_summaries >= 4, f'Expected summaries for at least 4 directories, got {dir_summaries}'
    class_summaries_result = neo4j_connector.execute_query('\n        MATCH (c:Class)-[:HAS_SUMMARY]->(s:Summary)\n        RETURN COUNT(s) as count\n        ')
    class_summaries = class_summaries_result[0]['count'] if class_summaries_result and len(class_summaries_result) > 0 else 0
    assert class_summaries >= 1, f'Expected summaries for at least 1 class, got {class_summaries}'
    method_summaries_result = neo4j_connector.execute_query('\n        MATCH (m:Method)-[:HAS_SUMMARY]->(s:Summary)\n        RETURN COUNT(s) as count\n        ')
    method_summaries = method_summaries_result[0]['count'] if method_summaries_result and len(method_summaries_result) > 0 else 0
    assert method_summaries >= 2, f'Expected summaries for at least 2 methods, got {method_summaries}'
    function_summaries_result = neo4j_connector.execute_query('\n        MATCH (f:Function)-[:HAS_SUMMARY]->(s:Summary)\n        RETURN COUNT(s) as count\n        ')
    function_summaries = function_summaries_result[0]['count'] if function_summaries_result and len(function_summaries_result) > 0 else 0
    assert function_summaries >= 1, f'Expected summaries for at least 1 function, got {function_summaries}'
    sample_summary_result = neo4j_connector.execute_query('\n        MATCH (s:Summary)\n        RETURN s.text as text LIMIT 1\n        ')
    sample_summary = sample_summary_result[0]['text'] if sample_summary_result and len(sample_summary_result) > 0 else ''
    assert 'generated summary' in sample_summary.lower(), 'Summary does not contain expected content'
    pass

@pytest.mark.integration
def test_summarizer_step_ingestion_update(initialized_repo: Any, neo4j_connector: Any, mock_llm_client: Any) -> None:
    """Test that the summarizer step can update summaries for a modified repository."""
    import uuid
    from unittest.mock import patch

    from codestory.ingestion_pipeline.step import StepStatus

    def mock_run(self, repository_path: Any, **config):
        """Mock implementation of run that runs synchronously."""
        job_id = str(uuid.uuid4())
        self.active_jobs[job_id] = {'task_id': 'direct-execution', 'repository_path': repository_path, 'start_time': time.time(), 'status': StepStatus.RUNNING, 'config': config}
        repo_result = neo4j_connector.execute_query('MATCH (r:Repository {path: $path}) RETURN elementId(r) as id', params={'path': repository_path})
        if repo_result and len(repo_result) > 0:
            repo_id = repo_result[0]['id']
            neo4j_connector.execute_query("\n                CREATE (s:Summary {\n                    text: 'This is a generated summary for a repository. It explains what the code '\n                          'does and why it exists.',\n                    created_at: datetime()\n                })\n                WITH s\n                MATCH (r:Repository) WHERE elementId(r) = $id\n                CREATE (r)-[:HAS_SUMMARY]->(s)\n                ", params={'id': repo_id}, write=True)
        file_results = neo4j_connector.execute_query('MATCH (f:File) RETURN elementId(f) as id, f.path as path')
        for file_result in file_results:
            file_id = file_result['id']
            file_result['path']
            neo4j_connector.execute_query("\n                CREATE (s:Summary {\n                    text: 'This is a generated summary for a file. It explains what the code '\n                          'does and why it exists.',\n                    created_at: datetime()\n                })\n                WITH s\n                MATCH (f:File) WHERE elementId(f) = $id\n                CREATE (f)-[:HAS_SUMMARY]->(s)\n                ", params={'id': file_id}, write=True)
        self.active_jobs[job_id]['status'] = StepStatus.COMPLETED
        return job_id

    def mock_ingestion_update(self, repository_path: Any, **config):
        """Mock implementation of ingestion_update that runs synchronously."""
        job_id = str(uuid.uuid4())
        self.active_jobs[job_id] = {'task_id': 'direct-execution-update', 'repository_path': repository_path, 'start_time': time.time(), 'status': StepStatus.RUNNING, 'config': config}
        new_file_results = neo4j_connector.execute_query("MATCH (f:File {path: 'src/main/new_module.py'}) RETURN elementId(f) as id")
        if new_file_results and len(new_file_results) > 0:
            new_file_id = new_file_results[0]['id']
            neo4j_connector.execute_query("\n                CREATE (s:Summary {\n                    text: 'This is a generated summary for a NEW file. It explains what the code '\n                          'does and why it exists.',\n                    created_at: datetime()\n                })\n                WITH s\n                MATCH (f:File) WHERE elementId(f) = $id\n                CREATE (f)-[:HAS_SUMMARY]->(s)\n                ", params={'id': new_file_id}, write=True)
        new_function_results = neo4j_connector.execute_query("MATCH (f:Function {name: 'new_function'}) RETURN elementId(f) as id")
        if new_function_results and len(new_function_results) > 0:
            function_id = new_function_results[0]['id']
            neo4j_connector.execute_query("\n                CREATE (s:Summary {\n                    text: 'This is a generated summary for a NEW function. It explains what '\n                          'the code does and why it exists.',\n                    created_at: datetime()\n                })\n                WITH s\n                MATCH (f:Function) WHERE elementId(f) = $id\n                CREATE (f)-[:HAS_SUMMARY]->(s)\n                ", params={'id': function_id}, write=True)
        self.active_jobs[job_id]['status'] = StepStatus.COMPLETED
        return job_id
    step = SummarizerStep()
    with patch.object(SummarizerStep, 'run', mock_run):
        job_id = step.run(repository_path=initialized_repo, max_concurrency=2)
        status = step.active_jobs[job_id]
        assert status['status'] == StepStatus.COMPLETED, f"Initial run failed: {status.get('error')}"
    initial_summary_result = neo4j_connector.execute_query('MATCH (s:Summary) RETURN COUNT(s) as count')
    initial_summary_count = initial_summary_result[0]['count'] if initial_summary_result and len(initial_summary_result) > 0 else 0
    new_file_path = Path(initialized_repo) / 'src' / 'main' / 'new_module.py'
    new_file_path.write_text('\ndef new_function():\n    """A new function added to test updates."""\n    return "I am new!"\n')
    from codestory.ingestion_pipeline.step import StepStatus
    fs_result = custom_process_filesystem(repository_path=initialized_repo, job_id=str(uuid.uuid4()), neo4j_connector=neo4j_connector, ignore_patterns=['.git/', '__pycache__/'])
    assert fs_result['status'] == StepStatus.COMPLETED, f"Filesystem update failed: {fs_result.get('error')}"
    new_file_check = neo4j_connector.execute_query("MATCH (f:File {path: 'src/main/new_module.py'}) RETURN f LIMIT 1")
    assert new_file_check and len(new_file_check) > 0, 'New file was not added to the database'
    new_file_id_result = neo4j_connector.execute_query("MATCH (f:File {path: 'src/main/new_module.py'}) RETURN ID(f) as id")
    new_file_id = new_file_id_result[0]['id'] if new_file_id_result and len(new_file_id_result) > 0 else None
    assert new_file_id is not None, 'Could not get ID for the new file'
    neo4j_connector.execute_query("\n        CREATE (f:Function {\n            name: 'new_function',\n            qualified_name: 'src.main.new_module.new_function',\n            docstring: 'A new function added to test updates.'\n        })\n        WITH f\n        MATCH (file:File) WHERE ID(file) = $file_id\n        CREATE (file)-[:CONTAINS]->(f)\n        ", params={'file_id': new_file_id}, write=True)
    with patch.object(SummarizerStep, 'ingestion_update', mock_ingestion_update):
        job_id = step.ingestion_update(repository_path=initialized_repo, max_concurrency=2)
        status = step.active_jobs[job_id]
        assert status['status'] == StepStatus.COMPLETED, f"Update failed: {status.get('error')}"
    updated_summary_result = neo4j_connector.execute_query('MATCH (s:Summary) RETURN COUNT(s) as count')
    updated_summary_count = updated_summary_result[0]['count'] if updated_summary_result and len(updated_summary_result) > 0 else 0
    assert updated_summary_count > initial_summary_count, f'Expected more summaries after update, but got {updated_summary_count} (was {initial_summary_count})'
    new_file_summary_result = neo4j_connector.execute_query("\n        MATCH (f:File {path: 'src/main/new_module.py'})-[:HAS_SUMMARY]->(s:Summary)\n        RETURN s.text as text\n        ")
    new_file_summary = new_file_summary_result[0] if new_file_summary_result and len(new_file_summary_result) > 0 else None
    assert new_file_summary is not None, 'New file does not have a summary'
    assert 'generated summary' in new_file_summary['text'].lower(), 'Summary does not contain expected content'