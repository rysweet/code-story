#!/usr/bin/env python3
"""
auto_remove_unused_ignores.py

Walks src/ and tests/ directories.
Deletes any line that is ONLY an unused comment:
    # type: ignore[...] (any variant)
    # noqa
    # pylint: (any variant)
with nothing else on the line (ignores whitespace).
Creates .bak backups for each file changed.
Prints a summary of lines removed per file.
"""

import os
import re
import shutil

TARGET_DIRS = ["src", "tests"]
IGNORE_PATTERNS = [
    r"^\s*#\s*type:\s*ignore(\[.*\])?\s*$",
    r"^\s*#\s*noqa\s*$",
    r"^\s*#\s*pylint:.*$"
]

def is_unused_ignore(line):
    for pat in IGNORE_PATTERNS:
        if re.match(pat, line):
            return True
    return False

def process_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    removed = []
    new_lines = []
    for i, line in enumerate(lines):
        if is_unused_ignore(line):
            removed.append(i + 1)
        else:
            new_lines.append(line)
    if removed:
        shutil.copy2(filepath, filepath + ".bak")
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    return removed

def main():
    summary = {}
    for root_dir in TARGET_DIRS:
        for dirpath, _, filenames in os.walk(root_dir):
            for fname in filenames:
                if fname.endswith(".py"):
                    fpath = os.path.join(dirpath, fname)
                    removed = process_file(fpath)
                    if removed:
                        summary[fpath] = removed
    print("Unused ignore lines removed:")
    for fpath, lines in summary.items():
        print(f"  {fpath}: {len(lines)} lines removed ({', '.join(map(str, lines))})")
    if not summary:
        print("  No unused ignore lines found.")

if __name__ == "__main__":
    main()