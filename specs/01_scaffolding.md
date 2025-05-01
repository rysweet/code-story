## 00 Scaffolding (P0)
*(full content from canvas – purpose, layout, toolchain, MIT license, …)*

### Python project setup
- Use Poetry to initialize project with `poetry init`.
- Declare runtime dependencies under `[tool.poetry.dependencies]`.
- **Declare dev dependencies under `tool.poetry.group.dev.dependencies`** (e.g. ruff, mypy, pytest) instead of the deprecated `tool.poetry.dev-dependencies`.

### CLI entrypoint
- Add `[tool.poetry.scripts]` section to expose the CLI (e.g. `code-story = "code_story.cli:main"`).
- Ensure `code_story/cli.py` defines `main()`, and package entrypoint imports `main` in `__init__.py` or provides a stub (`.pyi`) for static type checkers.

### Node workspace setup
...existing content...
