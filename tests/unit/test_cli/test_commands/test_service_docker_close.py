import subprocess
import sys
import pytest

@pytest.mark.usefixtures("recwarn")
def test_service_status_no_resource_warning(recwarn):
    """
    Ensure that running the CLI 'service status' command does not emit a ResourceWarning
    from the Docker SDK (i.e., all Docker clients are properly closed).
    """
    # Run the CLI command as a subprocess to capture warnings
    result = subprocess.run(
        [sys.executable, "-m", "codestory.cli.main", "service", "status"],
        capture_output=True,
        text=True,
    )
    # Print output for debugging if needed
    print(result.stdout)
    print(result.stderr)
    # Assert no ResourceWarning was raised
    warnings = [w for w in recwarn if issubclass(w.category, ResourceWarning)]
    assert not warnings, f"ResourceWarning(s) found: {warnings}"