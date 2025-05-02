# code-story

A service that ingests a code repository, constructs a Neo4j knowledge graph + LLM summaries, and exposes the knowledge via MCP, CLI, and GUI.

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 16+
- Docker & Docker Compose
- Poetry
- pnpm

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/rysweet/code-story.git
   cd code-story
   ```

2. Install Python dependencies with Poetry:
   ```bash
   poetry install
   ```

3. Install Node.js dependencies with pnpm:
   ```bash
   pnpm install
   ```

4. Start services via Docker Compose:
   ```bash
   docker-compose up --build
   ```

## Usage

Run CLI:
```bash
poetry run code-story --help
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
