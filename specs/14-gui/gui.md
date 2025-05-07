# 14.0 GUI

**Previous:** [CLI](../13-cli/cli.md) | **Next:** [Infrastructure](../15-infra/infra.md)

**Dependencies:** 
- [Scaffolding](../02-scaffolding/scaffolding.md)
- [Configuration Module](../03-configuration/configuration.md)
- [Code Story Service](../11-code-story-service/code-story-service.md)
- [MCP Adapter](../12-mcp-adapter/mcp-adapter.md)

**Used by:** End users

## 14.1 Purpose

Provide a **React + Redux** single‑page application that visualises the Neo4j graph in 3‑D (using `3d-force-graph`), lets users control ingestion runs, query graph data, and edit configuration.  Users may also ask natural language questions about the graph and get answers back. The GUI will run in a container locally or in Azure Container Apps.  The GUI will be a wrapper around the code-story service API and MCP adapter, so it does not need to know about the details of the implementation of the code-story service or the MCP adapter.

## 14.2 Key Features

* 3‑D force‑directed graph view with Neo4j integration, showing node/edge metadata and data on hover/click. 
* Ingestion dashboard: start run, show progress per step.
* Config editor form bound to `.env` / `.codestory.toml` via REST.
* MCP playground tab to issue tool calls and view JSON.
* Natural language query tab to ask questions about the graph and get answers back.
* Responsive design for desktop and mobile.
* Offers all the features of the CLI, but in a user-friendly web interface.
* Uses the code-story service API and MCP adapter to interact with the graph database and ingestion pipeline. Does not use the CLI for any of its functionality.
* Uses the `@vasturiano/force-graph` library to render the graph in 3D.

## 14.3 Tech Stack

* Typescript + React
* Redux Toolkit + RTK Query
* Mantine UI components; `3d-force-graph` for visualisation
* Axios for API calls; WebSocket for live progress

## 14.4 Code Structure

## 14.4 Code Structure

```
gui/
├── src/
│   ├── main.tsx                    # Application entry point
│   ├── App.tsx                     # Root component
│   ├── store/                      # Redux store
│   │   ├── index.ts                # Store configuration
│   │   ├── slices/                 # Redux state slices
│   │   │   ├── configSlice.ts      # Configuration state
│   │   │   └── uiSlice.ts          # UI state (active tab, etc.)
│   │   └── api/                    # RTK Query API definitions
│   │       ├── graphApi.ts         # Graph query endpoints
│   │       ├── ingestApi.ts        # Ingestion control endpoints
│   │       └── configApi.ts        # Configuration endpoints
│   ├── components/                 # Reusable UI components
│   │   ├── common/                 # Shared components
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── LoadingSpinner.tsx
│   │   │   └── ErrorBoundary.tsx
│   │   ├── graph/                  # Graph visualization components
│   │   │   ├── GraphViewer.tsx     # 3D force graph container
│   │   │   ├── NodeDetails.tsx     # Node property panel
│   │   │   ├── EdgeDetails.tsx     # Edge property panel
│   │   │   └── GraphControls.tsx   # Zoom, filter controls
│   │   ├── ingest/                 # Ingestion components
│   │   │   ├── IngestionPanel.tsx  # Start new ingestion
│   │   │   ├── JobsList.tsx        # List of ingestion jobs
│   │   │   └── ProgressTracker.tsx # WebSocket progress bar
│   │   ├── config/                 # Configuration components
│   │   │   ├── ConfigEditor.tsx    # Form for .env/.toml
│   │   │   └── ConfigSchema.tsx    # Dynamic form generator
│   │   ├── mcp/                    # MCP playground components
│   │   │   ├── McpPlayground.tsx   # Tool call interface
│   │   │   └── ResponseViewer.tsx  # JSON response formatter
│   │   └── ask/                    # Natural language components
│   │       ├── QueryInput.tsx      # Question input form
│   │       └── AnswerDisplay.tsx   # Formatted answer display
│   ├── hooks/                      # Custom React hooks
│   │   ├── useWebSocket.ts         # WebSocket connection handler
│   │   ├── useGraph.ts             # Graph data manipulation
│   │   └── useIngest.ts            # Ingestion job management
│   ├── pages/                      # Main application views
│   │   ├── GraphPage.tsx           # 3D graph visualization
│   │   ├── IngestionPage.tsx       # Ingestion dashboard
│   │   ├── ConfigPage.tsx          # Configuration editor
│   │   ├── McpPage.tsx             # MCP playground
│   │   └── AskPage.tsx             # Natural language queries
│   ├── utils/                      # Helper functions
│   │   ├── api.ts                  # API client setup
│   │   ├── graph.ts                # Graph data processing
│   │   └── formatters.ts           # Data display formatters
│   └── styles/                     # Global styles and themes
│       ├── theme.ts                # Mantine theme config
│       └── global.css              # Global CSS
└── public/                         # Static assets
```

The GUI's architecture follows a layered approach with clear separation of concerns:

1. **Core Structure**
   - Entry point (`main.tsx`) configures React and Redux providers
   - `App.tsx` handles routing between main pages
   - Pages compose multiple components specific to their feature area

2. **State Management**
   - Redux Toolkit for global state (`configSlice`, `uiSlice`)
   - RTK Query for API interaction and caching (`graphApi`, etc.)
   - Local component state for UI-specific concerns

3. **API Integration**
   - `graphApi.ts` - Endpoints for graph queries and manipulation
   - `ingestApi.ts` - Endpoints for ingestion control and status
   - `configApi.ts` - Endpoints for configuration management
   - WebSocket handling for real-time progress updates

4. **Component Organization**
   - Feature-based organization (`graph/`, `ingest/`, `config/`, etc.)
   - Common components shared across features
   - Hooks extract reusable logic from components

5. **Styling Approach**
   - Mantine components provide consistent look and feel
   - Custom theme configuration for branding
   - Minimal global CSS

This structure enables independent development of each feature area while maintaining a cohesive application. The modular approach allows components to be tested in isolation and supports potential future extensions.

## 14.5 Implementation Steps

The following steps outline the implementation of the GUI, ensuring that all user stories and acceptance criteria are met:

1. **Set up project structure**
   - Create a new React TypeScript project: `pnpm create vite gui --template react-ts`
   - Set up directory structure as outlined in section 14.4
   - Configure TypeScript with appropriate settings for strict type checking

2. **Install dependencies**
   ```bash
   pnpm add @reduxjs/toolkit react-redux @mantine/core @mantine/hooks @mantine/form @vasturiano/3d-force-graph three axios react-router-dom
   pnpm add -D typescript @types/react @types/three eslint prettier vitest
   ```

3. **Implement Redux store**
   - Create store configuration in `store/index.ts`
   - Implement Redux slices for UI state and configuration
   - Set up RTK Query API definitions for graph, ingestion, and configuration endpoints
   - Add WebSocket middleware for real-time updates

4. **Implement graph visualization components**
   - Create `GraphViewer` component that queries `/v1/query` for subgraph data
   - Implement node and edge detail panels for property inspection
   - Add graph controls for filtering, zooming, and node selection
   - Build 3D force-directed graph visualization using `3d-force-graph`

5. **Implement ingestion components**
   - Create ingestion panel for starting new jobs
   - Implement job listing and management interface
   - Build real-time progress tracking using WebSockets (`/ws/status/{job_id}`)
   - Add error handling and status notifications

6. **Implement configuration editor**
   - Create dynamic form generator based on config schema from `/v1/config/schema`
   - Build configuration editor that reads from and writes to `/v1/config`
   - Implement validation and error handling for configuration updates
   - Add support for hot-reloading when configuration changes

7. **Implement MCP playground**
   - Create interface for issuing MCP tool calls
   - Build JSON response viewer with syntax highlighting
   - Add history and saved queries functionality
   - Implement error handling for MCP requests

8. **Implement natural language query components**
   - Create query input interface for `/v1/ask` endpoint
   - Build answer display component with formatting
   - Add support for query history and example queries
   - Implement loading states and error handling

9. **Set up routing and navigation**
   - Configure React Router for navigation between pages
   - Implement sidebar navigation and header components
   - Add responsive design for mobile and desktop layouts
   - Build error boundaries and fallback UI

10. **Implement hooks and utilities**
    - Create custom hooks for WebSocket connections, graph data, and ingestion management
    - Build API client utilities with error handling and authentication
    - Implement graph data processing and formatting utilities
    - Add helper functions for common operations

11. **Set up testing infrastructure**
    - Configure Vitest for component and hook testing
    - Add mock service worker for API testing
    - Create test fixtures and helpers
    - Write unit tests for critical components

12. **Add documentation**
    - Add JSDoc comments to components and functions
    - Create README with setup and usage instructions
    - Document API integration points and data flows
    - Include contributing guidelines

13. **Set up Docker environment**
    - Create `gui.Dockerfile` for production build
    - Configure build and deployment scripts
    - Add service to project-level `docker-compose.yaml`
    - Configure dev server to run on port 5173

14. **Implement authentication flow**
    - Add login page for local development mode
    - Implement token storage and management
    - Add authentication headers to API requests
    - Handle authentication errors and token refresh

15. **Quality assurance**
    - Add ESLint and Prettier for code quality
    - Implement pre-commit hooks for formatting
    - Add accessibility testing and improvements
    - Optimize performance and bundle size

16. **Verification and Review**
    - Run all unit and integration tests to ensure correct functionality
    - Run tests against all components and hooks
    - Verify API integration with mock services
    - Test all user interface flows and interactions
    - Run linting and type checking on all code
    - Perform thorough code review against requirements and design principles
    - Test across different browsers and screen sizes
    - Verify responsive design and mobile usability
    - Test WebSocket connections for real-time updates
    - Check accessibility compliance
    - Validate proper error handling for all edge cases
    - Make necessary adjustments based on review findings
    - Re-run all tests after any changes
    - Document issues found and their resolutions
    - Create detailed PR for final review

17. **Acceptance testing**
    - Verify all user stories in section 14.6 are satisfied
    - Test across different browsers and devices
    - Validate integration with Code Story Service API
    - Document any limitations or known issues

## 14.6 User Stories and Acceptance Criteria

| User Story | Acceptance Criteria |
|------------|---------------------|
| As a developer, I want to visualize the Neo4j graph in 3D so that I can understand the relationships between nodes and edges. | • The GUI displays a 3D force-directed graph of the Neo4j database.<br>• Nodes and edges show metadata on hover/click.<br>• Graph visualization respects node types with appropriate colors and icons.<br>• Camera controls allow for zoom, pan, and rotation of the graph. |
| As a developer, I want to filter and search the graph so I can focus on specific parts of the codebase. | • Search functionality allows finding nodes by name, type, or properties.<br>• Filtering controls can show/hide specific node types.<br>• Selected nodes highlight their direct relationships.<br>• Path finding between selected nodes is visually indicated. |
| As a developer, I want detailed information about nodes and edges so I can understand their properties and context. | • Clicking a node displays its full properties in a detail panel.<br>• Node details include links to related nodes.<br>• Edge details show relationship type and properties.<br>• Code snippets are properly formatted with syntax highlighting. |
| As a developer, I want to start and monitor ingestion runs so that I can track the progress of the ingestion process. | • The GUI provides a dashboard to start ingestion runs.<br>• The GUI shows real-time progress per step in the ingestion process via WebSocket.<br>• Progress indicators show completion percentage and current activity.<br>• Notifications alert when ingestion jobs complete or fail. |
| As a developer, I want to manage existing ingestion jobs so I can monitor and control the system. | • The GUI displays a paginated list of all ingestion jobs with status.<br>• Jobs can be cancelled or stopped from the interface.<br>• Job details show execution time, repository, and step-by-step results.<br>• Failed jobs show detailed error messages and potential resolution steps. |
| As a developer, I want to edit the configuration settings so that I can customize the behavior of the code-story service. | • The GUI provides a form to edit configuration settings.<br>• Configuration UI is dynamically generated from the schema endpoint.<br>• Changes are saved to `.env` or `.codestory.toml` file.<br>• Validation prevents invalid configuration values. |
| As a developer, I want to issue MCP tool calls and view the JSON responses so that I can interact with the graph service programmatically. | • The MCP playground allows constructing and executing tool calls.<br>• JSON responses are displayed with syntax highlighting and collapsible sections.<br>• Query history is maintained for reference and reuse.<br>• Common tool call templates are available for quick access. |
| As a developer, I want to ask natural language questions about the graph and get answers back so that I can interact with the graph service in a more intuitive way. | • The natural language query interface accepts free-form questions.<br>• Answers combine text explanations with relevant graph data.<br>• Query results can be exported or saved.<br>• Answer quality improves based on graph context and data. |
| As a developer, I want intuitive navigation between different features so I can work efficiently. | • Sidebar navigation provides access to all main features.<br>• URL routing preserves state when sharing links.<br>• Breadcrumb navigation shows current location and path.<br>• Recently accessed items are easily accessible. |
| As a developer, I want responsive design so I can use the GUI on different devices. | • Interface adapts to desktop, tablet, and mobile screen sizes.<br>• Critical functionality is accessible on all device types.<br>• Touch controls work properly on mobile devices.<br>• Performance remains acceptable on lower-powered devices. |
| As a developer, I want clear error handling so I can understand and resolve issues. | • API errors are displayed with human-readable messages.<br>• Connection issues show appropriate retry options.<br>• Error boundaries prevent entire application crashes.<br>• Detailed error logging helps with troubleshooting. |
| As a developer, I want secure authentication so my graph data is protected. | • Login screen supports local development mode authentication.<br>• Tokens are securely stored and managed.<br>• Session timeouts are handled gracefully with re-authentication.<br>• Authentication errors provide clear guidance. |
| As a developer, I want fast loading and rendering performance so I can work efficiently with large codebases. | • Initial page load is optimized for speed.<br>• Large graphs use efficient rendering techniques (e.g., WebGL).<br>• Data is cached appropriately to minimize API calls.<br>• Progressive loading shows important data first. |
| As a developer, I want to control service lifecycle (start/stop) via the GUI so I can manage the system without CLI. | • GUI provides controls to start and stop the code-story service.<br>• Service status is clearly indicated in the interface.<br>• Start/stop operations show progress and result confirmation.<br>• Any service errors are clearly displayed with troubleshooting guidance. |
| As a developer, I want consistent visual design and UX patterns so the interface is intuitive and easy to learn. | • Mantine UI components are used consistently throughout.<br>• Color scheme and design language is cohesive across all pages.<br>• Interactive elements behave predictably across the application.<br>• Visual hierarchy guides users to important information and actions. |


---

