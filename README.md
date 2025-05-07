# Code Story

A modular, spec-driven codebase for codebase analysis, documentation, and knowledge graph generation.

## Project Structure

See `specs/02-scaffolding/scaffolding.md` for the canonical directory and toolchain layout.

## Getting Started

- Clone the repo
- Run `scripts/bootstrap.sh` to set up dependencies and environment
- See `docs/` for user and developer guides

## Contributing

See `.github/copilot-instructions.md` and `CONTRIBUTING.md` (if present).

## Development

- All code is generated and maintained according to the specifications in `/specs`.
- Each module and submodule is developed, tested, and documented before moving to the next.
- All shell commands and user prompts are tracked in `/Specifications/shell_history.md` and `/Specifications/prompt-history.md`.
- See `/docs/developer_guide.md` for more details.

## Testing

- Run all Python tests:
  ```sh
  poetry run pytest
  ```
- Run all JS/TS tests (from `gui/`):
  ```sh
  cd gui
  pnpm test
  ```

## Contributing

- Follow the spec-driven process described in `/specs/Main.md` and `/02-scaffolding/scaffolding.md`.
- All work should be performed in a branch prefixed with `msft-` and merged via PR.
- See `/docs/developer_guide.md` for coding standards and contribution guidelines.

## License

See `LICENSE` file for details.
