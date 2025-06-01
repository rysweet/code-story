from typing import Any
'Unit tests for the ProgressClient class.'
from unittest.mock import MagicMock, patch
import redis
from codestory.cli.client.progress_client import ProgressClient

class TestProgressClient:
    """Tests for the ProgressClient class."""

    def test_init(self: Any) -> None:
        """Test ProgressClient initialization."""
        with patch('redis.from_url') as mock_redis_from_url:
            mock_redis_from_url.side_effect = redis.RedisError('Connection failed')
            callback = MagicMock()
            client = ProgressClient(job_id='test-job', callback=callback)
            assert client.use_redis is False
            assert client.redis is None

    def test_redis_connection_success(self: Any) -> None:
        """Test successful Redis connection."""
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        callback = MagicMock()
        with patch('redis.from_url') as mock_redis_from_url:
            mock_redis_from_url.side_effect = [redis.RedisError('Connection failed'), mock_redis_client]
            client = ProgressClient(job_id='test-job', callback=callback)
            assert client.use_redis is True
            assert client.redis is not None

    def test_docker_port_detection(self: Any) -> None:
        """Test Docker port detection for Redis."""
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        callback = MagicMock()
        mock_settings = MagicMock()
        mock_settings.redis = MagicMock()
        mock_settings.redis.uri = 'redis://redis:6379'
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = '0.0.0.0:6389\n'
            mock_run.return_value = mock_result
            with patch('redis.from_url') as mock_redis_from_url:
                mock_redis_from_url.side_effect = [redis.RedisError('Connection failed'), mock_redis_client]
                client = ProgressClient(job_id='test-job', callback=callback, settings=mock_settings)
                mock_run.assert_called_once_with(['docker', 'port', 'codestory-redis', '6379'], capture_output=True, text=True, check=False)
                assert mock_redis_from_url.call_args_list[0][0][0] == 'redis://redis:6379'
                assert mock_redis_from_url.call_args_list[1][0][0] == 'redis://localhost:6389'
                assert client.use_redis is True
                assert client.redis is not None

    def test_use_explicit_redis_url(self: Any) -> None:
        """Test using explicitly provided Redis URL."""
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        callback = MagicMock()
        with patch('redis.from_url') as mock_redis_from_url:
            mock_redis_from_url.return_value = mock_redis_client
            client = ProgressClient(job_id='test-job', callback=callback, redis_url='redis://explicit:1234')
            mock_redis_from_url.assert_called_with('redis://explicit:1234', socket_timeout=2.0)
            assert client.use_redis is True
            assert client.redis is not None

    def test_fallback_to_http_polling(self: Any) -> None:
        """Test fallback to HTTP polling when Redis is not available."""
        callback = MagicMock()
        with patch('redis.from_url') as mock_redis_from_url:
            mock_redis_from_url.side_effect = redis.RedisError('Connection failed')
            client = ProgressClient(job_id='test-job', callback=callback)
            assert client.use_redis is False
            assert client.redis is None
            with patch('threading.Thread') as mock_thread:
                mock_thread_instance = MagicMock()
                mock_thread.return_value = mock_thread_instance
                client.start()
                mock_thread.assert_called_once()
                assert mock_thread.call_args[1]['target'] == client._poll_http
                assert mock_thread_instance.daemon is True
                mock_thread_instance.start.assert_called_once()