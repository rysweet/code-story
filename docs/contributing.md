# Contributing

Thank you for your interest in contributing to CodeStory! This guide covers development setup, testing, documentation, and CI expectations.

## Development Setup

1. **Clone the repository** and install dependencies using [uv](https://github.com/astral-sh/uv):
   ```sh
   uv pip install -r requirements.txt
   ```

2. **Set up your environment variables**:
   - Copy `.env.example` to `.env` and edit as needed.
   - Never commit real secrets or credentials.

## Pre-commit Hooks

CodeStory uses [pre-commit](https://pre-commit.com/) to enforce code quality and documentation standards. Hooks include:
- `ruff` (lint/fix)
- `black` (format)
- Large file check
- `mkdocs build` (strict, fail on warnings)
- `mkdocs linkcheck` (check documentation links)

**Run all hooks before committing:**
```sh
uv run pre-commit run --all-files
```

## Running Tests

All tests must pass before merging. Use:
```sh
uv run pytest
```

Tests are self-contained and use fixtures for dependencies. Do not hardcode secrets; use environment variables.

## Building Documentation

To build and check documentation locally:
```sh
uv run mkdocs build --strict
uv run mkdocs linkcheck
```

## Continuous Integration

All code and documentation changes are validated by CI:
- Linting, formatting, and tests must pass
- Documentation must build without warnings
- Broken links will fail the build

## Writing Docs

- Edit Markdown files in `docs/`
- Reference code and configuration accurately
- Use code blocks and tables for clarity

---

For questions or to propose changes, open an issue or pull request. See `.env.example` for required environment variables.