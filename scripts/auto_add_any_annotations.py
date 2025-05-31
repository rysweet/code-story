#!/usr/bin/env python3
"""
Auto-add Any annotations to functions missing type hints.

This script walks through src/ and tests/ directories, finds functions with
un-annotated parameters or missing return types, and adds ": Any" annotations
to parameters and "-> Any" to return types where appropriate.
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Set, Tuple


class AnyAnnotationTransformer(ast.NodeTransformer):
    """AST transformer to add Any annotations to functions."""
    
    def __init__(self):
        self.functions_modified = 0
        self.needs_any_import = False
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Visit function definitions and add Any annotations where missing."""
        return self._process_function(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        """Visit async function definitions and add Any annotations where missing."""
        return self._process_function(node)
    
    def _process_function(self, node):
        """Process a function node to add missing Any annotations."""
        modified = False
        
        # Check if function already has concrete annotations
        if self._has_concrete_annotations(node):
            return node
        
        # Process arguments
        for arg in node.args.args:
            if arg.annotation is None:
                arg.annotation = ast.Name(id='Any', ctx=ast.Load())
                modified = True
                self.needs_any_import = True
        
        # Process keyword-only arguments
        for arg in node.args.kwonlyargs:
            if arg.annotation is None:
                arg.annotation = ast.Name(id='Any', ctx=ast.Load())
                modified = True
                self.needs_any_import = True
        
        # Process varargs (*args)
        if node.args.vararg and node.args.vararg.annotation is None:
            node.args.vararg.annotation = ast.Name(id='Any', ctx=ast.Load())
            modified = True
            self.needs_any_import = True
        
        # Process kwargs (**kwargs)
        if node.args.kwarg and node.args.kwarg.annotation is None:
            node.args.kwarg.annotation = ast.Name(id='Any', ctx=ast.Load())
            modified = True
            self.needs_any_import = True
        
        # Process return type
        if node.returns is None:
            node.returns = ast.Name(id='Any', ctx=ast.Load())
            modified = True
            self.needs_any_import = True
        
        if modified:
            self.functions_modified += 1
        
        return node
    
    def _has_concrete_annotations(self, node) -> bool:
        """Check if function already has concrete (non-Any) annotations."""
        # Check if all parameters have annotations and return type exists
        all_args = (
            node.args.args + 
            node.args.kwonlyargs + 
            ([node.args.vararg] if node.args.vararg else []) +
            ([node.args.kwarg] if node.args.kwarg else [])
        )
        
        # If any parameter lacks annotation, it's not fully annotated
        for arg in all_args:
            if arg.annotation is None:
                return False
        
        # If return type is missing, it's not fully annotated
        if node.returns is None:
            return False
        
        # Function is fully annotated, skip it
        return True


class ImportTransformer(ast.NodeTransformer):
    """AST transformer to ensure Any is imported from typing."""
    
    def __init__(self):
        self.has_any_import = False
        self.has_typing_import = False
        self.typing_import_node = None
        self.import_added = False
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom:
        """Check for existing typing imports."""
        if node.module == 'typing':
            self.has_typing_import = True
            self.typing_import_node = node
            
            # Check if Any is already imported
            for alias in node.names:
                if alias.name == 'Any':
                    self.has_any_import = True
                    break
            
            # If Any is not imported, add it
            if not self.has_any_import:
                node.names.append(ast.alias(name='Any', asname=None))
                self.has_any_import = True
                self.import_added = True
        
        return node
    
    def add_any_import(self, tree: ast.Module) -> ast.Module:
        """Add Any import if needed and not already present."""
        if self.has_any_import:
            return tree
        
        if self.has_typing_import and not self.import_added:
            # Any import was added to existing typing import
            return tree
        
        if not self.has_typing_import:
            # Add new typing import
            import_node = ast.ImportFrom(
                module='typing',
                names=[ast.alias(name='Any', asname=None)],
                level=0
            )
            
            # Insert after any existing imports
            insert_pos = 0
            for i, node in enumerate(tree.body):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    insert_pos = i + 1
                else:
                    break
            
            tree.body.insert(insert_pos, import_node)
        
        return tree


def process_file(file_path: Path) -> Tuple[bool, int]:
    """
    Process a single Python file to add Any annotations.
    
    Returns:
        Tuple of (file_modified, functions_modified)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return False, 0
        
        # Transform functions
        function_transformer = AnyAnnotationTransformer()
        tree = function_transformer.visit(tree)
        
        # Handle imports if Any annotations were added
        if function_transformer.needs_any_import:
            import_transformer = ImportTransformer()
            tree = import_transformer.visit(tree)
            tree = import_transformer.add_any_import(tree)
        
        # If no modifications were made, skip writing
        if function_transformer.functions_modified == 0:
            return False, 0
        
        # Create backup
        backup_path = file_path.with_suffix(file_path.suffix + '.bak')
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Write modified content
        modified_content = ast.unparse(tree)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        return True, function_transformer.functions_modified
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, 0


def find_python_files(directories: List[str]) -> List[Path]:
    """Find all Python files in the given directories."""
    python_files = []
    
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"Directory {directory} does not exist, skipping...")
            continue
        
        for py_file in dir_path.rglob('*.py'):
            if py_file.is_file():
                python_files.append(py_file)
    
    return python_files


def main():
    """Main function to process all Python files."""
    print("Auto-adding Any annotations to functions with missing type hints...")
    
    # Process src/ and tests/ directories
    directories = ['src', 'tests']
    python_files = find_python_files(directories)
    
    if not python_files:
        print("No Python files found in src/ and tests/")
        return
    
    print(f"Found {len(python_files)} Python files to process...")
    
    total_files_modified = 0
    total_functions_modified = 0
    
    for file_path in python_files:
        file_modified, functions_modified = process_file(file_path)
        
        if file_modified:
            total_files_modified += 1
            total_functions_modified += functions_modified
            print(f"  {file_path}: {functions_modified} functions annotated")
    
    print(f"\nSummary:")
    print(f"  Files modified: {total_files_modified}")
    print(f"  Functions annotated: {total_functions_modified}")
    print(f"  Backup files created with .bak extension")


if __name__ == '__main__':
    main()