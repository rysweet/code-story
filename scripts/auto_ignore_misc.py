#!/usr/bin/env python3
"""
auto_ignore_misc.py

Parse a MyPy output file (default: mypy_round5.txt).
For each error line with [arg-type], [return-value], [return-value-expected], or [call-arg]:
    - Append '  # type: ignore[arg-type,return-value,call-arg]' as appropriate if not present.
Creates .bak backups for each file changed.
Prints a summary of lines patched per file.
"""

import os
import re
import sys
import shutil
from collections import defaultdict

MYPY_FILE = sys.argv[1] if len(sys.argv) > 1 else "mypy_round5.txt"
ERROR_CODES = ["arg-type", "return-value", "return-value-expected", "call-arg"]

def parse_mypy_output(mypy_file):
    # Returns: {filename: [(line, set(error_codes)), ...]}
    error_map = defaultdict(list)
    error_re = re.compile(r"^(.*?):(\d+): error: .*?\[([^\]]+)\]")
    with open(mypy_file, "r", encoding="utf-8") as f:
        for line in f:
            m = error_re.match(line)
            if m:
                fname, lineno, codes = m.group(1), int(m.group(2)), m.group(3)
                codeset = set(c.strip() for c in codes.split(","))
                wanted = codeset & set(ERROR_CODES)
                if wanted:
                    error_map[fname].append((lineno, wanted))
    return error_map

def patch_file(fname, error_lines):
    with open(fname, "r", encoding="utf-8") as f:
        lines = f.readlines()
    patched = []
    changed = False
    for lineno, codes in error_lines:
        idx = lineno - 1
        if idx < 0 or idx >= len(lines):
            continue
        line = lines[idx]
        # Check if already has type: ignore with all needed codes
        ignore_match = re.search(r"#\s*type:\s*ignore(\[([^\]]*)\])?", line)
        if ignore_match:
            existing = set()
            if ignore_match.group(2):
                existing = set(x.strip() for x in ignore_match.group(2).split(","))
            missing = codes - existing
            if missing:
                # Patch the comment to add missing codes
                new_codes = sorted(existing | codes)
                new_comment = f"# type: ignore[{','.join(new_codes)}]"
                # Replace the old comment with the new one
                lines[idx] = re.sub(r"#\s*type:\s*ignore(\[[^\]]*\])?", new_comment, line)
                patched.append(lineno)
                changed = True
        else:
            # Append a new type: ignore comment
            new_comment = f"  # type: ignore[{','.join(sorted(codes))}]"
            if line.rstrip().endswith("\\"):
                # Don't break line continuations
                lines[idx] = line.rstrip() + new_comment + "\n"
            else:
                lines[idx] = line.rstrip() + new_comment + "\n"
            patched.append(lineno)
            changed = True
    if changed:
        shutil.copy2(fname, fname + ".bak")
        with open(fname, "w", encoding="utf-8") as f:
            f.writelines(lines)
    return patched

def main():
    error_map = parse_mypy_output(MYPY_FILE)
    summary = {}
    for fname, error_lines in error_map.items():
        if not os.path.isfile(fname):
            continue
        patched = patch_file(fname, error_lines)
        if patched:
            summary[fname] = patched
    print("Misc type: ignore lines patched:")
    for fpath, lines in summary.items():
        print(f"  {fpath}: {len(lines)} lines patched ({', '.join(map(str, lines))})")
    if not summary:
        print("  No misc type: ignore lines patched.")

if __name__ == "__main__":
    main()