# Using uv for Python Environment and Package Management

This project now supports [uv](https://github.com/astral-sh/uv) for fast, modern Python package and virtual environment management.

## Why uv?
- Much faster dependency resolution and installation than pip/pip-tools
- Simple, single-binary tool for venv, install, and dependency management
- Compatible with pyproject.toml and requirements.txt

## Getting Started

### 1. Install uv

Download from https://github.com/astral-sh/uv#installation or use:

```
# On Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```

Or use Homebrew, Scoop, or download a release binary.

### 2. Create a Virtual Environment

```
uv venv .venv
```

### 3. Install Dependencies

```
uv pip install -r requirements.txt
```

Or install directly from pyproject.toml:

```
uv pip install -r pyproject.toml
```

### 4. Add/Update Dependencies

- To add a package:
  ```
  uv pip install <package>
  ```
- To update all:
  ```
  uv pip install -U -r requirements.txt
  ```
- To recompile requirements.txt from pyproject.toml:
  ```
  uv pip compile --all-extras --output-file=requirements.txt pyproject.toml
  ```

### 5. Run Project

Activate the venv and use as normal:

```
.venv\Scripts\Activate.ps1  # Windows PowerShell
source .venv/bin/activate    # Linux/macOS
```

## Notes
- `uv` is fully compatible with pip and venv workflows.
- You can continue to use Poetry or pip if desired, but `uv` is recommended for speed and simplicity.
- See https://github.com/astral-sh/uv for full documentation.
