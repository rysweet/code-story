There will be a demo of the system, showcasing its capabilities and features. The demo will include the following components:

- A top level document linking to each of the other demos.
- [CLI Demo](./demo.md#CLI%20Demo) which step-by-step illustrates the [command line interface](../13-cli/cli.md) and its functionality.
- [GUI Demo](./demo.md#GUI%20Demo) which showcases the [graphical user interface](../14-gui/gui.md) and its features.
- [Agent Based MCP Demo](./demo.md#MCP%20Demo) which demonstrates the [MCP service](../12-mcp-adapter/mcp-adapter.md) being consumed by an agent.


# CLI Demo

The CLI Demo will showcase the command line interface of the system. It will include the following steps:
1. **Installation**: Instructions on how to install the CLI tool.
2. **Configuration**: Setting up the configuration file and environment variables.
3. **Code Ingestion**: The demo will show how to ingest code files into the system using the CLI. We will use the CodeStory codebase as an example.
4. **Code Analysis**: Demonstration of how to analyze the ingested code using the CLI. Includes demoing the `codestory query` command to run ad-hoc Cypher or MCP tool calls as well as the `codestory ask` command to query graph summaries using natural language.
5. **Graph Visualization**: Show how to visualize the code structure and relationships using the CLI.
6. **Remaining Features**: Highlight any remaining features of the CLI that are not covered in the previous steps.
7. **Cleanup**: Instructions on how to clean up the environment after the demo.

## Demo Document

The demo document will be a markdown file. It will link to the CLI documentation in the appropriate sections. It will include CLI commands in markdown fence blocks that allow the user to copy them easily, followed by the real output of the commands. The demo document will be structured in a way that allows the user to follow along with the CLI commands and see the output in their terminal.

## Demo Testing

The CLI demo requires a test suite to validate that the demo works as expected. The test suite will run each command in the demo document and compare the output to the expected output.

# GUI Demo

The GUI Demo will showcase the graphical user interface of the system. It will include the following steps:
1. **Installation**: Instructions on how to install/run the GUI tool.
2. **Configuration**: Setting up the configuration file and environment variables.
3. **Code Ingestion**: The demo will show how to ingest code files into the system using the GUI. We will use the CodeStory codebase as an example.
4. **Code Analysis**: Demonstration of how to analyze the ingested code using the GUI. Includes demoing the `codestory query` command to run ad-hoc Cypher or MCP tool calls as well as the `codestory ask` command to query graph summaries using natural language.
5. **Graph Visualization**: Show how to visualize the code structure and relationships using the GUI.
6. **Remaining Features**: Highlight any remaining features of the GUI that are not covered in the previous steps.
7. **Cleanup**: Instructions on how to clean up the environment after the demo.

## GUI Demo Automation

The GUI demo will be automated using the [Playwright](https://playwright.dev/) library. This will allow us to create a script that can run the demo steps automatically, simulating user interactions with the GUI. Each Step of the demo will have a narrative explaining what is happening, displayed in a frame surrounding the GUI. The demo document will includ the demo script and tell the user how to launch the demo process. The script will be run in a separate process, and the user will be able to see the GUI and the demo narrative at the same time.

## GUI Demo Testing

The GUI demo requires a test suite to validate that the demo works as expected. The test suite will run each step of the demo and compare the output to the expected output.

# MCP Demo

The MCP Demo will showcase the MCP service and its integration with the system. It will include the following steps:
1. **Installation**: Instructions on how to install/run the MCP service.
2. **Configuration**: Setting up the configuration file and environment variables.
3. **Code Ingestion**: The demo will show how to ingest code files into the system using the CLI service (so that code graph becomes available to the mcp service). We will use the CodeStory codebase as an example.
4. **Code Analysis**: Demonstration of how to use the MCP service from within an autogen agent, following examples [here](https://microsoft.github.io/autogen/stable/reference/python/autogen_ext.tools.mcp.html). 
5. **Instructions on how to configure the MCP Service within GitHub Copilot In Visual Studio Code following the docs [here](https://code.visualstudio.com/docs/copilot/chat/mcp-servers?wt.md_id=AZ-MVP-5004796).
7. **Cleanup**: Instructions on how to clean up the environment after the demo.

## MCP Demo Tests

The MCP demo requires a test suite to validate that the demo works as expected. The test suite will run each step of the demo and compare the output to the expected output.