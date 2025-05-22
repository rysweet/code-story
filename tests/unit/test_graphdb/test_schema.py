"""Tests for graph database schema module."""

from unittest.mock import MagicMock, patch

import pytest
from codestory.graphdb.exceptions import SchemaError
from codestory.graphdb.schema import (
    create_custom_vector_index,
    get_all_schema_elements,
    get_schema_initialization_queries,
    get_vector_index_query,
    initialize_schema,
    verify_schema,
)


# Mock Prometheus metrics to prevent registration conflicts
@pytest.fixture(autouse=True)
def mock_prometheus_metrics():
    """Mock prometheus metrics to avoid registration issues during tests."""
    with patch("prometheus_client.Counter") as mock_counter, patch(
        "prometheus_client.Gauge"
    ) as mock_gauge, patch("prometheus_client.Histogram") as mock_histogram, patch(
        "prometheus_client.REGISTRY._names_to_collectors", {}
    ):
        # Configure mocks to avoid attribute errors
        mock_labels = MagicMock()
        mock_counter.return_value.labels = mock_labels
        mock_counter.return_value.labels.return_value.inc = MagicMock()
        mock_gauge.return_value.set = MagicMock()
        mock_histogram.return_value.labels = mock_labels
        mock_histogram.return_value.labels.return_value.observe = MagicMock()

        yield


def test_get_vector_index_query():
    """Test getting vector index query."""
    # Test with default parameters
    query = get_vector_index_query("Test", "embedding")
    assert "CREATE VECTOR INDEX test_embedding_vector_idx" in query
    assert "FOR (n:Test)" in query
    assert "ON (n.embedding)" in query
    assert "`vector.dimensions`: 1536" in query
    assert '`vector.similarity_function`: "cosine"' in query

    # Test with custom parameters
    query = get_vector_index_query(
        "CustomLabel", "vectors", dimensions=768, similarity="euclidean"
    )
    assert "CREATE VECTOR INDEX customlabel_vectors_vector_idx" in query
    assert "FOR (n:CustomLabel)" in query
    assert "ON (n.vectors)" in query
    assert "`vector.dimensions`: 768" in query
    assert '`vector.similarity_function`: "euclidean"' in query


def test_get_all_schema_elements():
    """Test getting all schema elements."""
    schema_elements = get_all_schema_elements()

    # Check structure
    assert "constraints" in schema_elements
    assert "fulltext_indexes" in schema_elements
    assert "property_indexes" in schema_elements
    assert "vector_indexes" in schema_elements

    # Check content types
    assert isinstance(schema_elements["constraints"], list)
    assert isinstance(schema_elements["fulltext_indexes"], list)
    assert isinstance(schema_elements["property_indexes"], list)
    assert isinstance(schema_elements["vector_indexes"], list)

    # Check content
    assert any("File" in c and "path" in c for c in schema_elements["constraints"])
    assert any("Directory" in c and "path" in c for c in schema_elements["constraints"])
    assert any("Class" in c for c in schema_elements["constraints"])

    assert any("file_content" in idx for idx in schema_elements["fulltext_indexes"])
    assert any("code_name" in idx for idx in schema_elements["fulltext_indexes"])

    assert any(
        "file_extension_idx" in idx for idx in schema_elements["property_indexes"]
    )

    assert any(
        "Summary" in idx and "embedding" in idx
        for idx in schema_elements["vector_indexes"]
    )
    assert any(
        "Documentation" in idx and "embedding" in idx
        for idx in schema_elements["vector_indexes"]
    )


def test_get_schema_initialization_queries():
    """Test getting schema initialization queries."""
    queries = get_schema_initialization_queries()

    # Should be a list of strings
    assert isinstance(queries, list)
    assert all(isinstance(q, str) for q in queries)

    # Should include all schema elements
    schema_elements = get_all_schema_elements()
    total_expected = sum(len(items) for items in schema_elements.values())
    assert len(queries) == total_expected


def test_create_custom_vector_index():
    """Test creating a custom vector index."""
    # Create mock connector
    mock_connector = MagicMock()

    # Test successful index creation
    create_custom_vector_index(
        mock_connector, "TestLabel", "embedding", dimensions=1536, similarity="cosine"
    )

    # Check that execute_query was called with the correct query
    mock_connector.execute_query.assert_called_once()
    args, kwargs = mock_connector.execute_query.call_args
    query = args[0]
    assert "CREATE VECTOR INDEX testlabel_embedding_vector_idx" in query
    assert "FOR (n:TestLabel)" in query
    assert kwargs.get("write") is True

    # Test error handling
    mock_connector.execute_query.side_effect = Exception("Test error")

    with pytest.raises(SchemaError) as exc_info:
        create_custom_vector_index(mock_connector, "TestLabel", "embedding")

    assert "Failed to create vector index" in str(exc_info.value)
    assert exc_info.value.details["operation"] == "create_vector_index"
    assert exc_info.value.details["label"] == "TestLabel"
    assert exc_info.value.details["property"] == "embedding"


def test_initialize_schema():
    """Test initializing schema."""
    # Create mock connector
    mock_connector = MagicMock()

    # Test successful schema initialization with simplified schema
    # Patch get_schema_initialization_queries to return a simpler list
    with patch(
        "src.codestory.graphdb.schema.get_schema_initialization_queries"
    ) as mock_get_queries:
        # Simulate the simplified schema we're now using
        mock_get_queries.return_value = [
            "CREATE CONSTRAINT file_path IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE",
            "CREATE CONSTRAINT dir_path IF NOT EXISTS FOR (d:Directory) REQUIRE d.path IS UNIQUE",
            "CREATE INDEX file_extension_idx IF NOT EXISTS FOR (f:File) ON (f.extension)",
        ]
        initialize_schema(mock_connector)

        # Check that execute_query was called for each schema element in our mock
        assert mock_connector.execute_query.call_count == 3

    # Test error handling
    mock_connector.reset_mock()
    mock_connector.execute_query.side_effect = Exception("Test error")

    with pytest.raises(SchemaError) as exc_info:
        # Force=False to keep it simple
        initialize_schema(mock_connector, force=False)

    assert "Failed to initialize schema" in str(exc_info.value)
    assert exc_info.value.details is not None


def test_verify_schema():
    """Test verifying schema."""
    # Create mock connector with mock results
    mock_connector = MagicMock()

    # Mock the execute_query to return some fake constraints and indexes
    mock_connector.execute_query.side_effect = [
        [
            {"name": "constraint_unique_file_path", "type": "UNIQUENESS"},
            {"name": "constraint_unique_dir_path", "type": "UNIQUENESS"},
        ],
        [
            {"name": "file_content", "type": "FULLTEXT"},
            {"name": "code_name", "type": "FULLTEXT"},
            {"name": "summary_embedding_vector_idx", "type": "VECTOR"},
        ],
    ]

    # Test successful schema verification
    results = verify_schema(mock_connector)

    # Check structure of results
    assert "constraints" in results
    assert "indexes" in results
    assert "vector_indexes" in results

    # Check that execute_query was called twice (once for constraints, once for indexes)
    assert mock_connector.execute_query.call_count == 2

    # Test error handling
    mock_connector.execute_query.side_effect = Exception("Test error")

    with pytest.raises(SchemaError) as exc_info:
        verify_schema(mock_connector)

    assert "Failed to verify schema" in str(exc_info.value)
    assert exc_info.value.details["operation"] == "verify_schema"
