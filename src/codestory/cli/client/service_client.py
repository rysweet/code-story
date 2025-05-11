"""
Service client for interacting with the Code Story service API.
"""

import json
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

        # Get port from settings, with fallback to default port
        try:
            port = getattr(self.settings.service, "port", 8000)
            # Convert to int in case it's a string or mock
            if not isinstance(port, int):
                port = 8000
        except (AttributeError, ValueError):
            port = 8000

        self.base_url = base_url or f"http://localhost:{port}/v1"
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
        """
        try:
            response = self.client.get("/health")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise ServiceError(f"Health check failed: {str(e)}")

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

    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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

    def generate_visualization(self) -> str:
        """
        Generate a graph visualization.

        Returns:
            HTML content for the visualization.
        """
        try:
            response = self.client.get("/visualize", headers={"Accept": "text/html"})
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