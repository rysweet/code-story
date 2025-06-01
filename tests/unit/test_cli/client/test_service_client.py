from typing import Any

"Unit tests for the ServiceClient class."
import tempfile
from unittest.mock import MagicMock, patch

import httpx
import pytest
from rich.console import Console

from codestory.cli.client.service_client import ServiceClient, ServiceError


class TestServiceClient:
    """Tests for the ServiceClient class."""

    def test_init(self: Any) -> None:
        """Test ServiceClient initialization."""
        client = ServiceClient()
        assert "localhost" in client.base_url
        assert client.api_key is None
        assert isinstance(client.console, Console)

    def test_console_methods(self: Any) -> None:
        """Test that only valid Console methods are used."""
        console = Console()
        client = ServiceClient(console=console)
        with patch("httpx.Client.get") as mock_get:
            mock_get.side_effect = httpx.HTTPError("Test error")
            with pytest.raises(ServiceError):
                client.check_service_health()

    def test_start_ingestion_logging(self: Any) -> None:
        """Test start_ingestion with console logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            console = Console()
            client = ServiceClient(console=console)
            with patch("httpx.Client.post") as mock_post:
                mock_response = MagicMock()
                mock_response.raise_for_status.return_value = None
                mock_response.json.return_value = {"job_id": "test-job"}
                mock_post.return_value = mock_response
                result = client.start_ingestion(temp_dir)
                assert result == {"job_id": "test-job"}

    def test_check_service_health_with_error(self: Any) -> None:
        """Test check_service_health with error and console logging."""
        console = Console()
        client = ServiceClient(console=console)
        with patch("httpx.Client.get") as mock_get:
            mock_get.side_effect = httpx.HTTPError("Test error")
            with pytest.raises(ServiceError):
                client.check_service_health()

    def test_generate_visualization_logging(self: Any) -> None:
        """Test generate_visualization with console logging."""
        console = Console()
        client = ServiceClient(console=console)
        with patch("httpx.Client.get") as mock_get:
            mock_get.side_effect = [
                httpx.HTTPError("First endpoint failed"),
                MagicMock(text="<html>Test Visualization</html>"),
            ]
            mock_get.return_value.raise_for_status.return_value = None
            try:
                client.generate_visualization()
            except ServiceError:
                pass

    def test_list_ingestion_jobs_with_items_field(self: Any) -> None:
        """Test list_ingestion_jobs with 'items' field in response."""
        client = ServiceClient()
        with patch("httpx.Client.get") as mock_get:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {
                "items": [
                    {"job_id": "job1", "status": "running"},
                    {"job_id": "job2", "status": "completed"},
                ],
                "total": 2,
                "limit": 10,
                "offset": 0,
                "has_more": False,
            }
            mock_get.return_value = mock_response
            jobs = client.list_ingestion_jobs()
            assert len(jobs) == 2
            assert jobs[0]["job_id"] == "job1"
            assert jobs[1]["job_id"] == "job2"

    def test_list_ingestion_jobs_with_jobs_field(self: Any) -> None:
        """Test list_ingestion_jobs with 'jobs' field in response (legacy format)."""
        client = ServiceClient()
        with patch("httpx.Client.get") as mock_get:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {
                "jobs": [
                    {"job_id": "job1", "status": "running"},
                    {"job_id": "job2", "status": "completed"},
                ]
            }
            mock_get.return_value = mock_response
            jobs = client.list_ingestion_jobs()
            assert len(jobs) == 2
            assert jobs[0]["job_id"] == "job1"
            assert jobs[1]["job_id"] == "job2"

    def test_list_ingestion_jobs_with_invalid_format(self: Any) -> None:
        """Test list_ingestion_jobs with response lacking both 'items' and 'jobs' fields."""
        client = ServiceClient()
        with patch("httpx.Client.get") as mock_get:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {"status": "success", "data": []}
            mock_get.return_value = mock_response
            with pytest.raises(ServiceError) as excinfo:
                client.list_ingestion_jobs()
            assert "Invalid response format" in str(excinfo.value)
            assert "expected job data structure" in str(excinfo.value)

    def test_list_ingestion_jobs_with_list_format(self: Any) -> None:
        """Test list_ingestion_jobs with direct list response format."""
        client = ServiceClient()
        with patch("httpx.Client.get") as mock_get:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = [
                {"job_id": "job1", "status": "running"},
                {"job_id": "job2", "status": "completed"},
            ]
            mock_get.return_value = mock_response
            jobs = client.list_ingestion_jobs()
            assert len(jobs) == 2
            assert jobs[0]["job_id"] == "job1"
            assert jobs[1]["job_id"] == "job2"

    def test_list_ingestion_jobs_with_single_job_format(self: Any) -> None:
        """Test list_ingestion_jobs with single job response format."""
        client = ServiceClient()
        with patch("httpx.Client.get") as mock_get:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {
                "job_id": "job1",
                "status": "running",
                "progress": 50.0,
            }
            mock_get.return_value = mock_response
            jobs = client.list_ingestion_jobs()
            assert len(jobs) == 1
            assert jobs[0]["job_id"] == "job1"

    def test_list_ingestion_jobs_with_mock_format(self: Any) -> None:
        """Test list_ingestion_jobs with mock service format (job_id='jobs')."""
        console = MagicMock()
        client = ServiceClient(console=console)
        with patch("httpx.Client.get") as mock_get:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {
                "job_id": "jobs",
                "status": "pending",
                "progress": 0.0,
            }
            mock_get.return_value = mock_response
            jobs = client.list_ingestion_jobs()
            assert len(jobs) == 1
            assert jobs[0]["job_id"] == "jobs"
            console.print.assert_called_once()
            assert "Warning" in console.print.call_args[0][0]
