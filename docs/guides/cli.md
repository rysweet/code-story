# CLI Usage

CodeStory provides a command-line interface (CLI) for code ingestion, querying, and configuration. The CLI is built with [Typer](https://typer.tiangolo.com/) and is designed for ease of use and extensibility.

## Basic Usage

To see available commands and options, run:

```sh
uv run codestory --help
```

### Example Output

```
Usage: codestory [OPTIONS] [COMMANDS]

  CodeStory command-line interface

Options:
  --help  Show this message and exit.

Commands:
  (no subcommands defined yet)
```

The CLI will be extended with subcommands for code ingestion, querying, and configuration. For now, use `--help` to see available options.

---

For more details on ingesting code and configuring the environment, see the [Quickstart](quickstart.md) and [Configuration](configuration.md) guides.