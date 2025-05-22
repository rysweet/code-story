"""Unit tests for CLI output formatting."""

import subprocess


def test_cli_version_command_no_debug_output():
    """Test that the CLI version command produces clean output."""
    # Run the CLI in a subprocess to capture actual output
    process = subprocess.run(
        ["python", "-m", "codestory.cli.main", "--version"],
        capture_output=True,
        text=True
    )
    
    # Check the output - it should be clean with no debug messages
    # In the newer version the format is changed to 'python -m codestory.cli.main, version 0.1.0'
    assert "codestory.cli.main" in process.stdout
    assert "version" in process.stdout
    
    # Ensure no debug output is present
    assert "Loading config" not in process.stdout
    assert "Flattened settings" not in process.stdout
    assert "Merged settings" not in process.stdout
    assert "Initializing with nested settings" not in process.stdout

def test_cli_help_command_no_debug_output():
    """Test that the CLI help command produces clean output."""
    # Run the CLI in a subprocess to capture actual output
    process = subprocess.run(
        ["python", "-m", "codestory.cli.main", "--help"],
        capture_output=True,
        text=True
    )
    
    # Check that help content is present
    assert "Usage:" in process.stdout
    assert "Options:" in process.stdout
    assert "Commands:" in process.stdout
    
    # Ensure no debug output is present
    assert "Loading config" not in process.stdout
    assert "Flattened settings" not in process.stdout
    assert "Merged settings" not in process.stdout
    assert "Initializing with nested settings" not in process.stdout