"""Unit tests for the ProgressClient class."""

import json
import threading
import time
from unittest.mock import MagicMock, patch

import redis
from rich.console import Console

from codestory.cli.client import ProgressClient


class TestProgressClient:
    """Tests for the ProgressClient class."""

    def test_init_with_redis(self) -> None:
        """Test initialization with Redis available."""
        with patch("codestory.cli.client.progress_client.redis.from_url") as mock_redis:
            # Create mock settings
            mock_settings = MagicMock()
            mock_settings.redis.uri = "redis://localhost:6379"

            # Create mock callback
            callback = MagicMock()

            # Create client
            client = ProgressClient(
                job_id="test-123",
                callback=callback,
                settings=mock_settings,
            )

            # Check properties
            assert client.job_id == "test-123"
            assert client.callback == callback
            assert client.use_redis is True
            assert client.channel == "codestory:ingestion:progress:test-123"

            # Check Redis initialization
            mock_redis.assert_called_once_with(
                "redis://localhost:6379", socket_timeout=2.0
            )

    def test_init_without_redis(self) -> None:
        """Test initialization with Redis unavailable."""
        with patch("codestory.cli.client.progress_client.redis.from_url") as mock_redis:
            # Make Redis initialization fail
            mock_redis.side_effect = redis.RedisError("Connection failed")

            # Create mock settings
            mock_settings = MagicMock()
            mock_settings.redis.uri = "redis://localhost:6379"

            # Create mock console and callback
            console = MagicMock(spec=Console)
            callback = MagicMock()

            # Create client
            client = ProgressClient(
                job_id="test-123",
                callback=callback,
                console=console,
                settings=mock_settings,
            )

            # Check properties
            assert client.job_id == "test-123"
            assert client.callback == callback
            assert client.use_redis is False
            assert client.redis is None

            # Check that console.print was called multiple times
            assert console.print.call_count > 0

            # Check that the first message is about setting up Redis
            assert (
                "Setting up Redis connection" in console.print.call_args_list[0][0][0]
            )

            # Check that the last message is a warning about falling back to polling
            last_call = console.print.call_args_list[-1][0][0]
            assert "Warning" in last_call and "falling back to polling" in last_call

    def test_start_and_stop_redis_mode(self) -> None:
        """Test starting and stopping in Redis mode."""
        # Create mock Redis and PubSub
        mock_redis = MagicMock()
        mock_pubsub = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub

        with patch(
            "codestory.cli.client.progress_client.redis.from_url",
            return_value=mock_redis,
        ):
            with patch(
                "codestory.cli.client.progress_client.threading.Thread"
            ) as mock_thread_class:
                # Create mock thread
                mock_thread = MagicMock()
                mock_thread_class.return_value = mock_thread

                # Create mock settings
                mock_settings = MagicMock()
                mock_settings.redis.uri = "redis://localhost:6379"

                # Create client
                client = ProgressClient(
                    job_id="test-123",
                    callback=MagicMock(),
                    settings=mock_settings,
                )

                # Start tracking
                client.start()

                # Check thread creation and start
                mock_thread_class.assert_called_once_with(
                    target=client._subscribe_redis
                )
                mock_thread.start.assert_called_once()

                # Stop tracking
                with patch.object(client._stop_event, "set") as mock_set:
                    client.stop()
                    mock_set.assert_called_once()
                    mock_thread.join.assert_called_once()

    def test_subscribe_redis(self) -> None:
        """Test Redis subscription."""
        # Create mock Redis and PubSub
        mock_redis = MagicMock()
        mock_pubsub = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub

        # Configure pubsub.listen to yield two messages then exit
        message1 = {"type": "message", "data": json.dumps({"progress": 50})}
        message2 = {"type": "message", "data": "invalid json"}
        message3 = {"type": "other", "data": "ignore"}
        mock_pubsub.listen.return_value = [message1, message2, message3]

        with patch(
            "codestory.cli.client.progress_client.redis.from_url",
            return_value=mock_redis,
        ):
            # Create mock settings and callback
            mock_settings = MagicMock()
            mock_settings.redis.uri = "redis://localhost:6379"
            mock_callback = MagicMock()

            # Create client
            client = ProgressClient(
                job_id="test-123",
                callback=mock_callback,
                settings=mock_settings,
            )

            # Set stop event after processing messages
            original_set = client._stop_event.set

            def stop_after_messages():
                # Stop after processing all messages
                time.sleep(0.1)
                original_set()

            stop_thread = threading.Thread(target=stop_after_messages)
            stop_thread.daemon = True
            stop_thread.start()

            # Run subscribe method
            client._subscribe_redis()

            # Check pubsub usage
            mock_pubsub.subscribe.assert_called_once_with(
                "codestory:ingestion:progress:test-123"
            )
            mock_pubsub.unsubscribe.assert_called_once()
            mock_pubsub.close.assert_called_once()

            # Check callback invocation
            mock_callback.assert_called_once_with({"progress": 50})

    def test_poll_http(self) -> None:
        """Test HTTP polling."""
        with patch(
            "codestory.cli.client.service_client.ServiceClient"
        ) as mock_client_class:
            # Create mock client
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Configure get_ingestion_status to return different states
            status_responses = [
                {"status": "running", "progress": 50},
                {"status": "running", "progress": 75},
                {"status": "completed", "progress": 100},
            ]
            mock_client.get_ingestion_status.side_effect = status_responses

            # Create mock settings and callback
            mock_settings = MagicMock()
            # Ensure redis.uri is a string not a MagicMock
            mock_settings.redis.uri = "redis://localhost:6379"
            mock_callback = MagicMock()
            mock_callback.side_effect = [True, True, False]  # Stop after third call

            # Create client with very short poll interval and patch redis connection
            with patch(
                "codestory.cli.client.progress_client.redis.from_url"
            ) as mock_redis_from_url:
                # Make redis fail so we fall back to HTTP polling
                mock_redis_from_url.side_effect = redis.RedisError("Connection failed")

                client = ProgressClient(
                    job_id="test-123",
                    callback=mock_callback,
                    settings=mock_settings,
                    poll_interval=0.01,  # Use short interval for test
                )

            # Run poll method (will exit when callback returns False)
            client._poll_http()

            # Check client usage
            assert mock_client.get_ingestion_status.call_count == 3
            for call in mock_client.get_ingestion_status.call_args_list:
                assert call[0][0] == "test-123"

            # Check callback invocations
            assert mock_callback.call_count == 3
            mock_callback.assert_any_call({"status": "running", "progress": 50})
            mock_callback.assert_any_call({"status": "running", "progress": 75})
            mock_callback.assert_any_call({"status": "completed", "progress": 100})
