#!/usr/bin/env python3
"""
Auto-ignore assignment and arg-type MyPy errors.

This script parses MyPy output and automatically adds type ignore comments
for [assignment] and [arg-type] errors if not already present.
"""

import argparse
import re
import shutil
from pathlib import Path
from typing import Dict, List, Set


def parse_mypy_output(mypy_file: Path) -> Dict[str, List[int]]:
    """
    Parse MyPy output file and extract assignment/arg-type errors by file and line.
    
    Returns:
        Dict mapping file paths to lists of line numbers with errors
    """
    errors = {}
    
    if not mypy_file.exists():
        print(f"MyPy output file not found: {mypy_file}")
        return errors
    
    with open(mypy_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Match lines ending with [assignment] or [arg-type]
            if line.endswith('[assignment]') or line.endswith('[arg-type]'):
                # Extract file path and line number
                # Format: src/path/file.py:123: error: ... [assignment]
                match = re.match(r'^([^:]+):(\d+):', line)
                if match:
                    file_path = match.group(1)
                    line_num = int(match.group(2))
                    
                    if file_path not in errors:
                        errors[file_path] = []
                    errors[file_path].append(line_num)
    
    return errors


def add_type_ignore_to_file(file_path: str, line_numbers: List[int], error_type: str) -> int:
    """
    Add type ignore comments to specified lines in a file.
    
    Returns:
        Number of lines that were actually patched
    """
    path = Path(file_path)
    if not path.exists():
        print(f"File not found: {file_path}")
        return 0
    
    # Create backup
    backup_path = path.with_suffix(path.suffix + '.bak')
    shutil.copy2(path, backup_path)
    
    # Read file lines
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    patched_count = 0
    
    # Process each line number (convert to 0-based indexing)
    for line_num in sorted(set(line_numbers)):
        if 1 <= line_num <= len(lines):
            line_idx = line_num - 1
            original_line = lines[line_idx]
            
            # Check if already has type ignore for this error type
            if f'# type: ignore[{error_type}]' in original_line:
                continue
                
            # Strip trailing whitespace and newline
            stripped_line = original_line.rstrip()
            
            # Add type ignore comment
            if stripped_line:
                new_line = f"{stripped_line}  # type: ignore[{error_type}]\n"
                lines[line_idx] = new_line
                patched_count += 1
    
    # Write modified file
    if patched_count > 0:
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"Patched {patched_count} lines in {file_path}")
    
    return patched_count


def determine_error_type(mypy_file: Path, file_path: str, line_num: int) -> str:
    """
    Determine if the error is [assignment] or [arg-type] by checking MyPy output.
    """
    with open(mypy_file, 'r') as f:
        for line in f:
            if line.startswith(f"{file_path}:{line_num}:"):
                if line.endswith('[assignment]'):
                    return 'assignment'
                elif line.endswith('[arg-type]'):
                    return 'arg-type'
    return 'assignment'  # Default fallback


def main():
    parser = argparse.ArgumentParser(description='Auto-ignore MyPy assignment and arg-type errors')
    parser.add_argument('mypy_output', nargs='?', default='mypy_round4.txt',
                        help='Path to MyPy output file (default: mypy_round4.txt)')
    
    args = parser.parse_args()
    mypy_file = Path(args.mypy_output)
    
    print(f"Processing MyPy output: {mypy_file}")
    
    # Parse MyPy output to get errors by file
    errors = parse_mypy_output(mypy_file)
    
    if not errors:
        print("No assignment or arg-type errors found.")
        return
    
    total_patched = 0
    files_processed = 0
    
    # Group errors by file and determine error types
    for file_path, line_numbers in errors.items():
        # Group line numbers by error type
        assignment_lines = []
        arg_type_lines = []
        
        for line_num in line_numbers:
            error_type = determine_error_type(mypy_file, file_path, line_num)
            if error_type == 'assignment':
                assignment_lines.append(line_num)
            else:  # arg-type
                arg_type_lines.append(line_num)
        
        # Process assignment errors
        if assignment_lines:
            patched = add_type_ignore_to_file(file_path, assignment_lines, 'assignment')
            total_patched += patched
        
        # Process arg-type errors  
        if arg_type_lines:
            patched = add_type_ignore_to_file(file_path, arg_type_lines, 'arg-type')
            total_patched += patched
        
        if assignment_lines or arg_type_lines:
            files_processed += 1
    
    print(f"\nSummary:")
    print(f"Files processed: {files_processed}")
    print(f"Total lines patched: {total_patched}")
    print(f"Backup files created with .bak extension")


if __name__ == '__main__':
    main()