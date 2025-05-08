"""
Unit tests for Neo4jConnector methods (mocked driver).
"""
import pytest
from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.graphdb.exceptions import Neo4jConnectionError, QueryError
from unittest.mock import patch, MagicMock

@pytest.fixture
def connector():
    return Neo4jConnector(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="testpassword"
    )

def test_check_connection_success(connector):
    with patch.object(connector._driver, "session") as mock_session:
        mock_session.return_value.__enter__.return_value.run.return_value = None
        assert connector.check_connection() is True

def test_check_connection_failure(connector):
    with patch.object(connector._driver, "session", side_effect=Exception()):
        assert connector.check_connection() is False

def test_execute_query_success(connector):
    mock_result = [MagicMock(data=lambda: {"foo": "bar"})]
    with patch.object(connector._driver, "session") as mock_session:
        mock_session.return_value.__enter__.return_value.run.return_value = mock_result
        result = connector.execute_query("RETURN 1")
        assert result == [{"foo": "bar"}]

def test_execute_query_failure(connector):
    with patch.object(connector._driver, "session", side_effect=Exception("fail")):
        with pytest.raises(QueryError):
            connector.execute_query("RETURN 1")
