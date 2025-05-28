#!/usr/bin/env python3
"""Advanced MyPy error fixing script - Phase 2."""

import re
import subprocess
from pathlib import Path


def run_mypy() -> str:
    """Run mypy and return output."""
    result = subprocess.run(
        ["poetry", "run", "mypy", "src/"],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
    )
    return result.stdout


def fix_uuid_imports(content: str, file_path: str) -> str:
    """Fix UUID import issues."""
    if "uuid4" in content and "import uuid" not in content:
        lines = content.splitlines()
        # Find the first import section
        import_index = 0
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                import_index = i
                break
        
        # Insert UUID import after the last import
        for i in range(import_index, len(lines)):
            if not (
                lines[i].startswith("import ") or lines[i].startswith("from ") 
                or lines[i].strip() == ""
            ):
                lines.insert(i, "import uuid")
                break
        
        # Replace uuid4() with uuid.uuid4()
        content = "\n".join(lines)
        content = re.sub(r'\buuid4\(\)', 'uuid.uuid4()', content)
    
    return content


def fix_callable_imports(content: str, file_path: str) -> str:
    """Fix Callable import issues."""
    if "Callable[" in content and "from typing import" in content:
        # Add Callable to existing typing imports
        content = re.sub(
            r'from typing import ([^)]+)',
            lambda m: (
                f'from typing import {m.group(1)}, Callable' 
                if 'Callable' not in m.group(1) 
                else m.group(0)
            ),
            content
        )
    elif "callable?" in content:
        # Replace callable? with Callable
        content = content.replace("callable?", "Callable[..., Any]")
        if "from typing import" in content:
            content = re.sub(
                r'from typing import ([^)]+)',
                lambda m: (
                    f'from typing import {m.group(1)}, Callable' 
                    if 'Callable' not in m.group(1) 
                    else m.group(0)
                ),
                content
            )
    
    return content


def fix_return_type_annotations(content: str, file_path: str) -> str:
    """Fix missing return type annotations."""
    lines = content.splitlines()
    new_lines = []
    
    for i, line in enumerate(lines):
        # Look for function definitions without return types
        if re.match(r'\s*def\s+\w+\([^)]*\):\s*$', line) and not line.strip().startswith('def __'):
            # Add -> None if it's likely a procedure
            if (i + 1 < len(lines) and 
                ('"""' in lines[i + 1] or 'return' not in ''.join(lines[i:i+10]))):
                line = line.replace(':', ' -> None:')
            else:
                line = line.replace(':', ' -> Any:')
        
        new_lines.append(line)
    
    return '\n'.join(new_lines)


def fix_variable_annotations(content: str, file_path: str) -> str:
    """Fix missing variable annotations."""
    # Fix common patterns
    fixes = [
        (r'^(\s*)([a-zA-Z_]\w*)\s*=\s*\[\]$', r'\1\2: list[Any] = []'),
        (r'^(\s*)([a-zA-Z_]\w*)\s*=\s*\{\}$', r'\1\2: dict[Any, Any] = {}'),
        (r'^(\s*)([a-zA-Z_]\w*)\s*=\s*set\(\)$', r'\1\2: set[Any] = set()'),
    ]
    
    for pattern, replacement in fixes:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    return content


def fix_specific_errors(content: str, file_path: str) -> str:
    """Fix specific mypy errors by file."""
    # Fix settings files - missing arguments
    if "settings.py" in file_path:
        # Add **kwargs to constructors that are missing arguments
        if "Missing named argument" in content:
            content = re.sub(
                r'(\w+Settings\()([^)]*)\)',
                r'\1**config.model_dump()\2)',
                content
            )
    
    # Fix SecretStr issues
    if "SecretStr" in content and "str | None" in content:
        content = re.sub(
            r'SecretStr\(([^)]+)\)',
            r'SecretStr(\1) if \1 is not None else None',
            content
        )
    
    # Fix frozenset indexing
    if "frozenset" in content:
        content = re.sub(
            r'(\w+)\.labels\[0\]',
            r'list(\1.labels)[0]',
            content
        )
    
    # Fix dict unpacking
    if "**dict[str," in content:
        content = content.replace("**dict[str,", "**{k: v for k, v in dict[str,")
    
    return content


def add_missing_imports(content: str, file_path: str) -> str:
    """Add missing imports based on usage."""
    imports_to_add = []
    
    # Check for Any usage
    if (": Any" in content or "-> Any" in content or 
        "list[Any]" in content or "dict[Any, Any]" in content):
        if "from typing import" in content:
            if "Any" not in content:
                imports_to_add.append("Any")
        else:
            imports_to_add.append("Any")
    
    # Check for Callable usage
    if "Callable[" in content and "Callable" not in content:
        imports_to_add.append("Callable")
    
    # Add imports
    if imports_to_add:
        lines = content.splitlines()
        
        # Find existing typing imports
        typing_line_idx = None
        for i, line in enumerate(lines):
            if line.startswith("from typing import"):
                typing_line_idx = i
                break
        
        if typing_line_idx is not None:
            # Add to existing import
            current_imports = lines[typing_line_idx]
            for imp in imports_to_add:
                if imp not in current_imports:
                    current_imports = current_imports.replace("import ", f"import {imp}, ")
            lines[typing_line_idx] = current_imports
        else:
            # Add new import line
            import_line = f"from typing import {', '.join(imports_to_add)}"
            # Find where to insert (after other imports)
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith(("import ", "from ")) or line.strip() == "":
                    insert_idx = i + 1
                else:
                    break
            lines.insert(insert_idx, import_line)
        
        content = "\n".join(lines)
    
    return content


def main() -> None:
    """Main function."""
    print("Running advanced mypy error fixes...")
    
    # Get mypy output
    mypy_output = run_mypy()
    if not mypy_output:
        print("No mypy errors found!")
        return
    
    # Parse errors
    error_files = set()
    for line in mypy_output.splitlines():
        if ": error:" in line:
            file_path = line.split(":")[0]
            error_files.add(file_path)
    
    print(f"Found errors in {len(error_files)} files")
    
    # Process each file
    for file_path in sorted(error_files):
        if not Path(file_path).exists():
            continue
            
        print(f"Processing {file_path}")
        
        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Apply fixes
            content = fix_uuid_imports(content, file_path)
            content = fix_callable_imports(content, file_path)
            content = fix_return_type_annotations(content, file_path)
            content = fix_variable_annotations(content, file_path)
            content = fix_specific_errors(content, file_path)
            content = add_missing_imports(content, file_path)
            
            # Write back if changed
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  Updated {file_path}")
            
        except Exception as e:
            print(f"  Error processing {file_path}: {e}")
    
    print("Done!")


if __name__ == "__main__":
    main()
