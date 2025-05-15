"""
Service client for interacting with the Code Story service API.
"""

import json
import os
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
        """
        # Try multiple health check endpoints in sequence
        # This is necessary because during service startup, one endpoint might
        # be available before the other
        try:
            # First try the standard v1 health endpoint
            try:
                response = self.client.get("/v1/health")
                response.raise_for_status()
                health_data = response.json()
                # Check if components are included
                if "components" not in health_data:
                    health_data["components"] = {}
                return health_data
            except httpx.HTTPError:
                # Fall back to root health endpoint
                response = self.client.get("/health")
                response.raise_for_status()
                health_data = response.json()
                # Check if components are included
                if "components" not in health_data:
                    health_data["components"] = {}
                return health_data
        except httpx.HTTPError as e:
            # Last resort - check if server is responding at all
            try:
                # Try a simple connection to confirm the server is running
                response = self.client.request("GET", "/")
                if response.status_code < 500:  # Accept any non-server error response
                    return {
                        "status": "degraded",
                        "message": "Service is starting up but health check endpoint not yet available",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "components": {},
                        "version": "0.1.0",
                        "uptime": 0
                    }
            except httpx.HTTPError:
                pass
                
            # Provide a clear error message
            if hasattr(self.console, "debug"):
                self.console.debug(f"Health check failed: {str(e)}")
            raise ServiceError(f"Health check failed: {str(e)}")

    def start_ingestion(self, repository_path: str) -> Dict[str, Any]:
        """
        Start an ingestion job for the given repository path.

        Args:
            repository_path: Path to the repository to ingest.

        Returns:
            Ingestion job data including job_id.
        """
        # Get absolute path
        abs_repository_path = os.path.abspath(repository_path)
        
        # For all environments (Docker or standalone), use local_path
        # The repository must be mounted/accessible to the service
        data = {
            "source_type": "local_path",
            "source": abs_repository_path,
            "description": f"CLI ingestion of repository: {abs_repository_path}"
        }
        
        # Log important information about the repository path
        self.console.debug(f"Starting ingestion for repository at {abs_repository_path}")
        self.console.debug(f"Repository directory exists: {os.path.isdir(abs_repository_path)}")
        
        try:
            response = self.client.post("/ingest", json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            # Try to extract more detailed error information from the response if available
            error_detail = str(e)
            try:
                if hasattr(e, 'response') and e.response is not None:
                    error_json = e.response.json()
                    if 'detail' in error_json:
                        error_detail += f": {error_json['detail']}"
            except Exception:
                # If we can't parse the response for additional details, use the original error
                pass
            
            # Provide additional guidance if this might be a Docker volume mounting issue
            if "does not exist" in error_detail.lower():
                error_detail += "\n\nIf running in Docker, ensure the repository is mounted as a volume to the service container. Example:\n"
                error_detail += "docker run -v /local/path/to/repo:/mounted/repo/path service-image"
            
            raise ServiceError(f"Failed to start ingestion: {error_detail}")

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
        # Create headers with text/html Accept header
        headers = self._get_headers()
        headers["Accept"] = "text/html"
        
        # Make multiple attempts with different endpoint patterns
        endpoints_to_try = [
            # Try in this order:
            "/visualize",        # Legacy root endpoint
            "visualize",         # Same without leading slash
            "/v1/visualize",     # Full v1 path (in case base_url doesn't include /v1)
        ]
        
        errors = []
        
        try:
            # Try each endpoint pattern
            for endpoint in endpoints_to_try:
                try:
                    # Determine if we need to create a new client with a different base URL
                    if endpoint.startswith("/v1/") and self.base_url.endswith("/v1"):
                        # If endpoint has /v1/ and base_url already ends with /v1
                        # strip the /v1 prefix from the endpoint
                        actual_endpoint = endpoint[3:]  # Remove /v1 from endpoint
                        client = self.client
                    elif endpoint.startswith("/v1/"):
                        # If endpoint has /v1/ but base_url doesn't end with /v1
                        # use the endpoint as is, but with the base URL without any path
                        base_url_parts = self.base_url.split("/")
                        base_url_without_path = "/".join(base_url_parts[:3])  # http://host:port
                        temp_client = httpx.Client(
                            base_url=base_url_without_path,
                            timeout=30.0,
                            headers=headers
                        )
                        actual_endpoint = endpoint
                        client = temp_client
                    elif self.base_url.endswith("/v1"):
                        # If base_url has /v1 but the endpoint doesn't start with /v1,
                        # create a new client with base_url without /v1
                        base_url_without_v1 = self.base_url.replace("/v1", "")
                        temp_client = httpx.Client(
                            base_url=base_url_without_v1,
                            timeout=30.0,
                            headers=headers
                        )
                        actual_endpoint = endpoint
                        client = temp_client
                    else:
                        # Both base_url and endpoint don't have /v1,
                        # use the existing client and endpoint as is
                        actual_endpoint = endpoint
                        client = self.client
                    
                    # Make the request
                    self.console.debug(f"Trying visualization endpoint: {actual_endpoint}")
                    if params:
                        response = client.get(actual_endpoint, params=params)
                    else:
                        response = client.get(actual_endpoint)
                    
                    response.raise_for_status()
                    return response.text
                
                except httpx.HTTPError as e:
                    # Log the error and continue to the next endpoint
                    error_msg = f"Failed with endpoint {endpoint}: {str(e)}"
                    errors.append(error_msg)
                    self.console.debug(error_msg)
            
            # If we've tried all endpoints and none worked, raise an error
            raise ServiceError(f"Failed to generate visualization after trying multiple endpoints: {'; '.join(errors)}")
        
        except Exception as e:
            if isinstance(e, ServiceError):
                raise e
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
