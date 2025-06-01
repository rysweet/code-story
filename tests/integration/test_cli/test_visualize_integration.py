from typing import Any

'Integration tests for CLI visualization commands.'
import os
import tempfile
from unittest.mock import patch

from click.testing import CliRunner

from codestory.cli.main import app


class TestVisualizeCommands:
    """Integration tests for visualization-related CLI commands."""

    def test_visualize_help(self: Any, cli_runner: CliRunner) -> None:
        """Test 'visualize --help' command."""
        result = cli_runner.invoke(app, ['visualize', '--help'])
        assert result.exit_code == 0
        assert 'visualize' in result.output.lower()
        assert 'generate' in result.output.lower()
        assert 'list' in result.output.lower()
        assert 'open' in result.output.lower()

    def test_visualize_generate(self: Any, cli_runner: CliRunner) -> None:
        """Test 'visualize generate' command."""
        with patch('subprocess.Popen') as mock_popen:
            result = cli_runner.invoke(app, ['visualize', 'generate', '--no-browser', '--type', 'force', '--theme', 'dark'])
            assert result.exit_code == 0
            assert 'Starting service automatically' in result.output
            assert mock_popen.called

    def test_visualize_list(self: Any, cli_runner: CliRunner) -> None:
        """Test 'visualize list' command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            orig_dir = os.getcwd()
            os.chdir(temp_dir)
            try:
                with open('codestory-graph-test.html', 'w') as f:
                    f.write('<html><body>Test visualization</body></html>')
                result = cli_runner.invoke(app, ['visualize', 'list'])
                assert result.exit_code == 0
                if 'No visualizations found' not in result.output:
                    assert 'codestory-graph' in result.output
            finally:
                os.chdir(orig_dir)

    def test_visualize_help_command(self: Any, cli_runner: CliRunner) -> None:
        """Test 'visualize help' command."""
        result = cli_runner.invoke(app, ['visualize', 'help'])
        assert result.exit_code == 0
        assert 'Code Story Graph Visualization' in result.output
        assert 'Visualization Types' in result.output