"""
Progress client for tracking ingestion job progress.
"""

import json
import threading
import time
from typing import Any, Callable, Dict, Optional

import redis
from rich.console import Console

from codestory.config import Settings, get_settings


class ProgressClient:
    """Client for tracking ingestion job progress."""

    def __init__(
        self,
        job_id: str,
        callback: Callable[[Dict[str, Any]], None],
        redis_url: Optional[str] = None,
        console: Optional[Console] = None,
        settings: Optional[Settings] = None,
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

        # Set up Redis connection
        try:
            # Get Redis URL from settings with proper localhost connection for CLI
            if redis_url:
                # Use provided URL if given
                pass
            elif hasattr(self.settings, "redis") and hasattr(self.settings.redis, "uri"):
                redis_url = self.settings.redis.uri
                # Convert docker-compose style URLs to localhost for CLI use
                if "redis://redis:" in redis_url:
                    # Map docker service name to localhost with port mapping
                    redis_url = redis_url.replace("redis://redis:", "redis://localhost:")
                    # Standard port mapping in docker-compose.yml is 6379:6379
            else:
                # Default to standard port
                redis_url = "redis://localhost:6379"
                
            self.console.print(f"[dim]Connecting to Redis at {redis_url}[/]")
            self.redis = redis.from_url(redis_url)
            self.use_redis = True
            # Use the standard channel format that matches the service's format
            self.channel = f"codestory:ingestion:progress:{job_id}"
            # Test the connection to ensure it works
            self.redis.ping()
            self.console.print(f"[green]Connected to Redis for real-time progress updates[/]")
        except (AttributeError, redis.RedisError) as e:
            self.use_redis = False
            self.redis = None
            self.console.print(
                f"[yellow]Warning: Redis not available ({str(e)}), falling back to polling[/]"
            )

        self._stop_event = threading.Event()
        self._thread = None

    def start(self) -> None:
        """
        Start tracking progress.
        """
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
        """
        Stop tracking progress.
        """
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=2.0)

    def _subscribe_redis(self) -> None:
        """
        Subscribe to Redis channel for progress updates.
        """
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
        """
        Poll service API for progress updates when Redis is unavailable.
        """
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
                    steps_data = [{
                        "name": status.get("current_step", "Processing"),
                        "status": status.get("status", "running").lower(),
                        "progress": status.get("progress", 0),
                        "message": status.get("message", "")
                    }]
                
                # Update steps in status if needed
                if steps_data and "steps" not in status:
                    status["steps"] = steps_data
                
                self.callback(status)

                # If job is completed, failed, or cancelled, stop polling
                if status.get("status", "").lower() in ("completed", "failed", "cancelled"):
                    break

            except ServiceError as e:
                self.console.print(f"[yellow]Warning: Failed to get job status: {e}[/]")
                # Don't break the loop on error, keep trying

            time.sleep(self.poll_interval)
