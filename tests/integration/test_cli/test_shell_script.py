import subprocess
import os

script_path = os.path.abspath("tests/integration/test_cli/run_query_cypher.sh")
print(f"RUNNING SHELL SCRIPT: {script_path}")
print(f"Script exists: {os.path.exists(script_path)}")
print(f"Script is executable: {os.access(script_path, os.X_OK)}")
proc = subprocess.run(
    [
        "bash",
        script_path,
        "bolt://localhost:12345",
        "tests/fixtures/test_config.toml",
    ],
    text=True,
    capture_output=True,
)
print(f"Shell script return code: {proc.returncode}")
print("Shell script STDOUT:")
print(proc.stdout)
print("Shell script STDERR:")
print(proc.stderr)