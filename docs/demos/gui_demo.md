# GUI Demo

This demonstration showcases the Code Story graphical user interface, providing a visual way to explore, analyze, and understand codebases.

## Installation and Setup

### Prerequisites

- Node.js (v18+)
- NPM (v8+)
- Running Code Story service and Neo4j database

### Starting the GUI

```bash
# Clone the repository if you haven't already
git clone https://github.com/rysweet/code-story.git
cd code-story

# Install dependencies
npm install

# Start the development server
npm run dev
```

The GUI should now be running at http://localhost:5173. Open this URL in your browser to access the Code Story interface.

## Configuration

The first time you access the GUI, you'll need to configure the connection settings:

1. Click on the **Configuration** tab in the sidebar
2. Enter your Neo4j connection details:
   - Database URL: `bolt://localhost:7687`
   - Username: `neo4j`
   - Password: `your-password`
   - Database Name: `codestory`
3. Enter your OpenAI API settings:
   - API Key: `your-openai-api-key`
   - Model: `gpt-4o`
4. Click **Save Configuration**

## Code Ingestion

Before you can explore code, you need to ingest a repository:

1. Click on the **Ingestion** tab in the sidebar
2. In the ingestion panel, enter the path to your repository:
   - Repository Path: `/path/to/your/repo` or use the file picker
3. Click **Start Ingestion**

A progress tracker will appear showing the status of the ingestion process. This includes:
- Filesystem scanning
- Code analysis
- Summary generation
- Knowledge graph creation

For this demo, we'll use the Code Story codebase itself, which should take a few minutes to ingest.

## Graph Exploration

Once ingestion is complete, you can explore the code graph:

1. Click on the **Graph** tab in the sidebar
2. The central panel now shows an interactive visualization of the code graph
3. You can:
   - Zoom in/out using the mouse wheel
   - Pan by dragging the background
   - Click on nodes to see details
   - Expand/collapse node connections
   - Filter the graph using the controls panel

### Exploring Node Details

1. Click on a file node (e.g., `neo4j_connector.py`)
2. The details panel on the right shows:
   - File metadata (path, size, extensions)
   - Summary of the file's purpose
   - List of functions and classes
3. Click on function and class links to navigate the graph
4. Use the "Neighbors" tab to see relationships

### Using Graph Controls

The Graph Controls panel allows you to:
1. Search for specific nodes by name or path
2. Filter by node types (files, directories, functions, classes)
3. Adjust the layout algorithm
4. Change visualization settings

## Asking Questions

The Code Story GUI includes a natural language interface:

1. Click on the **Ask** tab in the sidebar
2. Type a question in the input field, for example:
   - "How does the ingestion pipeline work?"
   - "What are the main components of the system?"
   - "Show me the dependency structure of the CLI module"
3. Click **Ask Question**

The system will analyze your question, search the knowledge graph, and present a detailed answer with relevant code references.

## MCP Playground

The MCP (Machine Callable Packages) Playground allows you to interact with the code through structured tool calls:

1. Click on the **MCP** tab in the sidebar
2. Select a template from the dropdown (e.g., "Find similar code")
3. Fill in the parameters for the tool
4. Click **Execute**

The system will execute the tool and display the results. You can chain multiple tool calls together to create complex workflows.

## Cleanup

When you're done with the demo:

1. Stop the development server by pressing `Ctrl+C` in the terminal
2. Optional: Clear the database by running:
   ```bash
   codestory query run "MATCH (n) DETACH DELETE n"
   ```

## Automating the Demo

For presentations or testing, you can use the automated GUI demo script:

```bash
# Run the automated demo
npm run demo
```

This will start a guided tour of the GUI features with narrative explanations.