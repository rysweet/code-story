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
            redis_url = redis_url or self.settings.redis.uri
            self.redis = redis.from_url(redis_url)
            self.use_redis = True
            self.channel = f"status::{job_id}"
        except (AttributeError, redis.RedisError):
            self.use_redis = False
            self.redis = None
            self.console.print("[yellow]Warning: Redis not available, falling back to polling[/]")
        
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
        
        try:
            for message in pubsub.listen():
                if self._stop_event.is_set():
                    break
                    
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        self.callback(data)
                    except (json.JSONDecodeError, TypeError):
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
                status = client.get_ingestion_status(self.job_id)
                self.callback(status)
                
                # If job is completed, failed, or cancelled, stop polling
                if status.get("status") in ("completed", "failed", "cancelled"):
                    break
                    
            except ServiceError:
                pass
                
            time.sleep(self.poll_interval)