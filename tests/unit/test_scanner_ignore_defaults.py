import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import pytest

from codestory_filesystem.step import get_combined_ignore_spec


def create_test_tree(root: Any) -> None:
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


def walk_files(root: Any, ignore_spec: Any) -> Any:
    result = []
    for dirpath, dirs, files in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        rel_dir_posix = "" if rel_dir == "." else Path(rel_dir).as_posix()
        dirs[:] = [
            d
            for d in dirs
            if not ignore_spec.match_file(os.path.join(rel_dir_posix, d) + "/")
        ]
        for f in files:
            rel_file = os.path.join(rel_dir_posix, f) if rel_dir_posix else f
            if not ignore_spec.match_file(rel_file):
                result.append(rel_file)
    return sorted(result)


def test_builtin_ignore_patterns(tmp_path: Any) -> None:
    create_test_tree(tmp_path)
    ignore_spec = get_combined_ignore_spec(str(tmp_path))
    found = walk_files(str(tmp_path), ignore_spec)
    assert set(found) == {"main.py", "src/keep.py"}


def test_builtin_and_extra_patterns(tmp_path: Any) -> None:
    create_test_tree(tmp_path)
    ignore_spec = get_combined_ignore_spec(str(tmp_path), extra_patterns=["*.py"])
    found = walk_files(str(tmp_path), ignore_spec)
    assert set(found) == set()


def test_builtin_and_gitignore(tmp_path: Any) -> None:
    create_test_tree(tmp_path)
    (Path(tmp_path) / ".gitignore").write_text("src/\n")
    ignore_spec = get_combined_ignore_spec(str(tmp_path))
    found = walk_files(str(tmp_path), ignore_spec)
    assert set(found) == {"main.py"}
