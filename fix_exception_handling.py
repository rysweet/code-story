#!/usr/bin/env python3
"""Script to automatically fix B904 exception handling issues.

Adds 'from err' or 'from None' to raise statements in except blocks.
"""

import re
import subprocess
from pathlib import Path


def get_b904_issues():
    """Get all B904 issues from ruff."""
    try:
        result = subprocess.run(
            ["ruff", "check", ".", "--select", "B904"],
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )
        
        issues = []
        for line in result.stdout.strip().split('\n'):
            if line and ':' in line:
                parts = line.split(':')
                if len(parts) >= 3:
                    file_path = parts[0]
                    line_num = int(parts[1])
                    issues.append((file_path, line_num))
        
        return issues
    except Exception as e:
        print(f"Error getting B904 issues: {e}")
        return []


def fix_exception_handling(file_path: str, line_num: int):
    """Fix a specific B904 issue in a file."""
    try:
        with open(file_path) as f:
            lines = f.readlines()
        
        if line_num > len(lines):
            print(f"Line {line_num} out of range in {file_path}")
            return False
        
        line = lines[line_num - 1]  # Convert to 0-based index
        
        # Check if this is a raise statement that needs fixing
        if 'raise ' in line and ' from ' not in line:
            # Look backwards to find the except clause
            except_var = None
            for i in range(line_num - 2, max(0, line_num - 20), -1):
                except_line = lines[i].strip()
                if except_line.startswith('except '):
                    # Extract variable name from except clause
                    match = re.search(r'except\s+[^:]+?\s+as\s+(\w+):', except_line)
                    if match:
                        except_var = match.group(1)
                    break
                elif (except_line.startswith('try:') or not except_line 
                      or except_line.startswith('#')):
                    continue
                elif 'except' in except_line:
                    break
            
            # Fix the raise statement
            if except_var and f'{except_var}' in line:
                # Add 'from err' where err is the exception variable
                fixed_line = line.rstrip() + f' from {except_var}\n'
            else:
                # Add 'from None' for generic cases
                fixed_line = line.rstrip() + ' from None\n'
            
            lines[line_num - 1] = fixed_line
            
            with open(file_path, 'w') as f:
                f.writelines(lines)
            
            print(f"Fixed {file_path}:{line_num}")
            return True
    
    except Exception as e:
        print(f"Error fixing {file_path}:{line_num}: {e}")
        return False


def main():
    """Main function to fix all B904 issues."""
    print("Finding B904 exception handling issues...")
    issues = get_b904_issues()
    
    if not issues:
        print("No B904 issues found!")
        return
    
    print(f"Found {len(issues)} B904 issues")
    
    fixed_count = 0
    for file_path, line_num in issues:
        if fix_exception_handling(file_path, line_num):
            fixed_count += 1
    
    print(f"Fixed {fixed_count} out of {len(issues)} issues")
    
    # Check remaining issues
    remaining = get_b904_issues()
    print(f"Remaining B904 issues: {len(remaining)}")


if __name__ == "__main__":
    main()
