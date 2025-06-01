#!/usr/bin/env python3
"""
Auto-annotate return types for functions that implicitly return None.

This script:
1. Recurses through src/ and tests/ directories
2. Uses AST to find functions/async functions that:
   - End without explicit return (implicit None)
   - Have missing or Any return type annotations
3. Adds -> None to such functions
4. Removes lines containing only unused # type: ignore or # noqa comments
5. Creates backups with .bak suffix
6. Prints summary of changes
"""

import ast
import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Set, Tuple


class ReturnTypeAnnotator(ast.NodeTransformer):
    """AST transformer to add -> None annotations to appropriate functions."""
    
    def __init__(self):
        self.functions_modified = 0
        self.modifications: List[Tuple[int, str]] = []  # (lineno, function_name)
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Visit function definitions and add -> None if appropriate."""
        self.generic_visit(node)
        
        if self._should_add_none_annotation(node):
            # Add -> None annotation
            node.returns = ast.Constant(value=None)
            self.functions_modified += 1
            self.modifications.append((node.lineno, node.name))
        
        return node
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        """Visit async function definitions and add -> None if appropriate."""
        self.generic_visit(node)
        
        if self._should_add_none_annotation(node):
            # Add -> None annotation
            node.returns = ast.Constant(value=None)
            self.functions_modified += 1
            self.modifications.append((node.lineno, f"async {node.name}"))
        
        return node
    
    def _should_add_none_annotation(self, node) -> bool:
        """Check if function should get -> None annotation."""
        # Skip if already has return annotation
        if node.returns is not None:
            # Check if it's Any annotation (which we want to replace)
            if isinstance(node.returns, ast.Name) and node.returns.id == "Any":
                pass  # Continue to check if we should replace Any with None
            else:
                return False
        
        # Check if function implicitly returns None
        return self._implicitly_returns_none(node)
    
    def _implicitly_returns_none(self, node) -> bool:
        """Check if function body ends without explicit return."""
        if not node.body:
            return True
        
        # Check the last statement
        last_stmt = node.body[-1]
        
        # If last statement is return without value, it's implicit None
        if isinstance(last_stmt, ast.Return) and last_stmt.value is None:
            return True
        
        # If last statement is not a return, it's implicit None
        if not isinstance(last_stmt, ast.Return):
            return True
        
        # If there's an explicit return with value, don't annotate
        return False


def remove_unused_type_ignores(content: str) -> Tuple[str, int]:
    """Remove lines that contain only # type: ignore or # noqa comments."""
    lines = content.splitlines()
    new_lines = []
    removed_count = 0
    
    for line in lines:
        stripped = line.strip()
        # Check if line contains only whitespace and type ignore/noqa comment
        if (stripped.startswith('# type: ignore') or 
            stripped.startswith('# noqa') or
            re.match(r'^\s*#\s*type:\s*ignore', line) or
            re.match(r'^\s*#\s*noqa', line)):
            # Skip this line (remove it)
            removed_count += 1
            continue
        new_lines.append(line)
    
    return '\n'.join(new_lines), removed_count


def process_python_file(file_path: Path) -> Tuple[int, int]:
    """Process a single Python file. Returns (functions_modified, ignores_removed)."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Parse AST
        try:
            tree = ast.parse(original_content)
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return 0, 0
        
        # Transform AST to add return type annotations
        annotator = ReturnTypeAnnotator()
        new_tree = annotator.visit(tree)
        
        # Convert back to source code
        new_content = ast.unparse(new_tree)
        
        # Remove unused type ignore comments
        new_content, ignores_removed = remove_unused_type_ignores(new_content)
        
        # Only write if there are changes
        if annotator.functions_modified > 0 or ignores_removed > 0:
            # Create backup
            backup_path = file_path.with_suffix('.py.bak')
            shutil.copy2(file_path, backup_path)
            
            # Write modified content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            if annotator.functions_modified > 0:
                print(f"Modified {file_path}: added -> None to {annotator.functions_modified} functions")
                for lineno, func_name in annotator.modifications:
                    print(f"  Line {lineno}: {func_name}")
            
            if ignores_removed > 0:
                print(f"Removed {ignores_removed} unused type ignore comments from {file_path}")
        
        return annotator.functions_modified, ignores_removed
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0, 0


def find_python_files(directories: List[str]) -> List[Path]:
    """Find all Python files in the given directories."""
    python_files = []
    
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"Directory {directory} does not exist, skipping")
            continue
        
        for py_file in dir_path.rglob('*.py'):
            # Skip __pycache__ and other generated directories
            if '__pycache__' in py_file.parts:
                continue
            python_files.append(py_file)
    
    return sorted(python_files)


def main():
    """Main function to process all Python files."""
    print("Auto-annotating return types for functions that implicitly return None...")
    print("=" * 70)
    
    # Find all Python files in src/ and tests/
    directories = ['src', 'tests']
    python_files = find_python_files(directories)
    
    if not python_files:
        print("No Python files found in src/ or tests/ directories")
        return
    
    print(f"Found {len(python_files)} Python files to process")
    print()
    
    total_functions_modified = 0
    total_ignores_removed = 0
    files_modified = 0
    
    for file_path in python_files:
        functions_modified, ignores_removed = process_python_file(file_path)
        
        if functions_modified > 0 or ignores_removed > 0:
            files_modified += 1
        
        total_functions_modified += functions_modified
        total_ignores_removed += ignores_removed
    
    print()
    print("=" * 70)
    print("SUMMARY:")
    print(f"Files processed: {len(python_files)}")
    print(f"Files modified: {files_modified}")
    print(f"Functions annotated with -> None: {total_functions_modified}")
    print(f"Unused type ignore comments removed: {total_ignores_removed}")
    print()
    print("Backup files created with .bak suffix for all modified files")
    print("=" * 70)


if __name__ == '__main__':
    main()