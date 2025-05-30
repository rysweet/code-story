#!/usr/bin/env python3
"""
Script to automatically add `# type: ignore[attr-defined]` comments to lines
that have MyPy attr-defined errors.

Usage:
    python scripts/auto_ignore_attr_defined.py [mypy_output_file]
    
Default mypy_output_file is mypy_round3.txt
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple, Set
import shutil


def parse_mypy_output(mypy_file: Path) -> List[Tuple[str, int]]:
    """
    Parse MyPy output file and extract file paths and line numbers for attr-defined errors.
    
    Returns:
        List of (file_path, line_number) tuples
    """
    attr_defined_errors = []
    
    with open(mypy_file, 'r') as f:
        lines = f.readlines()
    
    # Look for lines with [attr-defined] error
    # Pattern: filepath:line_number: error: ... [attr-defined]
    # Also handle multi-line errors where [attr-defined] appears on next line
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Check for [attr-defined] on current line
        if '[attr-defined]' in line and ':' in line:
            # Pattern: filepath:line_number: error: ... [attr-defined]
            pattern = r'^([^:]+):(\d+):.*\[attr-defined\]'
            match = re.match(pattern, line)
            if match:
                file_path = match.group(1)
                line_number = int(match.group(2))
                attr_defined_errors.append((file_path, line_number))
                print(f"Found attr-defined error: {file_path}:{line_number}")
        
        # Check for [attr-defined] as a separate line after an error
        elif '[attr-defined]' in line and i > 0:
            prev_line = lines[i-1].strip()
            pattern = r'^([^:]+):(\d+):.*error:'
            match = re.match(pattern, prev_line)
            if match:
                file_path = match.group(1)
                line_number = int(match.group(2))
                attr_defined_errors.append((file_path, line_number))
                print(f"Found attr-defined error (multiline): {file_path}:{line_number}")
    
    return attr_defined_errors


def add_ignore_comment(file_path: str, line_number: int) -> bool:
    """
    Add `# type: ignore[attr-defined]` comment to the specified line if not already present.
    
    Returns:
        True if the comment was added, False if it was already present or if there was an error
    """
    try:
        path = Path(file_path)
        if not path.exists():
            print(f"Warning: File {file_path} does not exist")
            return False
        
        # Read the file
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if line_number > len(lines) or line_number < 1:
            print(f"Warning: Line {line_number} is out of range in {file_path}")
            return False
        
        # Check if the ignore comment is already present
        target_line = lines[line_number - 1]  # Convert to 0-based index
        ignore_comment = "# type: ignore[attr-defined]"
        
        if ignore_comment in target_line:
            print(f"Skipping {file_path}:{line_number} - ignore comment already present")
            return False
        
        # Add the ignore comment at the end of the line
        # Remove trailing newline, add comment, then add newline back
        lines[line_number - 1] = target_line.rstrip() + f"  {ignore_comment}\n"
        
        # Write the file back
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print(f"Added ignore comment to {file_path}:{line_number}")
        return True
        
    except Exception as e:
        print(f"Error processing {file_path}:{line_number}: {e}")
        return False


def backup_files(file_paths: Set[str]) -> None:
    """Create .bak backups for all files that will be modified."""
    for file_path in file_paths:
        path = Path(file_path)
        if path.exists():
            backup_path = path.with_suffix(path.suffix + '.bak')
            shutil.copy2(path, backup_path)
            print(f"Created backup: {backup_path}")


def main():
    parser = argparse.ArgumentParser(description='Auto-ignore attr-defined MyPy errors')
    parser.add_argument('mypy_file', nargs='?', default='mypy_round3.txt',
                        help='MyPy output file to process (default: mypy_round3.txt)')
    
    args = parser.parse_args()
    
    mypy_file = Path(args.mypy_file)
    if not mypy_file.exists():
        print(f"Error: MyPy output file {mypy_file} does not exist")
        sys.exit(1)
    
    # Parse the MyPy output
    print(f"Parsing MyPy output from {mypy_file}")
    attr_defined_errors = parse_mypy_output(mypy_file)
    
    if not attr_defined_errors:
        print("No attr-defined errors found")
        return
    
    print(f"Found {len(attr_defined_errors)} attr-defined errors")
    
    # Get unique file paths for backup
    unique_files = set(file_path for file_path, _ in attr_defined_errors)
    
    # Create backups
    print(f"Creating backups for {len(unique_files)} files...")
    backup_files(unique_files)
    
    # Process each error
    files_changed = set()
    lines_patched = 0
    
    for file_path, line_number in attr_defined_errors:
        if add_ignore_comment(file_path, line_number):
            files_changed.add(file_path)
            lines_patched += 1
    
    # Print summary
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"Files changed: {len(files_changed)}")
    print(f"Lines patched: {lines_patched}")
    print("\nFiles modified:")
    for file_path in sorted(files_changed):
        print(f"  - {file_path}")


if __name__ == "__main__":
    main()