"""Progress client for tracking ingestion job progress."""
import json
import threading
import time
from collections.abc import Callable
from typing import Any

import redis
from rich.console import Console

from codestory.config import Settings, get_settings


class ProgressClient:
    """Client for tracking ingestion job progress."""

    def __init__(self: Any, job_id: str, callback: Callable[[dict[str, Any]], None], redis_url: str | None=None, console: Console | None=None, settings: Settings | None=None, poll_interval: float=1.0) -> None:
        """
        Initialize the progress client.

        Args:
            job_id: ID of the job to track.
            callback: Function to call with progress updates.
            redis_url: Redis URL. If not provided, uses settings.
            console: Rich console for output. If not provided, creates a new one.
            settings: Settings object. If not provided, loads from configuration.
            poll_interval: Polling interval in seconds for fallback mode.
        """
        self.job_id = job_id
        self.callback = callback
        self.settings = settings or get_settings()
        self.console = console or Console()
        self.poll_interval = poll_interval
        self.console.print('[dim]Setting up Redis connection for progress tracking...[/]')
        redis_urls: list[Any] = []
        if redis_url:
            redis_urls.append(redis_url)
        if hasattr(self.settings, 'redis') and hasattr(self.settings.redis, 'uri'):
            settings_url = self.settings.redis.uri
            redis_urls.append(settings_url)
            if 'redis://redis:' in settings_url:
                try:
                    import subprocess
                    internal_port = settings_url.split(':')[-1].split('/')[0]
                    container_name = 'codestory-redis'
                    try:
                        result = subprocess.run(['docker', 'port', container_name, internal_port], capture_output=True, text=True, check=False)
                        if result.returncode == 0 and result.stdout.strip():
                            port_mapping = result.stdout.strip()
                            mapped_port = port_mapping.split(':')[-1]
                            mapped_localhost = f'redis://localhost:{mapped_port}'
                            redis_urls.insert(1, mapped_localhost)
                            redis_urls.insert(2, f'redis://127.0.0.1:{mapped_port}')
                            self.console.print(f'[dim]Detected Docker port mapping: {internal_port} -> {mapped_port}[/]')
                    except Exception as e:
                        self.console.print(f'[dim]Could not detect Docker port mapping: {e!s}[/]')
                    localhost_url = settings_url.replace('redis://redis:', 'redis://localhost:')
                    redis_urls.append(localhost_url)
                    redis_urls.append(f'redis://127.0.0.1:{internal_port}')
                except Exception:
                    localhost_url = settings_url.replace('redis://redis:', 'redis://localhost:')
                    redis_urls.append(localhost_url)
                    try:
                        port = localhost_url.split(':')[-1].split('/')[0]
                        redis_urls.append(f'redis://127.0.0.1:{port}')
                    except Exception:
                        pass
        redis_urls.extend(['redis://localhost:6379', 'redis://127.0.0.1:6379', 'redis://localhost:6389', 'redis://127.0.0.1:6389', 'redis://localhost:6380', 'redis://127.0.0.1:6380'])
        redis_urls = list(dict.fromkeys(redis_urls))
        self.console.print(f"[dim]Redis connection URLs to try: {', '.join(redis_urls)}[/]")
        connected = False
        for url in redis_urls:
            try:
                self.console.print(f'[dim]Trying Redis connection at {url}...[/]')
                redis_client = redis.from_url(url, socket_timeout=2.0)
                redis_client.ping()
                self.redis = redis_client
                self.use_redis = True
                self.channel = f'codestory:ingestion:progress:{job_id}'
                self.console.print(f'[green]Connected to Redis at {url} for real-time progress updates[/]')
                if hasattr(self.settings, 'redis'):
                    self.settings.redis.uri = url
                connected = True
                break
            except (redis.RedisError, Exception) as e:
                self.console.print(f'[dim]Could not connect to Redis at {url}: {e!s}[/]')
        if not connected:
            self.use_redis = False
            self.redis = None
            self.console.print('[yellow]Warning: Redis not available after trying multiple endpoints, falling back to polling[/]')
        self._stop_event = threading.Event()
        self._thread = None

    def start(self: Any) -> None:
        """Start tracking progress."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        if self.use_redis:
            self._thread = threading.Thread(target=self._subscribe_redis)
        else:
            self._thread = threading.Thread(target=self._poll_http)
        self._thread.daemon = True
        self._thread.start()

    def stop(self: Any) -> None:
        """Stop tracking progress."""
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=2.0)

    def _subscribe_redis(self: Any) -> None:
        """Subscribe to Redis channel for progress updates."""
        pubsub = self.redis.pubsub()
        pubsub.subscribe(self.channel)
        try:
            latest_key = f'codestory:ingestion:latest:{self.job_id}'
            latest_data = self.redis.get(latest_key)
            if latest_data:
                try:
                    data = json.loads(latest_data)
                    self.callback(data)
                except (json.JSONDecodeError, TypeError) as e:
                    self.console.print(f'[yellow]Warning: Could not parse latest job data: {e}[/]')
        except Exception as e:
            self.console.print(f'[yellow]Warning: Could not get latest job data: {e}[/]')
        try:
            for message in pubsub.listen():
                if self._stop_event.is_set():
                    break
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        self.callback(data)
                        if data.get('status') in ('completed', 'failed', 'cancelled'):
                            break
                    except (json.JSONDecodeError, TypeError) as e:
                        self.console.print(f'[yellow]Warning: Could not parse job update: {e}[/]')
                elif message['type'] == 'heartbeat':
                    pass
        finally:
            pubsub.unsubscribe()
            pubsub.close()

    def _poll_http(self: Any) -> None:
        """Poll service API for progress updates when Redis is unavailable."""
        from codestory.cli.client.service_client import ServiceClient, ServiceError
        client = ServiceClient(console=self.console, settings=self.settings)
        while not self._stop_event.is_set():
            try:
                status = client.get_ingestion_status(self.job_id)
                steps_data: list[Any] = []
                if 'steps' in status:
                    steps_data = status.get('steps', [])
                elif 'current_step' in status:
                    steps_data = [{'name': status.get('current_step', 'Processing'), 'status': status.get('status', 'running').lower(), 'progress': status.get('progress', 0), 'message': status.get('message', '')}]
                if steps_data and 'steps' not in status:
                    status['steps'] = steps_data
                self.callback(status)
                if status.get('status', '').lower() in ('completed', 'failed', 'cancelled'):
                    break
            except ServiceError as e:
                self.console.print(f'[yellow]Warning: Failed to get job status: {e}[/]')
            time.sleep(self.poll_interval)