# 13.0 CLI

**Previous:** [MCP Adapter](../12-mcp-adapter/mcp-adapter.md) | **Next:** [GUI](../14-gui/gui.md)

**Dependencies:** 
- [Scaffolding](../02-scaffolding/scaffolding.md)
- [Configuration Module](../03-configuration/configuration.md)
- [Code Story Service](../11-code-story-service/code-story-service.md)

**Used by:** End users

## 13.1 Purpose

Offer a **Rich -based** command‑line interface enabling developers to:

* Stop and Start the code-story service and MCP adapter (if another command is run before the service is started it will start the service automatically)
* Trigger ingestion runs
* Manage ingestion jobs (stop, cancel, status, etc.)
* Query the graph database using Cypher or MCP tool calls
* Query the graph database using natural language queries (using the MCP adapter)
* Query graph summaries (`search`, `path`, etc.)
* Show or update the configuration (except secrets)
* Open the GUI in a browser
* Show help for each command
* Show the status of the code-story service and MCP adapter
* Output an HTML visualization of the graph database with a color-coded key and a 3D force-directed graph visualization.
* Is just a wrapper around the code-story service API and MCP adapter, so it does not need to know about the details of the implementation of the code-story service or the MCP adapter.

## 13.2 Commands

| Command                          | Alias    | Description                                                |
| -------------------------------- | -------- | ---------------------------------------------------------- |
| `codestory ingest <path-or-url>` | `cs in`  | Kick off ingestion and stream progress bar.                |
| `codestory status <run-id>`      | `cs st`  | Show status table for a previous run.                      |
| `codestory query <cypher or mcp>`| `cs q`   | Run ad‑hoc Cypher or MCP tool call.                        |
| `codestory config <key=value>`   | `cs cfg` | Set Configuration values                                   |
| `codestory ui`                   | `cs ui`  | Open GUI at `http://localhost:5173`.                       |
| `codestory service start`        | `cs ss`  | Start the code-story service and MCP adapter.              |
| `codestory service stop`         | `cs sx`  | Stop the code-story service and MCP adapter.               |
| `codestory ingest stop <run-id>` | `cs is`  | Stop a running ingestion job.                              |
| `codestory ingest jobs`          | `cs ij`  | List all ingestion jobs with their statuses.               |
| `codestory ask <query>`          | `cs gs`  | Query graph summaries using natural language.              |
| `codestory config show`          | `cs cfs` | Display current configuration settings.                    |
| `codestory visualize`            | `cs vz`  | Output an HTML visualization of the graph database with a color-coded key and a 3D force-directed graph visualization. |

## 13.3 Implementation Steps

1. `poetry add rich rich-markdown rich-click`
2. Create `cli/__main__.py` registering Typer app.
3. Use Rich live progress: subscribe to Redis `status::<run_id>`.
4. Implement config TUI via `rich.prompt` + TOML editing.
5. Package entry‑point in `pyproject.toml` → `console_scripts = { codestory = 'codestory.cli:app' }`.
6. **Verification and Review**
   - Run all unit tests to verify command parsing and execution
   - Run integration tests against a real Code-story instance
   - Test each command to ensure it functions as specified
   - Verify proper formatting and display of Rich UI elements
   - Test error handling for all edge cases
   - Run linting and type checking on all code
   - Perform thorough code review against requirements
   - Verify that all commands in section 13.2 are implemented
   - Test CLI in both interactive and non-interactive modes
   - Make necessary adjustments based on review findings
   - Re-run all tests after any changes
   - Document discovered issues and their resolutions
   - Create detailed PR for final review

## 13.4 Testing

- **Unit** - ensure CLI commands parse and invoke the correct methods
  - Test command registration and argument parsing
  - Test client API calls and error handling
  - Test output formatting with Rich
  - Test configuration validation and updates
  - Mock all external dependencies (service API, Redis, browser)

- **Integration** - run CLI commands against a real Code-story instance; validate output format and data integrity
  - Test full command workflow with real or containerized services
  - Verify correct handling of service state (start/stop)
  - Test real ingestion process and progress reporting
  - Test query execution and result rendering
  - Test configuration updates persist correctly
  - Test visualization generation and browser interaction

See the [CLI Test Plan](./cli_test_plan.md) for a comprehensive testing strategy.

## 13.5 Acceptance Criteria

- Typing `cs in .` on fresh repo prints colored progress and ends with green “Completed”.
- `cs q "MATCH (n) RETURN count(n)"` returns Rich table.
- Typing `cs st <run-id>` displays a clearly formatted Rich table showing the detailed status of the specified ingestion run.
- Typing `cs q "<cypher or mcp>"` executes the provided Cypher or MCP query and returns results formatted in a readable Rich table.
- Typing `cs cfg <key=value>` successfully updates the specified configuration setting and confirms the update with a clear message.
- Typing `cs ui` opens the default web browser at `http://localhost:5173` and loads the GUI successfully.
- Typing `cs ss` starts the code-story service and MCP adapter, displaying a confirmation message upon successful startup.
- Typing `cs sx` stops the code-story service and MCP adapter, displaying a confirmation message upon successful shutdown.
- Typing `cs is <run-id>` successfully stops the specified ingestion job and confirms the action with a clear message.
- Typing `cs ij` lists all ingestion jobs along with their statuses in a clearly formatted Rich table.
- Typing `cs gs "<query>"` executes the natural language query against the graph summaries and returns relevant results formatted clearly.
- Typing `cs cfs` displays all current configuration settings in a clearly formatted Rich table.
- Typing `cs vz` outputs an HTML visualization of the graph database with a color-coded key and a 3D force-directed graph visualization.
- The CLI is able to handle errors gracefully, providing clear error messages and suggestions for resolution.
- The CLI is able to handle invalid input gracefully, providing clear error messages and suggestions for resolution.


---

