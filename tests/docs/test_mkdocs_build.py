import os
import subprocess
import pytest


def test_mkdocs_build():
    if os.environ.get("DOCS_SKIP"):
        pytest.skip("DOCS_SKIP is set; skipping mkdocs build test.")
    subprocess.run(
        ["uv", "run", "mkdocs", "build", "--strict", "--site-dir", "tmp_site"],
        check=True,
    )
