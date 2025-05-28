#!/usr/bin/env python3
"""
Script to systematically fix mypy type annotation errors.
"""

import os
import re
import subprocess
from pathlib import Path


class MypyErrorFixer:
    def __init__(self, src_dir: str) -> None:
        self.src_dir = Path(src_dir)

    def run_mypy(self) -> list[str]:
        """Run mypy and return list of error lines."""
        try:
            result = subprocess.run(
                ["mypy", str(self.src_dir), "--show-error-codes"],
                capture_output=True,
                text=True,
                check=False
            )
            return result.stdout.split('\n')
        except Exception as e:
            print(f"Error running mypy: {e}")
            return []

    def parse_errors(self, error_lines: list[str]) -> dict[str, list[tuple[int, str, str]]]:
        """Parse mypy errors into file -> [(line_num, error_type, message)]."""
        errors_by_file: dict[str, list[tuple[int, str, str]]] = {}

        for line in error_lines:
            if not line.strip() or ': error:' not in line:
                continue

            # Pattern: src/path/file.py:123: error: Message [error-code]
            match = re.match(r'^([^:]+):(\d+): error: (.+?) \[([^\]]+)\]', line)
            if match:
                file_path, line_num, message, error_code = match.groups()
                if file_path not in errors_by_file:
                    errors_by_file[file_path] = []
                errors_by_file[file_path].append((int(line_num), error_code, message))

        return errors_by_file
    
    def install_missing_stubs(self) -> None:
        """Install missing stub packages."""
        stubs_to_install = [
            "types-PyYAML",
            "types-setuptools",
            "types-docker"
        ]

        for stub in stubs_to_install:
            try:
                subprocess.run(["pip", "install", stub], check=True)
                print(f"Installed {stub}")
            except subprocess.CalledProcessError:
                print(f"Failed to install {stub}")
    
    def fix_no_untyped_def_errors(self, file_path: str, errors: list[tuple[int, str, str]]) -> None:
        """Fix no-untyped-def errors by adding type annotations."""
        try:
            with open(file_path, encoding='utf-8') as f:
                lines = f.readlines()
            
            modified = False
            
            for line_num, error_code, message in errors:
                if error_code != 'no-untyped-def':
                    continue
                    
                line_idx = line_num - 1
                if line_idx >= len(lines):
                    continue
                    
                line = lines[line_idx]
                
                # Add return type annotations
                if (
                    "Function is missing a return type annotation" in message
                    and "-> None" in message
                ):
                    # Functions that should return None
                    if re.search(r'def\s+\w+\s*\([^)]*\)\s*:', line):
                        lines[line_idx] = re.sub(
                            r'(\s*def\s+\w+\s*\([^)]*\))\s*:', r'\1 -> None:', line
                        )
                        modified = True
                elif "Function is missing a return type annotation" in message:
                    # Other functions - add basic typing
                    if re.search(r'def\s+\w+\s*\([^)]*\)\s*:', line):
                        # For now, just add Any return type
                        lines[line_idx] = re.sub(
                            r'(\s*def\s+\w+\s*\([^)]*\))\s*:', r'\1 -> Any:', line
                        )
                        modified = True
                elif "Function is missing a type annotation for one or more arguments" in message:
                    # Add parameter type annotations
                    if re.search(r'def\s+\w+\s*\([^)]*\)\s*:', line):
                        # For now, add Any to untyped parameters - this is conservative
                        # More sophisticated logic would parse the function signature
                        pass
            
            # Add necessary imports if we modified the file
            if modified:
                # Check if Any import is needed and add it
                content = ''.join(lines)
                if (
                    'Any' in content
                    and 'from typing import' not in content
                    and 'import typing' not in content
                ):
                    # Find the best place to add the import
                    import_added = False
                    for i, line in enumerate(lines):
                        if line.startswith('from typing import'):
                            # Add Any to existing typing import
                            if 'Any' not in line:
                                lines[i] = line.rstrip() + ', Any\n'
                                import_added = True
                                break
                        elif line.startswith('import') and not import_added:
                            # Add new typing import after other imports
                            continue
                    
                    if not import_added:
                        # Find the first import line
                        for i, line in enumerate(lines):
                            if line.startswith('import') or line.startswith('from'):
                                lines.insert(i, 'from typing import Any\n')
                                break
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print(f"Fixed function annotations in {file_path}")
                
        except Exception as e:
            print(f"Error fixing {file_path}: {e}")
    
    def fix_var_annotated_errors(self, file_path: str, errors: list[tuple[int, str, str]]) -> None:
        """Fix var-annotated errors by adding type hints."""
        try:
            with open(file_path, encoding='utf-8') as f:
                lines = f.readlines()
            
            modified = False
            
            for line_num, error_code, message in errors:
                if error_code != 'var-annotated':
                    continue
                    
                line_idx = line_num - 1
                if line_idx >= len(lines):
                    continue
                    
                line = lines[line_idx]
                
                # Extract variable name from error message
                var_match = re.search(r'Need type annotation for "([^"]+)"', message)
                if var_match:
                    var_name = var_match.group(1)
                    
                    # Add type hint based on the suggestion in the error
                    if 'list[<type>]' in message:
                        lines[line_idx] = re.sub(
                            rf'(\s*{re.escape(var_name)}\s*=)',
                            rf'{var_name}: list[Any] =',
                            line
                        )
                        modified = True
                    elif 'dict[<type>, <type>]' in message:
                        lines[line_idx] = re.sub(
                            rf'(\s*{re.escape(var_name)}\s*=)',
                            rf'{var_name}: dict[Any, Any] =',
                            line
                        )
                        modified = True
                    elif '__all__' in var_name:
                        lines[line_idx] = re.sub(
                            r'(__all__\s*=)', r'__all__: list[str] =', line
                        )
                        modified = True
            
            if modified:
                # Add Any import if needed
                content = ''.join(lines)
                if (
                    'Any' in content
                    and 'from typing import' not in content
                    and 'import typing' not in content
                ):
                    # Add import
                    for i, line in enumerate(lines):
                        if line.startswith('from typing import'):
                            if 'Any' not in line:
                                lines[i] = line.rstrip() + ', Any\n'
                                break
                        elif line.startswith('import') or line.startswith('from'):
                            continue
                        else:
                            lines.insert(i, 'from typing import Any\n')
                            break
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print(f"Fixed variable annotations in {file_path}")
                
        except Exception as e:
            print(f"Error fixing {file_path}: {e}")

    def fix_import_untyped_errors(self, file_path: str, errors: list[tuple[int, str, str]]) -> None:
        """Fix import-untyped errors by adding type: ignore comments."""
        try:
            with open(file_path, encoding='utf-8') as f:
                lines = f.readlines()
            
            modified = False
            
            for line_num, error_code, message in errors:
                if error_code != 'import-untyped':
                    continue
                    
                line_idx = line_num - 1
                if line_idx >= len(lines):
                    continue
                    
                line = lines[line_idx]
                
                # Add type: ignore comment if not already present
                if '# type: ignore' not in line:
                    lines[line_idx] = line.rstrip() + '  # type: ignore[import-untyped]\n'
                    modified = True
            
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print(f"Fixed import annotations in {file_path}")
                
        except Exception as e:
            print(f"Error fixing {file_path}: {e}")

    def fix_simple_issues(self, file_path: str, errors: list[tuple[int, str, str]]) -> None:
        """Fix simple/obvious type issues."""
        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Fix specific patterns
            
            # Fix callable type annotation
            content = re.sub(
                r':\s*callable\s*\?',
                ': Callable[..., Any] | None',
                content,
                flags=re.IGNORECASE
            )
            
            # Fix uuid issues
            if 'uuid' in content and 'import uuid' not in content:
                # Add uuid import
                import_lines = []
                other_lines = []
                for line in content.split('\n'):
                    if line.startswith('import ') or line.startswith('from '):
                        import_lines.append(line)
                    else:
                        other_lines.append(line)
                
                import_lines.append('import uuid')
                content = '\n'.join(import_lines + other_lines)
            
            # Fix name-defined issues for uuid
            content = re.sub(r'\buuid\b(?=\s*\.\s*uuid4)', 'uuid.uuid4', content)
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Fixed simple issues in {file_path}")
                
        except Exception as e:
            print(f"Error fixing {file_path}: {e}")

    def run_fixes(self) -> None:
        """Run all fixes systematically."""
        print("Installing missing stub packages...")
        self.install_missing_stubs()
        
        print("\nRunning mypy to get current errors...")
        error_lines = self.run_mypy()
        errors_by_file: dict[str, list[tuple[int, str, str]]] = self.parse_errors(error_lines)
        
        print(f"Found errors in {len(errors_by_file)} files")
        
        # Prioritize fixes by error type
        error_type_counts: dict[str, int] = {}
        for file_errors in errors_by_file.values():
            for _, error_code, _ in file_errors:
                error_type_counts[error_code] = error_type_counts.get(error_code, 0) + 1
        
        print("\nError counts by type:")
        for error_code, count in sorted(
            error_type_counts.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  {error_code}: {count}")
        
        # Fix errors by priority
        for file_path, file_errors in errors_by_file.items():
            if not os.path.exists(file_path):
                continue
                
            print(f"\nFixing {file_path}...")
            
            # Fix in order of priority
            self.fix_import_untyped_errors(file_path, file_errors)
            self.fix_var_annotated_errors(file_path, file_errors)
            self.fix_simple_issues(file_path, file_errors)
            self.fix_no_untyped_def_errors(file_path, file_errors)

if __name__ == "__main__":
    fixer = MypyErrorFixer("src")
    fixer.run_fixes()
