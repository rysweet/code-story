# Coding Guidelines (CG)
*(full guidelines: Python PEP 8+type-hints, ESLint rules, docstrings, …)*

### Static Analysis and Testing Commands
- Use `ruff check .` to lint the codebase (avoid deprecated usage like `ruff .`).
- Use `mypy .` for type checking across all modules.
- Run `pytest` to execute unit and integration tests.

### CLI Module Structure
- CLI entrypoint functions must be defined in a dedicated `cli.py` module with a `main()` function.
- Export `main` via `__all__ = ["main"]` in `cli.py` to satisfy static type checkers.
- Ensure `code_story/__main__.py` imports and invokes `main()` so that `poetry run code-story` works correctly.
- Optional: provide a `.pyi` stub file for `cli.py` if needed for type checking.
