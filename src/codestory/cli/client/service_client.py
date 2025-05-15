"""
Service client for interacting with the Code Story service API.
"""

import json
import time
import webbrowser
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import httpx
from pydantic import SecretStr
from rich.console import Console

from codestory.config import Settings, get_settings


class ServiceClient:
    """Client for interacting with the Code Story service API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        console: Optional[Console] = None,
        settings: Optional[Settings] = None,
    ):
        """
        Initialize the service client.

        Args:
            base_url: Service base URL. If not provided, uses settings.
            api_key: API key for authentication. If not provided, uses settings.
            console: Rich console for output. If not provided, creates a new one.
            settings: Settings object. If not provided, loads from configuration.
        """
        self.settings = settings or get_settings()

        # Get host and port from settings, with fallback to default
        try:
            # Default to localhost for CLI usage
            host = getattr(self.settings.service, "host", "localhost")
            
            # Always use localhost for CLI client
            if host == "0.0.0.0":
                host = "localhost"
                
            port = getattr(self.settings.service, "port", 8000)
            # Convert to int in case it's a string or mock
            if not isinstance(port, int):
                port = 8000
        except (AttributeError, ValueError):
            host = "localhost"
            port = 8000

        self.base_url = base_url or f"http://{host}:{port}/v1"
        self.api_key = api_key

        # Try to get API key from settings
        try:
            if not self.api_key and hasattr(self.settings.service, "api_key"):
                api_key_setting = self.settings.service.api_key
                if isinstance(api_key_setting, SecretStr):
                    self.api_key = api_key_setting.get_secret_value()
                else:
                    self.api_key = api_key_setting
        except (AttributeError, ValueError):
            pass

        self.console = console or Console()
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=30.0,
            headers=self._get_headers(),
        )

    def _get_headers(self) -> Dict[str, str]:
        """
        Get headers for API requests.

        Returns:
            Headers dictionary including auth if available.
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    def check_service_health(self) -> Dict[str, Any]:
        """
        Check if the service is healthy.

        Returns:
            Health check response data.
        
        This method attempts to call both the v1 health endpoint (/v1/health) and
        the legacy endpoint (/health). It will try the legacy endpoint first, then
        the v1 endpoint if that fails.
        """
        error_messages = []
        
        # Try legacy endpoint first (/health)
        try:
            response = self.client.get("/health")
            response.raise_for_status()
            health_data = response.json()
            # Check if Celery/Redis status is included
            if "components" not in health_data:
                health_data["components"] = {}
            return health_data
        except httpx.HTTPError as e:
            error_messages.append(f"Legacy health endpoint failed: {str(e)}")
            # Use print instead of debug if not available
            if hasattr(self.console, "debug"):
                self.console.debug(f"Legacy health endpoint failed: {str(e)}")
            else:
                print(f"Legacy health endpoint failed: {str(e)}")
        
        # If that fails, try the v1 endpoint
        try:
            response = self.client.get("/v1/health")
            response.raise_for_status()
            health_data = response.json()
            # Check if Celery/Redis status is included
            if "components" not in health_data:
                health_data["components"] = {}
            return health_data
        except httpx.HTTPError as e:
            error_messages.append(f"V1 health endpoint failed: {str(e)}")
            # Use print instead of debug if not available
            if hasattr(self.console, "debug"):
                self.console.debug(f"V1 health endpoint failed: {str(e)}")
            else:
                print(f"V1 health endpoint failed: {str(e)}")
        
        # Try fallback to raw health check - some installations only return 200 but no valid JSON
        try:
            # Just check if the server is responding at all
            response = self.client.request("GET", "/health")
            if response.status_code == 200:
                self.console.debug("Raw health check succeeded with status code 200 but invalid JSON")
                return {
                    "status": "degraded",
                    "message": "Service is running but returned invalid health check data",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "components": {
                        "celery": {"status": "unknown"},
                        "redis": {"status": "unknown"}
                    }
                }
        except Exception as e:
            error_messages.append(f"Raw health check failed: {str(e)}")
            # Use print instead of debug if not available
            if hasattr(self.console, "debug"):
                self.console.debug(f"Raw health check failed: {str(e)}")
            else:
                print(f"Raw health check failed: {str(e)}")
        
        # If both failed, raise an error with both messages
        raise ServiceError(f"Health check failed: {'; '.join(error_messages)}")

    def start_ingestion(self, repository_path: str) -> Dict[str, Any]:
        """
        Start an ingestion job for the given repository path.

        Args:
            repository_path: Path to the repository to ingest.

        Returns:
            Ingestion job data including job_id.
        """
        data = {
            "repository_path": repository_path,
        }

        try:
            response = self.client.post("/ingest", json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise ServiceError(f"Failed to start ingestion: {str(e)}")

    def get_ingestion_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get the status of an ingestion job.

        Args:
            job_id: ID of the ingestion job.

        Returns:
            Ingestion job status data.
        """
        try:
            response = self.client.get(f"/ingest/{job_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise ServiceError(f"Failed to get ingestion status: {str(e)}")

    def stop_ingestion(self, job_id: str) -> Dict[str, Any]:
        """
        Stop an ingestion job.

        Args:
            job_id: ID of the ingestion job to stop.

        Returns:
            Response data indicating success or failure.
        """
        try:
            response = self.client.post(f"/ingest/{job_id}/stop")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise ServiceError(f"Failed to stop ingestion: {str(e)}")

    def list_ingestion_jobs(self) -> List[Dict[str, Any]]:
        """
        List all ingestion jobs.

        Returns:
            List of ingestion job data.
        """
        try:
            response = self.client.get("/ingest/jobs")
            response.raise_for_status()
            return response.json()["jobs"]
        except httpx.HTTPError as e:
            raise ServiceError(f"Failed to list ingestion jobs: {str(e)}")
        except (KeyError, json.JSONDecodeError) as e:
            raise ServiceError(f"Invalid response format: {str(e)}")

    def execute_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a Cypher query or MCP tool call.

        Args:
            query: Cypher query or MCP tool call string.
            parameters: Optional query parameters.

        Returns:
            Query results.
        """
        data = {
            "query": query,
        }

        if parameters:
            data["parameters"] = parameters

        try:
            response = self.client.post("/query", json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise ServiceError(f"Query execution failed: {str(e)}")

    def ask_question(self, question: str) -> Dict[str, Any]:
        """
        Ask a natural language question about the codebase.

        Args:
            question: Natural language question.

        Returns:
            Answer data.
        """
        data = {
            "question": question,
        }

        try:
            response = self.client.post("/ask", json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise ServiceError(f"Failed to ask question: {str(e)}")

    def get_config(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Get the current configuration.

        Args:
            include_sensitive: Whether to include sensitive values.

        Returns:
            Configuration data.
        """
        params = {}
        if include_sensitive:
            params["include_sensitive"] = "true"

        try:
            response = self.client.get("/config", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise ServiceError(f"Failed to get configuration: {str(e)}")

    def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update configuration values.

        Args:
            updates: Dictionary of configuration keys and values to update.

        Returns:
            Updated configuration data.
        """
        try:
            response = self.client.patch("/config", json=updates)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise ServiceError(f"Failed to update configuration: {str(e)}")

    def start_service(self) -> Dict[str, Any]:
        """
        Start the Code Story service.

        Returns:
            Service status data.
        """
        try:
            response = self.client.post("/service/start")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise ServiceError(f"Failed to start service: {str(e)}")

    def stop_service(self) -> Dict[str, Any]:
        """
        Stop the Code Story service.

        Returns:
            Service status data.
        """
        try:
            response = self.client.post("/service/stop")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise ServiceError(f"Failed to stop service: {str(e)}")

    def get_service_status(self) -> Dict[str, Any]:
        """
        Get the status of the Code Story service.

        Returns:
            Service status data.
        """
        try:
            response = self.client.get("/service/status")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise ServiceError(f"Failed to get service status: {str(e)}")

    def generate_visualization(self, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a graph visualization.

        Args:
            params: Optional parameters for the visualization.
                - type: Type of visualization (force, hierarchy, radial, sankey)
                - theme: Color theme (light, dark, auto)
                - title: Custom title for the visualization

        Returns:
            HTML content for the visualization.
        """
        try:
            # Only include params if they're provided
            if params:
                response = self.client.get(
                    "/visualize", params=params, headers={"Accept": "text/html"}
                )
            else:
                response = self.client.get(
                    "/visualize", headers={"Accept": "text/html"}
                )
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as e:
            raise ServiceError(f"Failed to generate visualization: {str(e)}")

    def open_ui(self) -> None:
        """
        Open the GUI in the default web browser.
        """
        # Get UI URL with fallback
        try:
            ui_url = getattr(self.settings.service, "ui_url", None)
        except (AttributeError, ValueError):
            ui_url = None

        # Use default if not set
        if not ui_url:
            ui_url = "http://localhost:5173"

        webbrowser.open(ui_url)


class ServiceError(Exception):
    """Exception raised for service client errors."""

    pass
