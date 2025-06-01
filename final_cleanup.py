import os
import re

MYPY_INI = ".mypy.ini"
KOMBU_SECTION = "[mypy-kombu.*]\nignore_missing_imports = True\n"

def remove_unused_ignores_from_file(filepath):
    """Remove unused '# type: ignore' comments from a Python file."""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        # Remove lines that are ONLY "# type: ignore" or "# type: ignore[unused-ignore]"
        if re.match(r"^\s*#\s*type:\s*ignore(\[unused-ignore\])?\s*$", line):
            continue
        # Remove trailing "  # type: ignore[unused-ignore]" or "  # type: ignore" if unused
        new_line = re.sub(r"\s+#\s*type:\s*ignore(\[unused-ignore\])?", "", line)
        new_lines.append(new_line)

    if new_lines != lines:
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

def clean_all_py_files():
    """Clean all Python files in 'src' and 'tests' by removing unused ignore comments."""
    for root, dirs, files in os.walk("src"):
        for file in files:
            if file.endswith(".py"):
                remove_unused_ignores_from_file(os.path.join(root, file))
    for root, dirs, files in os.walk("tests"):
        for file in files:
            if file.endswith(".py"):
                remove_unused_ignores_from_file(os.path.join(root, file))

def ensure_kombu_ignore():
    """Ensure the kombu ignore section exists in the .mypy.ini file."""
    if not os.path.exists(MYPY_INI):
        return
    with open(MYPY_INI, "r", encoding="utf-8") as f:
        content = f.read()
    if "[mypy-kombu.*]" not in content:
        with open(MYPY_INI, "a", encoding="utf-8") as f:
            if not content.endswith("\n"):
                f.write("\n")
            f.write(KOMBU_SECTION)

if __name__ == "__main__":
    clean_all_py_files()
    ensure_kombu_ignore()
    print("Cleanup complete: unused # type: ignore lines removed and kombu ignore section ensured in .mypy.ini.")