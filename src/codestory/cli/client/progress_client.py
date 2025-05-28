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

    def __init__(
        self,
        job_id: str,
        callback: Callable[[dict[str, Any]], None],
        redis_url: str | None = None,
        console: Console | None = None,
        settings: Settings | None = None,
        poll_interval: float = 1.0,
    ):
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

        # Set up Redis connection with smarter fallback options
        self.console.print("[dim]Setting up Redis connection for progress tracking...[/]")

        # List of possible Redis URLs to try
        redis_urls = []

        # 1. Use explicitly provided URL if given
        if redis_url:
            redis_urls.append(redis_url)

        # 2. Try to get from settings
        if hasattr(self.settings, "redis") and hasattr(self.settings.redis, "uri"):
            settings_url = self.settings.redis.uri
            redis_urls.append(settings_url)

            # 3. Check Docker port mappings if using container hostname
            if "redis://redis:" in settings_url:
                # Try to detect Docker port mapping
                try:
                    import subprocess

                    # Extract internal container port
                    internal_port = settings_url.split(":")[-1].split("/")[0]
                    container_name = "codestory-redis"

                    # Try to get the port mapping from Docker
                    try:
                        # Use docker port command to get the mapping
                        result = subprocess.run(
                            ["docker", "port", container_name, internal_port],
                            capture_output=True,
                            text=True,
                            check=False,
                        )

                        if result.returncode == 0 and result.stdout.strip():
                            # Parse the output to get the mapped port
                            port_mapping = result.stdout.strip()
                            # Format can be either "0.0.0.0:6389" or "127.0.0.1:6389"
                            mapped_port = port_mapping.split(":")[-1]

                            # Add these as highest priority in localhost variants
                            mapped_localhost = f"redis://localhost:{mapped_port}"
                            redis_urls.insert(1, mapped_localhost)
                            redis_urls.insert(2, f"redis://127.0.0.1:{mapped_port}")

                            self.console.print(
                                f"[dim]Detected Docker port mapping: {internal_port} -> "
                                f"{mapped_port}[/]"
                            )
                    except Exception as e:
                        self.console.print(f"[dim]Could not detect Docker port mapping: {e!s}[/]")

                    # Fallback to standard localhost variants if Docker command didn't work
                    localhost_url = settings_url.replace("redis://redis:", "redis://localhost:")
                    redis_urls.append(localhost_url)
                    redis_urls.append(f"redis://127.0.0.1:{internal_port}")
                except Exception:
                    # Fallback to just replacing the hostname
                    localhost_url = settings_url.replace("redis://redis:", "redis://localhost:")
                    redis_urls.append(localhost_url)

                    # Extract port number for additional variants
                    try:
                        port = localhost_url.split(":")[-1].split("/")[0]
                        # Try alternative localhost format
                        redis_urls.append(f"redis://127.0.0.1:{port}")
                    except Exception:
                        pass

        # 4. Add common ports as fallbacks
        # Check both standard port and port used in our docker-compose.yml
        redis_urls.extend(
            [
                "redis://localhost:6379",
                "redis://127.0.0.1:6379",
                "redis://localhost:6389",  # Used in our docker-compose.yml
                "redis://127.0.0.1:6389",
                "redis://localhost:6380",  # Used in test docker-compose
                "redis://127.0.0.1:6380",  # Used in test docker-compose
            ]
        )

        # Remove duplicates while preserving order
        redis_urls = list(dict.fromkeys(redis_urls))

        # Log the URLs we're going to try
        self.console.print(f"[dim]Redis connection URLs to try: {', '.join(redis_urls)}[/]")

        # Try each URL
        connected = False
        for url in redis_urls:
            try:
                self.console.print(f"[dim]Trying Redis connection at {url}...[/]")
                redis_client = redis.from_url(url, socket_timeout=2.0)
                # Test the connection
                redis_client.ping()
                # If we got here, connection successful
                self.redis = redis_client
                self.use_redis = True
                self.channel = f"codestory:ingestion:progress:{job_id}"
                self.console.print(
                    f"[green]Connected to Redis at {url} for real-time progress updates[/]"
                )

                # Save this URL to settings for future use in this session
                if hasattr(self.settings, "redis"):
                    self.settings.redis.uri = url

                connected = True
                break
            except (redis.RedisError, Exception) as e:
                self.console.print(f"[dim]Could not connect to Redis at {url}: {e!s}[/]")

        if not connected:
            self.use_redis = False
            self.redis = None
            self.console.print(
                "[yellow]Warning: Redis not available after trying multiple endpoints, "
                "falling back to polling[/]"
            )

        self._stop_event = threading.Event()
        self._thread = None

    def start(self) -> None:
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

    def stop(self) -> None:
        """Stop tracking progress."""
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=2.0)

    def _subscribe_redis(self) -> None:
        """Subscribe to Redis channel for progress updates."""
        pubsub = self.redis.pubsub()
        pubsub.subscribe(self.channel)

        # Also look for pre-existing job information
        try:
            # Check if there's existing data in Redis for this job
            latest_key = f"codestory:ingestion:latest:{self.job_id}"
            latest_data = self.redis.get(latest_key)
            if latest_data:
                try:
                    data = json.loads(latest_data)
                    self.callback(data)
                except (json.JSONDecodeError, TypeError) as e:
                    self.console.print(f"[yellow]Warning: Could not parse latest job data: {e}[/]")
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not get latest job data: {e}[/]")

        try:
            for message in pubsub.listen():
                if self._stop_event.is_set():
                    break

                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        self.callback(data)

                        # Check if this is a terminal status and break
                        if data.get("status") in ("completed", "failed", "cancelled"):
                            break
                    except (json.JSONDecodeError, TypeError) as e:
                        self.console.print(f"[yellow]Warning: Could not parse job update: {e}[/]")
                elif message["type"] == "heartbeat":
                    # Handle heartbeat messages
                    pass
        finally:
            pubsub.unsubscribe()
            pubsub.close()

    def _poll_http(self) -> None:
        """Poll service API for progress updates when Redis is unavailable."""
        # Import here to avoid circular imports
        from codestory.cli.client.service_client import ServiceClient, ServiceError

        client = ServiceClient(console=self.console, settings=self.settings)

        while not self._stop_event.is_set():
            try:
                # Get job status from service API
                status = client.get_ingestion_status(self.job_id)

                # Transform status to expected format if needed
                steps_data = []
                if "steps" in status:
                    # Already in correct format
                    steps_data = status.get("steps", [])
                elif "current_step" in status:
                    # Convert Celery job format to steps format
                    steps_data = [
                        {
                            "name": status.get("current_step", "Processing"),
                            "status": status.get("status", "running").lower(),
                            "progress": status.get("progress", 0),
                            "message": status.get("message", ""),
                        }
                    ]

                # Update steps in status if needed
                if steps_data and "steps" not in status:
                    status["steps"] = steps_data

                self.callback(status)

                # If job is completed, failed, or cancelled, stop polling
                if status.get("status", "").lower() in (
                    "completed",
                    "failed",
                    "cancelled",
                ):
                    break

            except ServiceError as e:
                self.console.print(f"[yellow]Warning: Failed to get job status: {e}[/]")
                # Don't break the loop on error, keep trying

            time.sleep(self.poll_interval)
