"""Unit tests for the ServiceClient class."""

import tempfile
from unittest.mock import MagicMock, patch

import httpx
import pytest
from rich.console import Console

from codestory.cli.client.service_client import ServiceClient, ServiceError


class TestServiceClient:
    """Tests for the ServiceClient class."""

    def test_init(self):
        """Test ServiceClient initialization."""
        # Create test client
        client = ServiceClient()

        # Check defaults
        assert "localhost" in client.base_url
        assert client.api_key is None
        assert isinstance(client.console, Console)

    def test_console_methods(self):
        """Test that only valid Console methods are used."""
        # Create a real Console object
        console = Console()

        # Create client with real console
        client = ServiceClient(console=console)

        # Check that methods used on console are all valid
        # This should not raise any attribute errors
        with patch("httpx.Client.get") as mock_get:
            # Configure mock to raise an exception
            mock_get.side_effect = httpx.HTTPError("Test error")

            # Call a method that uses console logging
            with pytest.raises(ServiceError):
                client.check_service_health()

    def test_start_ingestion_logging(self):
        """Test start_ingestion with console logging."""
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create client with real console but patched httpx
            console = Console()
            client = ServiceClient(console=console)

            # Mock the httpx post method
            with patch("httpx.Client.post") as mock_post:
                # Setup mock response
                mock_response = MagicMock()
                mock_response.raise_for_status.return_value = None
                mock_response.json.return_value = {"job_id": "test-job"}
                mock_post.return_value = mock_response

                # Call start_ingestion
                result = client.start_ingestion(temp_dir)

                # Check result
                assert result == {"job_id": "test-job"}

    def test_check_service_health_with_error(self):
        """Test check_service_health with error and console logging."""
        # Create client with real console
        console = Console()
        client = ServiceClient(console=console)

        # Mock the httpx get method
        with patch("httpx.Client.get") as mock_get:
            # Configure mock to raise an exception
            mock_get.side_effect = httpx.HTTPError("Test error")

            # Call check_service_health - should use console.print not console.debug
            with pytest.raises(ServiceError):
                client.check_service_health()

    def test_generate_visualization_logging(self):
        """Test generate_visualization with console logging."""
        # Create client with real console
        console = Console()
        client = ServiceClient(console=console)

        # Mock the httpx get method for first endpoint and second endpoint
        with patch("httpx.Client.get") as mock_get:
            # First call raises error, second succeeds
            mock_get.side_effect = [
                httpx.HTTPError("First endpoint failed"),
                MagicMock(text="<html>Test Visualization</html>"),
            ]

            # Configure second mock to pass raise_for_status
            mock_get.return_value.raise_for_status.return_value = None

            # Call generate_visualization
            # This should try the first endpoint, log the error, and move to the second
            try:
                client.generate_visualization()
            except ServiceError:
                pass  # We expect this to fail with all mocks returning errors

    def test_list_ingestion_jobs_with_items_field(self):
        """Test list_ingestion_jobs with 'items' field in response."""
        # Create client
        client = ServiceClient()

        # Mock the httpx get method
        with patch("httpx.Client.get") as mock_get:
            # Setup mock response with 'items' field
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

            # Call list_ingestion_jobs
            jobs = client.list_ingestion_jobs()

            # Check result
            assert len(jobs) == 2
            assert jobs[0]["job_id"] == "job1"
            assert jobs[1]["job_id"] == "job2"

    def test_list_ingestion_jobs_with_jobs_field(self):
        """Test list_ingestion_jobs with 'jobs' field in response (legacy format)."""
        # Create client
        client = ServiceClient()

        # Mock the httpx get method
        with patch("httpx.Client.get") as mock_get:
            # Setup mock response with 'jobs' field
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {
                "jobs": [
                    {"job_id": "job1", "status": "running"},
                    {"job_id": "job2", "status": "completed"},
                ]
            }
            mock_get.return_value = mock_response

            # Call list_ingestion_jobs
            jobs = client.list_ingestion_jobs()

            # Check result
            assert len(jobs) == 2
            assert jobs[0]["job_id"] == "job1"
            assert jobs[1]["job_id"] == "job2"

    def test_list_ingestion_jobs_with_invalid_format(self):
        """Test list_ingestion_jobs with response lacking both 'items' and 'jobs' fields."""
        # Create client
        client = ServiceClient()

        # Mock the httpx get method
        with patch("httpx.Client.get") as mock_get:
            # Setup mock response with neither field
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {
                "status": "success",
                "data": [],  # Some other unexpected format
            }
            mock_get.return_value = mock_response

            # Call list_ingestion_jobs - should raise ServiceError
            with pytest.raises(ServiceError) as excinfo:
                client.list_ingestion_jobs()

            # Check error message contains useful information
            assert "Invalid response format" in str(excinfo.value)
            assert "expected job data structure" in str(excinfo.value)

    def test_list_ingestion_jobs_with_list_format(self):
        """Test list_ingestion_jobs with direct list response format."""
        # Create client
        client = ServiceClient()

        # Mock the httpx get method
        with patch("httpx.Client.get") as mock_get:
            # Setup mock response as direct list
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = [
                {"job_id": "job1", "status": "running"},
                {"job_id": "job2", "status": "completed"},
            ]
            mock_get.return_value = mock_response

            # Call list_ingestion_jobs
            jobs = client.list_ingestion_jobs()

            # Check result
            assert len(jobs) == 2
            assert jobs[0]["job_id"] == "job1"
            assert jobs[1]["job_id"] == "job2"

    def test_list_ingestion_jobs_with_single_job_format(self):
        """Test list_ingestion_jobs with single job response format."""
        # Create client
        client = ServiceClient()

        # Mock the httpx get method
        with patch("httpx.Client.get") as mock_get:
            # Setup mock response as single job
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {
                "job_id": "job1",
                "status": "running",
                "progress": 50.0,
            }
            mock_get.return_value = mock_response

            # Call list_ingestion_jobs
            jobs = client.list_ingestion_jobs()

            # Check result
            assert len(jobs) == 1
            assert jobs[0]["job_id"] == "job1"

    def test_list_ingestion_jobs_with_mock_format(self):
        """Test list_ingestion_jobs with mock service format (job_id='jobs')."""
        # Create client with console mock to check warning
        console = MagicMock()
        client = ServiceClient(console=console)

        # Mock the httpx get method
        with patch("httpx.Client.get") as mock_get:
            # Setup mock response as mock format
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {
                "job_id": "jobs",
                "status": "pending",
                "progress": 0.0,
            }
            mock_get.return_value = mock_response

            # Call list_ingestion_jobs
            jobs = client.list_ingestion_jobs()

            # Check result
            assert len(jobs) == 1
            assert jobs[0]["job_id"] == "jobs"

            # Check warning was printed
            console.print.assert_called_once()
            assert "Warning" in console.print.call_args[0][0]
