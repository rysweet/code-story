#!/usr/bin/env python3
"""
Fix Neo4j connection issues in CI environment.

This script applies patches to test files to handle port differences
between local development and CI environments.
"""

import glob
import os
import re
import sys


def fix_neo4j_port_in_file(file_path):
    """Replace hardcoded Neo4j port with environment-aware code in a file."""
    with open(file_path) as f:
        content = f.read()
    
    # Only modify files that have the bolt://localhost:7688 string
    if 'bolt://localhost:7688' not in content:
        return False
    
    # Replace hardcoded port with environment-aware code
    # For direct string references
    modified_content = re.sub(
        r'bolt://localhost:7688', 
        'bolt://localhost:" + (os.environ.get("CI") == "true" and "7687" or "7688")',
        content
    )
    
    # For f-strings and string constants
    modified_content = re.sub(
        r'([\"\'])bolt://localhost:7688[\"\']', 
        r'\1bolt://localhost:" + (os.environ.get("CI") == "true" and "7687" or "7688") + "\1',
        modified_content
    )
    
    # Add os import if needed
    if 'import os' not in modified_content:
        modified_content = 'import os\n' + modified_content
    
    # Write back if changes were made
    if content != modified_content:
        with open(file_path, 'w') as f:
            f.write(modified_content)
        return True
    
    return False

def update_conftest():
    """Apply specific fix to conftest.py which handles most Neo4j connections."""
    conftest_path = os.path.join('tests', 'integration', 'conftest.py')
    
    if not os.path.exists(conftest_path):
        print(f"Error: {conftest_path} not found")
        return False
    
    with open(conftest_path) as f:
        content = f.read()
    
    # Add CI environment detection and port selection
    neo4j_env_fix = '''
@pytest.fixture(scope="session")
def neo4j_env():
    """Setup Neo4j environment variables for tests."""
    # Determine the correct Neo4j port to use
    # In CI environment, Neo4j is often on the standard port
    # In local docker-compose.test.yml, it's on port 7688
    ci_env = os.environ.get("CI") == "true"
    neo4j_port = "7687" if ci_env else "7688"
    
    # Set the environment variables
    neo4j_uri = f"bolt://localhost:{neo4j_port}"
    os.environ["NEO4J_URI"] = neo4j_uri
    os.environ["NEO4J__URI"] = neo4j_uri
    '''
    
    # Replace the existing function with our fixed version
    content = re.sub(
        (r'@pytest\.fixture\(scope="session"\)\ndef neo4j_env\(\):.*?os\.environ\["NEO4J_URI"\] = '
        r'"bolt://localhost:7688"\s+os\.environ\["NEO4J__URI"\] = "bolt://localhost:7688"'),
        neo4j_env_fix,
        content,
        flags=re.DOTALL
    )
    
    # Fix the neo4j_connector fixture
    neo4j_connector_fix = '''
    # Use correct Neo4j port based on environment
    ci_env = os.environ.get("CI") == "true"
    default_uri = f"bolt://localhost:{7687 if ci_env else 7688}"
    uri = os.environ.get("NEO4J__URI") or os.environ.get("NEO4J_URI") or default_uri
    '''
    
    content = re.sub(
        r'uri = os\.environ\.get\("NEO4J__URI"\) or os\.environ\.get\("NEO4J_URI"\) or "bolt://localhost:7688"',
        neo4j_connector_fix,
        content
    )
    
    with open(conftest_path, 'w') as f:
        f.write(content)
    
    return True

def main():
    """Main entry point for the script."""
    # Update conftest.py first as it handles most Neo4j connections
    if update_conftest():
        print("Updated conftest.py to handle different Neo4j ports in CI")
    
    # Find all Python files in the test directories that might have Neo4j connections
    test_files = glob.glob('tests/**/*.py', recursive=True)
    test_files += glob.glob('scripts/run_*.py')
    
    # Fixed file count
    fixed_count = 0
    
    # Apply fix to each file
    for file_path in test_files:
        if fix_neo4j_port_in_file(file_path):
            print(f"Fixed Neo4j port in {file_path}")
            fixed_count += 1
    
    print(f"Total files fixed: {fixed_count}")
    return 0

if __name__ == "__main__":
    sys.exit(main())