import os
import tempfile
import shutil
from pathlib import Path

import pytest

from codestory_filesystem.step import get_combined_ignore_spec

def create_test_tree(root):
    # Create files and directories
    (Path(root) / "main.py").write_text("# main")
    (Path(root) / "notes.log").write_text("log")
    (Path(root) / "build").mkdir()
    (Path(root) / "build" / "artifact.txt").write_text("artifact")
    (Path(root) / "__pycache__").mkdir()
    (Path(root) / "__pycache__" / "foo.pyc").write_text("pyc")
    (Path(root) / ".git").mkdir()
    (Path(root) / ".git" / "config").write_text("config")
    (Path(root) / "src").mkdir()
    (Path(root) / "src" / "keep.py").write_text("# keep")

def walk_files(root, ignore_spec):
    # Return all files not ignored by the spec, relative to root
    result = []
    for dirpath, dirs, files in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        rel_dir_posix = "" if rel_dir == "." else Path(rel_dir).as_posix()
        # Filter dirs in-place
        dirs[:] = [d for d in dirs if not ignore_spec.match_file(os.path.join(rel_dir_posix, d) + "/")]
        for f in files:
            rel_file = os.path.join(rel_dir_posix, f) if rel_dir_posix else f
            if not ignore_spec.match_file(rel_file):
                result.append(rel_file)
    return sorted(result)

def test_builtin_ignore_patterns(tmp_path):
    create_test_tree(tmp_path)
    ignore_spec = get_combined_ignore_spec(str(tmp_path))
    found = walk_files(str(tmp_path), ignore_spec)
    # Only main.py and src/keep.py should be present
    assert set(found) == {"main.py", "src/keep.py"}

def test_builtin_and_extra_patterns(tmp_path):
    create_test_tree(tmp_path)
    # Add extra ignore for *.py
    ignore_spec = get_combined_ignore_spec(str(tmp_path), extra_patterns=["*.py"])
    found = walk_files(str(tmp_path), ignore_spec)
    # Only src/keep.py and main.py should now be ignored as well
    assert set(found) == set()

def test_builtin_and_gitignore(tmp_path):
    create_test_tree(tmp_path)
    # Add a .gitignore that ignores src/
    (Path(tmp_path) / ".gitignore").write_text("src/\n")
    ignore_spec = get_combined_ignore_spec(str(tmp_path))
    found = walk_files(str(tmp_path), ignore_spec)
    # Only main.py should be present
    assert set(found) == {"main.py"}