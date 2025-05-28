#!/usr/bin/env python3
"""
This script fixes the Neo4j port configuration in test files.

It replaces the syntax error with the correct f-string format.
"""

import glob
import re


def fix_file(file_path):
    """Fix Neo4j URI syntax in test files."""
    print(f"Checking {file_path}...")
    with open(file_path) as f:
        content = f.read()

    # Fix syntax error with port configuration
    # From: "bolt://localhost:" + (os.environ.get("CI") == "true" and "7687" or "7688")"
    # To: f"bolt://localhost:{neo4j_port}"
    pattern1 = (
        r'"bolt://localhost:" \+ \(os\.environ\.get\("CI"\) == "true" and "7687" ' r'or "7688"\)"'
    )
    replacement1 = 'f"bolt://localhost:{neo4j_port}"'

    if re.search(pattern1, content):
        # Add port variable before the problematic line
        content = re.sub(pattern1, replacement1, content)

        # Add port variable declaration if not already present
        if "neo4j_port = " not in content:
            content = re.sub(
                r"import os",
                (
                    "import os\n\n# Determine Neo4j port based on CI environment\n"
                    'ci_env = os.environ.get("CI") == "true"\n'
                    'neo4j_port = "7687" if ci_env else "7688"'
                ),
                content,
            )

        with open(file_path, "w") as f:
            f.write(content)
        print(f"Fixed {file_path}")
        return True

    return False


def find_and_fix_files():
    """Find and fix all test files with Neo4j port configuration issues."""
    test_files = glob.glob("tests/**/*.py", recursive=True)
    fixed_count = 0

    for file_path in test_files:
        if fix_file(file_path):
            fixed_count += 1

    print(f"Fixed {fixed_count} files.")


if __name__ == "__main__":
    find_and_fix_files()
