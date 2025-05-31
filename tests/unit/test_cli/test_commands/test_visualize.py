from typing import Any
'Unit tests for the visualize CLI commands.'
import os
import tempfile
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from codestory.cli.main import app

class TestVisualizeCommands:
    """Tests for the visualize CLI commands."""

    def test_visualize_help(self: Any, cli_runner: CliRunner) -> None:
        """Test 'visualize --help' command."""
        result = cli_runner.invoke(app, ['visualize', '--help'])
        assert result.exit_code == 0
        assert 'visualize' in result.output.lower()
        assert 'generate' in result.output.lower()
        assert 'list' in result.output.lower()
        assert 'open' in result.output.lower()

    def test_visualize_generate(self: Any, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'visualize generate' command."""
        mock_service_client.generate_visualization.return_value = '<html><body>Test visualization</body></html>'
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, 'viz.html')
            with patch('codestory.cli.commands.visualize.webbrowser.open') as mock_open:
                with patch('codestory.cli.main.ServiceClient', return_value=mock_service_client):
                    result = cli_runner.invoke(app, ['visualize', 'generate', '--output', output_path, '--no-browser'])
                    assert result.exit_code == 0
                    assert 'Visualization generated successfully' in result.output
                    assert output_path in result.output
                    mock_service_client.generate_visualization.assert_called_once()
                    mock_open.assert_not_called()
                    assert os.path.exists(output_path)
                    with open(output_path) as f:
                        content = f.read()
                        assert 'Test visualization' in content

    def test_visualize_generate_with_options(self: Any, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test 'visualize generate' command with various options."""
        mock_service_client.generate_visualization.return_value = '<html><body>Test visualization</body></html>'
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, 'viz.html')
            with patch('codestory.cli.commands.visualize.webbrowser.open'), patch('codestory.cli.main.ServiceClient', return_value=mock_service_client):
                result = cli_runner.invoke(app, ['visualize', 'generate', '--output', output_path, '--no-browser', '--type', 'hierarchy', '--theme', 'dark', '--title', 'Test Visualization'])
                assert result.exit_code == 0
                assert 'Type: hierarchy' in result.output
                assert 'Theme: dark' in result.output
                mock_service_client.generate_visualization.assert_called_once()
                params = mock_service_client.generate_visualization.call_args[0][0]
                assert params.get('type') == 'hierarchy'
                assert params.get('theme') == 'dark'
                assert params.get('title') == 'Test Visualization'

    def test_visualize_list(self: Any, cli_runner: CliRunner) -> None:
        """Test 'visualize list' command with mock files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            orig_dir = os.getcwd()
            os.chdir(temp_dir)
            try:
                open('codestory-graph-20250101-121212.html', 'w').write('test')
                open('codestory-graph-20250101-121313.html', 'w').write('test')
                result = cli_runner.invoke(app, ['visualize', 'list'])
                assert result.exit_code == 0
                assert 'Recently generated visualizations' in result.output
                assert 'codestory-graph-' in result.output
                assert '20250101-121212' in result.output
                assert '20250101-121313' in result.output
            finally:
                os.chdir(orig_dir)

    def test_visualize_list_empty(self: Any, cli_runner: CliRunner) -> None:
        """Test 'visualize list' command with no files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            orig_dir = os.getcwd()
            os.chdir(temp_dir)
            try:
                result = cli_runner.invoke(app, ['visualize', 'list'])
                assert result.exit_code == 0
                assert 'No visualizations found' in result.output
            finally:
                os.chdir(orig_dir)

    def test_visualize_open(self: Any, cli_runner: CliRunner) -> None:
        """Test 'visualize open' command."""
        with tempfile.NamedTemporaryFile(suffix='.html') as temp_file:
            temp_file.write(b'<html><body>Test</body></html>')
            temp_file.flush()
            with patch('codestory.cli.commands.visualize.webbrowser.open') as mock_open:
                result = cli_runner.invoke(app, ['visualize', 'open', temp_file.name])
                assert result.exit_code == 0
                assert 'Opening' in result.output
                mock_open.assert_called_once()
                assert temp_file.name in mock_open.call_args[0][0]

    def test_visualize_help_command(self: Any, cli_runner: CliRunner) -> None:
        """Test 'visualize help' command."""
        result = cli_runner.invoke(app, ['visualize', 'help'])
        assert result.exit_code == 0
        assert 'Code Story Graph Visualization' in result.output
        assert 'Visualization Types' in result.output

    def test_visualize_service_auto_start(self: Any, cli_runner: CliRunner, mock_service_client: MagicMock) -> None:
        """Test visualize generate with service auto-start."""
        first_call = True

        def side_effect(*args, **kwargs):
            nonlocal first_call
            if first_call:
                first_call = False
                raise Exception('Service not available')
            return '<html><body>Auto-started service test visualization</body></html>'
        mock_service_client.generate_visualization.side_effect = side_effect
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, 'viz.html')
            with patch('subprocess.Popen') as mock_popen, patch('time.sleep'):
                mock_process = MagicMock()
                mock_popen.return_value = mock_process
                with patch('codestory.cli.commands.visualize.webbrowser.open'):
                    with patch('codestory.cli.main.ServiceClient', return_value=mock_service_client):
                        result = cli_runner.invoke(app, ['visualize', 'generate', '--output', output_path, '--no-browser'])
                        assert result.exit_code == 0
                        assert 'Starting service automatically' in result.output
                        assert 'Visualization generated successfully' in result.output
                        mock_popen.assert_called_once()
                        mock_service_client.generate_visualization.call_count >= 2