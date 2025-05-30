#!/usr/bin/env python3
"""
Auto-ignore missing library stubs in MyPy configuration.

This script reads MyPy output, identifies libraries missing stubs or py.typed markers,
and automatically adds ignore sections to .mypy.ini for those libraries.
"""

import re
import sys
from pathlib import Path
from typing import List, Set


def parse_mypy_output(file_path: str) -> Set[str]:
    """
    Parse MyPy output file and extract library names that are missing stubs.
    
    Args:
        file_path: Path to MyPy output file
    
    Returns:
        Set of library names to ignore
    """
    missing_stubs = set()
    
    # Pattern to match missing stubs/py.typed messages
    stub_pattern = re.compile(
        r'.*: error: Library stubs not installed for "([^"]+)".*|'
        r'.*: error: Skipping analyzing "([^"]+)": module is installed, but missing library stubs or py\.typed marker.*'
    )
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                match = stub_pattern.match(line.strip())
                if match:
                    # Get the library name from either capture group
                    lib_name = match.group(1) or match.group(2)
                    if lib_name:
                        # Extract top-level package name
                        top_level = lib_name.split('.')[0]
                        missing_stubs.add(top_level)
    
    except FileNotFoundError:
        print(f"Error: MyPy output file '{file_path}' not found")
        return missing_stubs
    except Exception as e:
        print(f"Error reading MyPy output file: {e}")
        return missing_stubs
    
    return missing_stubs


def read_mypy_ini() -> List[str]:
    """
    Read the current .mypy.ini file.
    
    Returns:
        List of lines from .mypy.ini
    """
    mypy_ini_path = Path('.mypy.ini')
    
    if not mypy_ini_path.exists():
        print("Error: .mypy.ini file not found")
        return []
    
    try:
        with open(mypy_ini_path, 'r', encoding='utf-8') as f:
            return f.readlines()
    except Exception as e:
        print(f"Error reading .mypy.ini: {e}")
        return []


def get_existing_ignores(lines: List[str]) -> Set[str]:
    """
    Extract existing ignore sections from .mypy.ini.
    
    Args:
        lines: Lines from .mypy.ini file
    
    Returns:
        Set of library names already being ignored
    """
    existing_ignores = set()
    
    # Pattern to match [mypy-LIBRARY.*] sections
    section_pattern = re.compile(r'^\[mypy-([^.\]]+)\.\*\]')
    
    for line in lines:
        match = section_pattern.match(line.strip())
        if match:
            lib_name = match.group(1)
            existing_ignores.add(lib_name)
    
    return existing_ignores


def add_ignore_sections(lines: List[str], libraries: Set[str]) -> List[str]:
    """
    Add ignore sections for missing libraries to .mypy.ini.
    
    Args:
        lines: Current lines from .mypy.ini
        libraries: Set of library names to add ignore sections for
    
    Returns:
        Updated lines with new ignore sections
    """
    if not libraries:
        return lines
    
    # Find the end of the file (or before any existing library-specific sections)
    insert_position = len(lines)
    
    # If there are existing [mypy-*] sections, insert before them
    for i, line in enumerate(lines):
        if line.strip().startswith('[mypy-') and not line.strip() == '[mypy]':
            insert_position = i
            break
    
    # Add a blank line before new sections if needed
    if insert_position > 0 and lines[insert_position - 1].strip():
        lines.insert(insert_position, '\n')
        insert_position += 1
    
    # Add ignore sections for each library
    for lib_name in sorted(libraries):
        section_lines = [
            f'[mypy-{lib_name}.*]\n',
            'ignore_missing_imports = True\n',
            '\n'
        ]
        
        for section_line in section_lines:
            lines.insert(insert_position, section_line)
            insert_position += 1
    
    return lines


def write_mypy_ini(lines: List[str]) -> bool:
    """
    Write updated lines back to .mypy.ini.
    
    Args:
        lines: Updated lines to write
    
    Returns:
        True if successful, False otherwise
    """
    mypy_ini_path = Path('.mypy.ini')
    
    try:
        # Create backup
        backup_path = mypy_ini_path.with_suffix('.ini.bak')
        if mypy_ini_path.exists():
            with open(mypy_ini_path, 'r', encoding='utf-8') as f:
                backup_content = f.read()
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(backup_content)
        
        # Write updated content
        with open(mypy_ini_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        return True
    
    except Exception as e:
        print(f"Error writing .mypy.ini: {e}")
        return False


def main():
    """Main function to process MyPy output and update .mypy.ini."""
    # Get MyPy output file path from command line argument
    if len(sys.argv) > 1:
        mypy_output_file = sys.argv[1]
    else:
        mypy_output_file = 'mypy_after_auto.txt'
    
    print(f"Processing MyPy output from: {mypy_output_file}")
    
    # Parse MyPy output to find missing stubs
    missing_stubs = parse_mypy_output(mypy_output_file)
    
    if not missing_stubs:
        print("No missing library stubs found in MyPy output")
        return
    
    print(f"Found {len(missing_stubs)} libraries missing stubs: {sorted(missing_stubs)}")
    
    # Read current .mypy.ini
    mypy_lines = read_mypy_ini()
    if not mypy_lines:
        return
    
    # Get existing ignore sections
    existing_ignores = get_existing_ignores(mypy_lines)
    
    # Find libraries that need new ignore sections
    new_ignores = missing_stubs - existing_ignores
    
    if not new_ignores:
        print("All missing libraries already have ignore sections in .mypy.ini")
        return
    
    print(f"Adding ignore sections for {len(new_ignores)} new libraries: {sorted(new_ignores)}")
    
    # Add new ignore sections
    updated_lines = add_ignore_sections(mypy_lines, new_ignores)
    
    # Write updated .mypy.ini
    if write_mypy_ini(updated_lines):
        print(f"Successfully updated .mypy.ini with {len(new_ignores)} new ignore sections")
        print("Backup created as .mypy.ini.bak")
    else:
        print("Failed to update .mypy.ini")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())