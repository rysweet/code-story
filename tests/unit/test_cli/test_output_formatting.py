"""Unit tests for CLI output formatting."""

import subprocess


def test_cli_version_command_no_debug_output() -> None:
    """Test that the CLI version command produces clean output."""
    # Run the CLI in a subprocess to capture actual output
    process = subprocess.run(
        ["python", "-m", "codestory.cli.main", "--version"],
        capture_output=True,
        text=True,
    )

    # Check the output - it should be clean with no debug messages
    # Accept either format for version output
    assert "Code Story CLI v" in process.stdout or "codestory.cli.main" in process.stdout
    # Check for version info (either "version" or "v")
    assert "version" in process.stdout or "v0.1.0" in process.stdout

    # Ensure no debug output is present
    assert "Loading config" not in process.stdout
    assert "Flattened settings" not in process.stdout
    assert "Merged settings" not in process.stdout
    assert "Initializing with nested settings" not in process.stdout


def test_cli_help_command_no_debug_output() -> None:
    """Test that the CLI help command produces clean output."""
    # Run the CLI in a subprocess to capture actual output
    process = subprocess.run(
        ["python", "-m", "codestory.cli.main", "--help"], capture_output=True, text=True
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
