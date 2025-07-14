# Quickstart

Get started with CodeStory in a few steps.

## 1. Install CodeStory

Install dependencies and set up your environment using [uv](https://github.com/astral-sh/uv):

```sh
uv pip install -r requirements.txt
```

## 2. Configure Environment

Copy the example environment file and edit as needed:

```sh
cp .env.example .env
# Edit .env to set Neo4j, Redis, and Azure OpenAI settings
```

Refer to comments in `.env.example` for required variables. Do **not** hardcode secrets—use environment variables.

## 3. Run the CLI

Check available commands:

```sh
uv run codestory --help
```

## 4. Ingest a Sample Codebase

To ingest a directory of source code (replace with your path):

```sh
uv run codestory ingest --path ./my_project
```

This will parse the code, build the graph, and prepare your project for semantic search and documentation.

---

For more details, see the [CLI Guide](cli.md) and [Configuration Guide](configuration.md).