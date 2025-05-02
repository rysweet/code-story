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

### Repository Setup
- Add a `.gitignore` at the root to exclude Python caches, virtualenvs, Node modules, IDE files, etc.
- Configure editor settings via `.editorconfig` for consistent formatting.
- Add linter and formatter configs: `.ruff.toml`, `mypy.ini`, `.eslintrc.json`, `.prettierrc`.
- Set up a `pre-commit` hook configuration to run `ruff check .`, `mypy .`, and `pytest` before commits.

### Docker Compose Improvements
- Use a Dockerfile for the `backend` service that installs Poetry and dependencies, instead of mounting the host volume directly.
- Ensure services restart policies and health checks are configured.
