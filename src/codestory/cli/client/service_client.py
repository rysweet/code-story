"""Service client for interacting with the Code Story service API."""
import json
import os
import sys
import time
import webbrowser
from typing import Any
import httpx
from pydantic import SecretStr
from rich.console import Console
from codestory.config import Settings, get_settings

class ServiceClient:
    """Client for interacting with the Code Story service API."""

    def __init__(self, base_url: str | None=None, api_key: str | None=None, console: Console | None=None, settings: Settings | None=None) -> None:
        """
        Initialize the service client.

        Args:
            base_url: Service base URL. If not provided, uses settings.
            api_key: API key for authentication. If not provided, uses settings.
            console: Rich console for output. If not provided, creates a new one.
            settings: Settings object. If not provided, loads from configuration.
        """
        self.settings = settings or get_settings()
        try:
            host = getattr(self.settings.service, 'host', 'localhost')
            if host == '0.0.0.0':
                host = 'localhost'
            port = getattr(self.settings.service, 'port', 8000)
            if not isinstance(port, int):
                port = 8000
        except (AttributeError, ValueError):
            host = 'localhost'
            port = 8000
        self.base_url = base_url or f'http://{host}:{port}/v1'
        self.api_key = api_key
        try:
            if not self.api_key and hasattr(self.settings.service, 'api_key'):
                api_key_setting = self.settings.service.api_key
                if isinstance(api_key_setting, SecretStr):
                    self.api_key = api_key_setting.get_secret_value()
                else:
                    self.api_key = api_key_setting
        except (AttributeError, ValueError):
            pass
        self.console = console or Console()
        self.client = httpx.Client(base_url=self.base_url, timeout=30.0, headers=self._get_headers())
        self.session = self.client

    def _get_headers(self) -> dict[str, str]:
        """
        Get headers for API requests.

        Returns:
            Headers dictionary including auth if available.
        """
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers

    def check_service_health(self, auto_fix: bool=False, timeout: int | None=None) -> dict[str, Any]:
        """
        Check if the service is healthy.

        Args:
            auto_fix: If True, attempt to automatically fix Azure authentication issues
            timeout: Optional timeout in seconds for the health check request

        Returns:
            Health check response data.

        Raises:
            ServiceError: If the health check fails
        """
        try:
            try:
                params = {'auto_fix': 'true'} if auto_fix else {}
                client_params: dict[Any, Any] = {}
                if timeout is not None:
                    client_params['timeout'] = timeout
                client = httpx.Client(base_url=self.base_url, timeout=timeout or 30.0, headers=self._get_headers())
                response = client.get('/v1/health', params=params)
                response.raise_for_status()
                health_data = response.json()
                if 'components' not in health_data:
                    health_data['components'] = {}
                self._check_for_azure_auth_issues(health_data)
                return health_data
            except httpx.HTTPError:
                params = {'auto_fix': 'true'} if auto_fix else {}
                response = self.client.get('/health', params=params)
                response.raise_for_status()
                health_data = response.json()
                if 'components' not in health_data:
                    health_data['components'] = {}
                self._check_for_azure_auth_issues(health_data)
                return health_data
        except httpx.HTTPError as e:
            try:
                if 'pytest' in sys.modules:
                    self.console.print(f'[dim]Health check failed: {e!s}[/]', style='dim')
                    raise ServiceError(f'Health check failed: {e!s}')
                response = self.client.request('GET', '/')
                if response.status_code < 500:
                    resp_data = {'status': 'degraded', 'message': 'Service is starting up but health check endpoint not yet available', 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'components': {}, 'version': '0.1.0', 'uptime': 0}
                    self.console.print(f'[dim]Health check endpoint not available: {e!s}[/]', style='dim')
                    return resp_data
            except httpx.HTTPError as connect_err:
                self.console.print(f'[dim]Server connection failed: {connect_err!s}[/]', style='dim')
                raise ServiceError(f'Health check failed: {connect_err!s}') from connect_err
            self.console.print(f'[dim]Health check failed: {e!s}[/]', style='dim')
            raise ServiceError(f'Health check failed: {e!s}') from e

    def _check_for_azure_auth_issues(self, health_data: dict[str, Any]) -> None:
        """
        Check if health data indicates Azure authentication issues and provide guidance.

        Args:
            health_data: Health check response data
        """
        try:
            if health_data.get('components') and 'openai' in health_data['components'] and (health_data['components']['openai'].get('status') == 'unhealthy'):
                openai_details = health_data['components']['openai'].get('details', {})
                if openai_details.get('type') == 'AuthenticationError' or 'DefaultAzureCredential' in str(openai_details.get('error', '')) or 'AzureIdentityCredentialAdapter' in str(openai_details.get('error', '')) or ('AADSTS700003' in str(openai_details.get('error', ''))):
                    solution = openai_details.get('solution', 'az login --scope https://cognitiveservices.azure.com/.default')
                    hint = openai_details.get('hint', '')
                    tenant_id = openai_details.get('tenant_id', '')
                    renewal_attempted = openai_details.get('renewal_attempted', False)
                    renewal_success = openai_details.get('renewal_success', False)
                    self.console.print('[bold red]Azure Authentication Issue Detected[/bold red]')
                    self.console.print('The service is having trouble authenticating with Azure OpenAI.')
                    if renewal_attempted:
                        if renewal_success:
                            self.console.print('[yellow]Automatic renewal was attempted and succeeded, but the service still reports auth issues.[/yellow]')
                            self.console.print("This might be because the service hasn't fully recognized the new tokens yet.")
                            self.console.print('\n[bold yellow]Recommendations:[/bold yellow]')
                            self.console.print('1. Wait a minute and check the status again: codestory service status')
                            self.console.print('2. Run the CLI auth renewal: codestory service auth-renew')
                            self.console.print('3. Try restarting the service: codestory service restart')
                        else:
                            self.console.print('[yellow]Automatic renewal was attempted but failed.[/yellow]')
                            if 'renewal_error' in openai_details:
                                self.console.print(f"[dim]Error: {openai_details['renewal_error']}[/dim]")
                            self.console.print('\n[bold yellow]Recommendations:[/bold yellow]')
                            self.console.print('1. Run the CLI auth renewal: codestory service auth-renew')
                            if tenant_id:
                                self.console.print(f'2. Specify tenant ID: codestory service auth-renew --tenant {tenant_id}')
                            self.console.print('3. Try manually running: ' + solution)
                    else:
                        self.console.print('\n[bold yellow]Solution:[/bold yellow]')
                        self.console.print('Run the following command to renew your Azure credentials:')
                        self.console.print('[bold cyan]codestory service auth-renew[/bold cyan]\n')
                        if tenant_id:
                            self.console.print('Or with specific tenant ID:')
                            self.console.print(f'[bold cyan]codestory service auth-renew --tenant {tenant_id}[/bold cyan]\n')
                        self.console.print('Alternatively, run this command manually:')
                        self.console.print(f'[dim]{solution}[/dim]\n')
                        if hint:
                            self.console.print(f'[dim]{hint}[/dim]\n')
                    health_data['components']['openai']['details']['user_message'] = 'Azure authentication credentials expired. See instructions for renewal.'
        except Exception as e:
            self.console.print(f'[dim]Error checking for Azure auth issues: {e!s}[/dim]', style='dim')

    def _handle_error_package(self, data: dict[str, Any]) -> dict[str, Any]:
        """Detects service-side errors in response and handles them.
        
        - Prints errors
        - Runs a health status check.
        """
        errors = data.get('error_package')
        if errors:
            self.console.print('[bold red]Service Errors:[/]')
            for err in errors:
                self.console.print(f'- {err}')
            status_data = self.check_service_health(auto_fix=False)
            self.console.print('[bold blue]Service Status:[/]')
            self.console.print(json.dumps(status_data, indent=2))
        return data

    def start_ingestion(self, repository_path: str, priority: str='default', dependencies: list[str] | None=None) -> dict[str, Any]:
        """
        Start an ingestion job for the given repository path.

        Args:
            repository_path: Path to the repository to ingest.
                This can be either a local path or a container path.
                For container paths, use /repositories/repo-name format.
            priority: Task priority ("high", "default", or "low"). Routes to the appropriate Celery queue.
            dependencies: List of job IDs or step names this job depends on. Job will not start until all dependencies are complete.

        Returns:
            Ingestion job data including job_id.
        """
        abs_repository_path = os.path.abspath(repository_path)
        is_container_path = abs_repository_path.startswith('/repositories')
        repo_config_path = None
        if not is_container_path:
            repo_config_path = os.path.join(abs_repository_path, '.codestory', 'repository.toml')
            if os.path.exists(repo_config_path):
                self.console.print(f'[dim]Repository config file found at [cyan]{repo_config_path}[/][/]', style='dim')
        data = {'source_type': 'local_path', 'source': abs_repository_path, 'description': f'CLI ingestion of repository: {abs_repository_path}', 'priority': priority}
        if dependencies:
            data['dependencies'] = list(dependencies)
        self.console.print(f'Starting ingestion for repository at [cyan]{abs_repository_path}[/]', style='dim')
        self.console.print(f'Repository directory exists: [cyan]{os.path.isdir(abs_repository_path)}[/]', style='dim')
        if is_container_path:
            self.console.print('[dim]Using container path directly[/]', style='dim')
        try:
            response = self.client.post('/ingest', json=data)
            response.raise_for_status()
            data = response.json()
            return self._handle_error_package(data)
        except httpx.HTTPError as e:
            error_detail = str(e)
            try:
                if hasattr(e, 'response') and e.response is not None:
                    error_json = e.response.json()
                    if 'detail' in error_json:
                        error_detail += f": {error_json['detail']}"
            except Exception:
                pass
            if 'does not exist' in error_detail.lower():
                error_detail += '\n\nIf running in Docker, ensure the repository is mounted as a volume to the service container.'
                repo_name = os.path.basename(abs_repository_path)
                error_detail += '\n\nTry these solutions:'
                error_detail += '\n1. Mount the repository using our script:'
                error_detail += f'\n   ./scripts/mount_repository.sh "{abs_repository_path}" --restart'
                error_detail += '\n\n2. Or use the container path format with the CLI:'
                error_detail += f'\n   codestory ingest start "{abs_repository_path}" --container'
                error_detail += '\n\n3. For manual mounting, modify your docker-compose.yml to include:'
                error_detail += '\n   volumes:'
                error_detail += f'\n     - {abs_repository_path}:/repositories/{repo_name}'
            raise ServiceError(f'Failed to start ingestion: {error_detail}') from None

    def get_ingestion_status(self, job_id: str) -> dict[str, Any]:
        """
        Get the status of an ingestion job.

        Args:
            job_id: ID of the ingestion job.

        Returns:
            Ingestion job status data.
        """
        try:
            response = self.client.get(f'/ingest/{job_id}')
            response.raise_for_status()
            data = response.json()
            return self._handle_error_package(data)
        except httpx.HTTPError as e:
            raise ServiceError(f'Failed to get ingestion status: {e!s}') from e

    def stop_ingestion(self, job_id: str) -> dict[str, Any]:
        """
        Stop an ingestion job.

        Args:
            job_id: ID of the ingestion job to stop.

        Returns:
            Response data indicating success or failure.
        """
        try:
            response = self.client.post(f'/ingest/{job_id}/cancel')
            response.raise_for_status()
            data = response.json()
            return self._handle_error_package(data)
        except httpx.HTTPError as e:
            raise ServiceError(f'Failed to stop ingestion: {e!s}') from e

    def list_ingestion_jobs(self) -> list[dict[str, Any]]:
        """
        List all ingestion jobs.

        Returns:
            List of ingestion job data.
        """
        try:
            response = self.client.get('/ingest')
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and 'error_package' in data:
                data = self._handle_error_package(data)
            if isinstance(data, dict):
                if 'items' in data:
                    return data['items']
                elif 'jobs' in data:
                    return data['jobs']
                elif 'job_id' in data:
                    if data.get('job_id') == 'jobs' and self.console:
                        self.console.print('[yellow]Warning: Mock service detected[/yellow]')
                    return [data]
                else:
                    raise ServiceError("Invalid response format: Response does not contain expected job data structure with 'items', 'jobs', or single job data")
            elif isinstance(data, list):
                return data
            else:
                raise ServiceError(f'Unexpected response format: {type(data)}')
        except httpx.HTTPError as e:
            raise ServiceError(f'Failed to list ingestion jobs: {e!s}') from e
        except (KeyError, json.JSONDecodeError) as e:
            raise ServiceError(f'Invalid response format: {e!s}') from e

    def execute_query(self, query: str, parameters: dict[str, Any] | None=None, query_type: str | None=None) -> dict[str, Any]:
        """
        Execute a Cypher query or MCP tool call.

        Args:
            query: Cypher query or MCP tool call string.
            parameters: Optional query parameters.
            query_type: Optional query type ("read" or "write"). If None, auto-detected 
                based on query.

        Returns:
            Query results.
        """
        data = {'query': query}
        if parameters:
            data['parameters'] = parameters
        if query_type in ['read', 'write']:
            data['query_type'] = query_type
        try:
            is_cypher = query.strip().upper().startswith(('MATCH', 'CREATE', 'MERGE', 'RETURN', 'DELETE', 'REMOVE', 'SET', 'WITH'))
            endpoint_type = 'cypher' if is_cypher else 'mcp'
            if query_type is None and is_cypher:
                if query.strip().upper().startswith(('CREATE', 'MERGE', 'DELETE', 'REMOVE', 'SET')):
                    data['query_type'] = 'write'
                else:
                    data['query_type'] = 'read'
            endpoint = '/query/cypher' if endpoint_type == 'cypher' else '/query'
            response = self.client.post(endpoint, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise ServiceError(f'Query execution failed: {e!s}') from e

    def ask_question(self, question: str) -> dict[str, Any]:
        """
        Ask a natural language question about the codebase.

        Args:
            question: Natural language question.

        Returns:
            Answer data.
        """
        data = {'question': question}
        try:
            response = self.client.post('/ask', json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise ServiceError(f'Failed to ask question: {e!s}') from e

    def get_config(self, include_sensitive: bool=False) -> dict[str, Any]:
        """
        Get the current configuration.

        Args:
            include_sensitive: Whether to include sensitive values.

        Returns:
            Configuration data.
        """
        params: dict[Any, Any] = {}
        if include_sensitive:
            params['include_sensitive'] = 'true'
        try:
            response = self.client.get('/config', params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise ServiceError(f'Failed to get configuration: {e!s}') from e

    def update_config(self, updates: dict[str, Any]) -> dict[str, Any]:
        """
        Update configuration values.

        Args:
            updates: Dictionary of configuration keys and values to update.

        Returns:
            Updated configuration data.
        """
        try:
            response = self.client.patch('/config', json=updates)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise ServiceError(f'Failed to update configuration: {e!s}') from e

    def start_service(self) -> dict[str, Any]:
        """
        Start the Code Story service.

        Returns:
            Service status data.
        """
        try:
            response = self.client.post('/service/start')
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise ServiceError(f'Failed to start service: {e!s}') from e

    def stop_service(self) -> dict[str, Any]:
        """
        Stop the Code Story service.

        Returns:
            Service status data.
        """
        try:
            response = self.client.post('/service/stop')
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise ServiceError(f'Failed to stop service: {e!s}') from e

    def get_service_status(self, renew_auth: bool=False) -> dict[str, Any]:
        """Query the health endpoint and return the status of the Code Story service.
        
        Returns the status of the service and its dependencies.
        """
        import traceback
        import rich
        import rich.console
        import rich.panel
        import rich.pretty
        import rich.text
        import rich.traceback
        console = rich.console.Console()
        console.log(f'[debug] get_service_status: base_url={self.base_url}')
        try:
            response = self.session.get(f'{self.base_url}/health', timeout=10)
            console.log(f'[debug] GET {self.base_url}/health -> status {response.status_code}')
            response.raise_for_status()
            health_data = response.json()
            console.log('[debug] Health endpoint response:')
            console.log(health_data)
            return health_data
        except Exception as e:
            console.log(f'[error] Exception in get_service_status: {e}')
            console.log('[error] Traceback:')
            tb = traceback.format_exc()
            console.log(tb)
            raise

    def generate_visualization(self, params: dict[str, Any] | None=None) -> str:
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
        headers = self._get_headers()
        headers['Accept'] = 'text/html'
        endpoints_to_try = ['/visualize', 'visualize', '/v1/visualize']
        errors: list[Any] = []
        try:
            for endpoint in endpoints_to_try:
                try:
                    if endpoint.startswith('/v1/') and self.base_url.endswith('/v1'):
                        actual_endpoint = endpoint[3:]
                        client = self.client
                    elif endpoint.startswith('/v1/'):
                        base_url_parts = self.base_url.split('/')
                        base_url_without_path = '/'.join(base_url_parts[:3])
                        temp_client = httpx.Client(base_url=base_url_without_path, timeout=30.0, headers=headers)
                        actual_endpoint = endpoint
                        client = temp_client
                    elif self.base_url.endswith('/v1'):
                        base_url_without_v1 = self.base_url.replace('/v1', '')
                        temp_client = httpx.Client(base_url=base_url_without_v1, timeout=30.0, headers=headers)
                        actual_endpoint = endpoint
                        client = temp_client
                    else:
                        actual_endpoint = endpoint
                        client = self.client
                    self.console.print(f'Trying visualization endpoint: [cyan]{actual_endpoint}[/]', style='dim')
                    if params:
                        response = client.get(actual_endpoint, params=params)
                    else:
                        response = client.get(actual_endpoint)
                    response.raise_for_status()
                    return response.text
                except httpx.HTTPError as e:
                    error_msg = f'Failed with endpoint {endpoint}: {e!s}'
                    errors.append(error_msg)
                    self.console.print(f'{error_msg}', style='dim')
            raise ServiceError(f"Failed to generate visualization after trying multiple endpoints: {'; '.join(errors)}")
        except Exception as e:
            if isinstance(e, ServiceError):
                raise e
            raise ServiceError(f'Failed to generate visualization: {e!s}') from e

    def open_ui(self) -> None:
        """Open the GUI in the default web browser."""
        try:
            ui_url = getattr(self.settings.service, 'ui_url', None)
        except (AttributeError, ValueError):
            ui_url = None
        if not ui_url:
            ui_url = 'http://localhost:5173'
        webbrowser.open(ui_url)

    def renew_azure_auth(self, tenant_id: str | None=None) -> dict[str, Any]:
        """
        Renew Azure authentication tokens.

        This method calls the Azure authentication renewal endpoint.

        Args:
            tenant_id: Optional Azure tenant ID for authentication

        Returns:
            Dictionary with renewal status information

        Raises:
            ServiceError: If the renewal process fails
        """
        params: dict[Any, Any] = {}
        if tenant_id:
            params['tenant_id'] = tenant_id
        try:
            try:
                response = self.client.get('/v1/auth-renew', params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError:
                response = self.client.get('/auth-renew', params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            error_detail = str(e)
            try:
                if hasattr(e, 'response') and e.response is not None:
                    error_json = e.response.json()
                    if 'detail' in error_json:
                        error_detail = error_json['detail']
                    elif 'message' in error_json:
                        error_detail = error_json['message']
            except Exception:
                pass
            if 'CLI error' in error_detail or 'NormalizedResponse' in error_detail:
                raise ServiceError(f'Azure authentication renewal failed due to Azure CLI installation issue: {error_detail}\nTry updating or reinstalling Azure CLI with: brew update && brew upgrade azure-cli') from None
            else:
                raise ServiceError(f'Azure authentication renewal failed: {error_detail}') from None

    def clear_database(self, confirm: bool=False) -> dict[str, Any]:
        """
        Clear all data from the database by executing a delete query.

        This is a destructive operation that will delete all nodes and relationships in
        the database. It requires admin privileges. Schema constraints and indexes will remain.

        Args:
            confirm: Whether the operation has been confirmed. Must be True to proceed.

        Returns:
            Dictionary with status information

        Raises:
            ServiceError: If the clear operation fails
            ValueError: If the operation is not confirmed
        """
        if not confirm:
            raise ValueError('Database clear operation must be explicitly confirmed by setting confirm=True')
        try:
            self.console.print('[yellow]Clearing all data from database...[/]')
            self.execute_query(query='MATCH (n) DETACH DELETE n', query_type='write')
            self.console.print('[yellow]Reinitializing database schema...[/]')
            self.execute_query(query='CALL apoc.schema.assert({}, {})', query_type='write')
            return {'status': 'success', 'message': 'Database cleared successfully', 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
        except ServiceError as e:
            error_message = str(e)
            if '403' in error_message or 'forbidden' in error_message.lower():
                raise ServiceError('Administrative privileges required to clear database') from e
            raise ServiceError(f'Failed to clear database: {error_message}') from e
        except Exception as e:
            raise ServiceError(f'Failed to clear database: {e!s}') from e

class ServiceError(Exception):
    """Exception raised for service client errors."""
    pass