#!/usr/bin/env python3
"""Fix **kwargs type annotations."""
import re
from pathlib import Path


def fix_kwargs_annotations() -> None:
    """Fix **kwargs type annotations in Python files."""
    # Files to fix
    files_to_fix = [
        "src/codestory/graphdb/exceptions.py",
    ]
    
    for file_path in files_to_fix:
        path = Path(file_path)
        if not path.exists():
            continue
            
        with open(path, "r") as f:
            content = f.read()
        
        # Pattern to match untyped **kwargs
        # Look for **kwargs that is NOT followed by : Any
        pattern = r'\*\*kwargs(?!:\s*Any)(?=\s*[,\)])'
        
        # Replace with typed version
        new_content = re.sub(pattern, '**kwargs: Any', content)
        
        if new_content != content:
            with open(path, "w") as f:
                f.write(new_content)
            print(f"Fixed **kwargs in {file_path}")


if __name__ == "__main__":
    fix_kwargs_annotations()
