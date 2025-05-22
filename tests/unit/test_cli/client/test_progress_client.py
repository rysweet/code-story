"""Unit tests for the ProgressClient class."""

from unittest.mock import MagicMock, patch

import redis

from codestory.cli.client.progress_client import ProgressClient


class TestProgressClient:
    """Tests for the ProgressClient class."""

    def test_init(self):
        """Test ProgressClient initialization."""
        # Create test client with mocked redis
        with patch("redis.from_url") as mock_redis_from_url:
            # Configure mock to fail for all URLs
            mock_redis_from_url.side_effect = redis.RedisError("Connection failed")

            # Create a callback
            callback = MagicMock()

            # Initialize client
            client = ProgressClient(
                job_id="test-job",
                callback=callback,
            )

            # Check defaults
            assert client.use_redis is False
            assert client.redis is None

    def test_redis_connection_success(self):
        """Test successful Redis connection."""
        # Create mock redis client
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True

        # Create a callback
        callback = MagicMock()

        # Mock redis.from_url to return a successful connection
        with patch("redis.from_url") as mock_redis_from_url:
            # First URL fails, second succeeds
            mock_redis_from_url.side_effect = [
                redis.RedisError("Connection failed"),
                mock_redis_client,
            ]

            # Initialize client
            client = ProgressClient(
                job_id="test-job",
                callback=callback,
            )

            # Check connection status
            assert client.use_redis is True
            assert client.redis is not None

    def test_docker_port_detection(self):
        """Test Docker port detection for Redis."""
        # Create mock redis client
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True

        # Create a callback
        callback = MagicMock()

        # Set up mock settings with Redis URL using container name
        mock_settings = MagicMock()
        mock_settings.redis = MagicMock()
        mock_settings.redis.uri = "redis://redis:6379"

        # Mock docker port command
        with patch("subprocess.run") as mock_run:
            # Configure docker port command to return mapped port
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "0.0.0.0:6389\n"
            mock_run.return_value = mock_result

            # Mock redis.from_url to fail for the first URL and succeed for the mapped one
            with patch("redis.from_url") as mock_redis_from_url:
                # Original URL fails, mapped URL succeeds
                mock_redis_from_url.side_effect = [
                    redis.RedisError("Connection failed"),  # Original URI
                    mock_redis_client,  # Mapped localhost:6389
                ]

                # Initialize client
                client = ProgressClient(
                    job_id="test-job",
                    callback=callback,
                    settings=mock_settings,
                )

                # Verify docker port command was called correctly
                mock_run.assert_called_once_with(
                    ["docker", "port", "codestory-redis", "6379"],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                # Check that mapped URLs were tried
                assert (
                    mock_redis_from_url.call_args_list[0][0][0] == "redis://redis:6379"
                )
                assert (
                    mock_redis_from_url.call_args_list[1][0][0]
                    == "redis://localhost:6389"
                )

                # Check connection status
                assert client.use_redis is True
                assert client.redis is not None

    def test_use_explicit_redis_url(self):
        """Test using explicitly provided Redis URL."""
        # Create mock redis client
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True

        # Create a callback
        callback = MagicMock()

        # Mock redis.from_url to return a successful connection
        with patch("redis.from_url") as mock_redis_from_url:
            mock_redis_from_url.return_value = mock_redis_client

            # Initialize client with explicit URL
            client = ProgressClient(
                job_id="test-job",
                callback=callback,
                redis_url="redis://explicit:1234",
            )

            # Check that explicit URL was tried first
            mock_redis_from_url.assert_called_with(
                "redis://explicit:1234", socket_timeout=2.0
            )

            # Check connection status
            assert client.use_redis is True
            assert client.redis is not None

    def test_fallback_to_http_polling(self):
        """Test fallback to HTTP polling when Redis is not available."""
        # Create a callback
        callback = MagicMock()

        # Mock redis.from_url to fail for all URLs
        with patch("redis.from_url") as mock_redis_from_url:
            mock_redis_from_url.side_effect = redis.RedisError("Connection failed")

            # Initialize client
            client = ProgressClient(
                job_id="test-job",
                callback=callback,
            )

            # Check connection status
            assert client.use_redis is False
            assert client.redis is None

            # Mock threading.Thread to avoid actual thread creation
            with patch("threading.Thread") as mock_thread:
                # Configure mock thread
                mock_thread_instance = MagicMock()
                mock_thread.return_value = mock_thread_instance

                # Start tracking progress
                client.start()

                # Check thread was created with correct target function
                mock_thread.assert_called_once()
                assert mock_thread.call_args[1]["target"] == client._poll_http

                # Check daemon flag was set on the thread instance
                assert mock_thread_instance.daemon is True

                # Check thread was started
                mock_thread_instance.start.assert_called_once()
