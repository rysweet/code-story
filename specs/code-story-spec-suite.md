<!-- code-story – Specification Suite (v0.4) -->

# 1.0 Overview & Architecture

## 1.1 Mission

Convert any codebase into a richly‑linked knowledge graph plus natural‑language summaries that developers can query through a CLI or GUI and which LLM agents can query through **Model Context Protocol (MCP)**.

## 1.2 Components and Data Flow

1. Configuration Module - manages the configuration of the application based on a .env file or Azure KeyVault.
2. **CLI or GUI** triggers *Ingestion* of a codebase (local or git). Alternatively queries or displays the graph or nodes/edges/metadata from the graph. 
   - *CLI* is a rich command line interface using [Rich](https://github.com/Textualize/rich-cli). 
   - *GUI* is a React + Redux web application that uses the 3D force graph library to display the graph and allows users to interact with it.
   - *CLI* and *GUI* are both built using the same codebase and consume the same API from the **Code-Story Service**.
3. *Code-Story Service* python service runs in a container and handles the API calls and manages the ingestion pipeline or queries the graph service.
   - *Ingestion Pipeline* is a Celery task queue and workers for running the ingestion pipeline.
   - *Graph Database* is a Neo4j graph database and semantic indexing service that stores the graph and semantic index.
   - *OpenAI Client* is an Azure OpenAI client for LLM inference.
4. *Ingestion Pipeline* runs all of the steps in the ingestion workflow. Each step is a plug‑in. System can be extended by adding new plugins.
   - *BlarifyStep* runs [Blarify](https://github.com/blarApp/blarify) to parse the codebase and store the raw AST in the **Graph Service**.
   - *Summariser* computes a DAG of code dependencies and walks from leaf nodes to the top and computes summaries for each module using the Azure AI model endpoints and stores them in the **Graph Service**.
   - *FileSystemStep* creates a graph of the filesystem layout of the codebase and links it to the AST nodes.
   - *DocumentationGrapher* creates a knowledge graph of the documentation and links it to the relevant AST, Filesystem, and Summary nodes.
5. *MCP Adapter* exposes the graph service to LLM agents [secured by Entra ID](https://den.dev/blog/auth-modelcontextprotocol-entra-id/) using the [mcp-neo4j-cypher](https://github.com/neo4j-contrib/mcp-neo4j/tree/main/servers/mcp-neo4j-cypher) adapter. 
6. *Graph Database* stores the graph and semantic index.
   - uses Neo4j 5.x with the native vector store and semantic indexing.
   - uses [APOC](https://neo4j.com/labs/apoc/)
   - One layer of the graph is the AST and its symbol bindings, created with blarify. 
   - Another layer of the graph is the filesystem layout of the codebase.
   - Another layer of the graph is the Summary of all the modules in the codebase.
   - The semantic index is a vector database of the codebase - see [Neo4j Blog on Semantic indexes](https://neo4j.com/blog/developer/knowledge-graph-structured-semantic-search/)
   - The graph and semantic index are used to answer queries from LLM agents.
7. External agents or the **CLI/GUI** call MCP tools to query code understanding.
8. *OpenAI Client* handles the OpenAI API calls for LLM inference. Will use ```az login --scope https://cognitiveservices.azure.com/.default``` with bearer token auth in the AzureOpenAI package to authenticate and use the Azure OpenAI API. The client will be a thin wrapper around the Azure OpenAI API and will handle the authentication and request/response handling, as well as backoff/throttling strategies. The client will also support asynchronous requests to improve performance and scalability. 
9. Docs - use Sphinx to generate docs from the codebase and its docstrings. There will also be Markdown documentation for each of the modules and components. 

## 1.3 Deployment Topology (local dev)

1. Neo4J Graph Service - runs in a container - Neo4j graph database and semantic indexing.
2. Blarify container - linux container running blarify to parse the codebase and populate the graph database.
3. Code-Story Service - Hosts the APIs for the core functionality of Ingestion and Querying the graph database.
4. CLI - Rich CLI for interacting with the code-story service.
5. GUI - React + Redux GUI for interacting with the code-story service.
6. OpenAI Client - Azure OpenAI client for LLM inference.
7. Ingestion Pipeline - Celery task queue and workers for running the ingestion pipeline.
8. MCP Adapter - use https://github.com/neo4j-contrib/mcp-neo4j/tree/main/servers/mcp-neo4j-cypher to expose the graph database as a MCP service.

All services run under `docker-compose` network; Azure Container Apps deployment mirrors this layout with container scaling.

## 1.4 Cross‑Cutting Concerns

* **Auth**: MCP endpoints protected by Entra ID bearer JWT; local mode can bypass with `--no-auth` flag.
* **Observability**: OpenTelemetry traces, Prometheus metrics from every service, Grafana dashboard template in `infra/`.
* **Extensibility**: Ingestion steps are plug‑in entry‑points; GUI dynamically reflects new step types; prompts in `prompts/` folder can be customised.

## 1.5 Project Specifications and Development Methodology

The project is built using a spec driven modular approach. 
The specifications start with this document. Each major component then will have its own specification directory with more detailed specifications that are co-created with LLMs using this document. Each module shall be broken down into small enough components (individual specifications) that the entire component can be regenerated from its specification in a single inference. When there are changes to code the specification must also be updated and the code regenerated from the specification.
The specifications shall include detailed descriptions, architectural notes, dependencies, technical stack, detailed user stories, test criteria, example of api usage for each module or component, and enough instructions to allow the one shot cogeneration of the entire component or module from a single LLM prompt.
The project will be built folowing these steps:

1. Break down this specification into derived specifications for each major module.
2. Each derived specification will be broken down into smaller specifications for each sub-module or component. 
3. If necessary, each sub-module or component will be broken down into smaller specifications, until each specification captures a single component that can be generated in a single LLM inference.
4. Each final specification will include a detailed prompt for the LLM to use to generate the code for that component. 
5. We will then walk through the specifications and generate the code for each component in the order of the required dependencies. 
6. During each generation stage we will run the tests for each component and ensure that all tests pass before moving on to the next component.
7. The AI Agent will also take the role of a reviewer and will review the generated code for each component and ensure that it meets the specifications, coding guidelines, and best practices.
8. We will also run the tests for the entire project after each component is generated to ensure that all components work together as expected.
9. Each component will have its own documentation generated to facilitate understanding and usage. 

## 1.6 Coding Guidelines

- Use the lastest stable versions of each language and framework where possible. 
- Follow the conventions for each language WRT code formatting, linting, and testing.
- Where possible use tools for linting and formatting checks. 
- Ensure that all tests are run and pass before merging any changes. 
- Use pre-commit hooks to ensure that all code is linted and formatted before committing.
- Use continuous integration tools to automate testing and ensure code quality.

## 1.7 Using github

1. the github repo is https://github.com/rysweet/code-story
2. Make use of the gh cli to manage the repo, PRs, and issues.
3. Each stage of the project should progress on a separate branch of the repo and upon completion be merged as a PR to the main branch.
4. Each PR should be reviewed and approved before merging.

# 2.0 Scaffolding

## 2.1 Purpose
Create a reproducible mono‑repo skeleton for Python 3.12 + TypeScript 5.4 development, containerised with Docker Compose and wired for CI. All later components depend on this foundation.

## 2.2 Directory Layout

```text
code-story/                  # Project root
├─ .devcontainer/            # VS Code & Codespaces
├─ .editorconfig             # Editor config
├─ .env                      # Secrets (not in repo)
├─ .env-template             # Template for secrets
├─ .eslintrc.json            # ESLint config
├─ .github/                  # CI pipelines
│  └─ workflows/             # CI pipelines
│  └─ copilot-instructions.md # Copilot instructions
├─ .gitignore                # Git ignore
├─ .mypy.ini                 # Mypy config
├─ .pre-commit-config.yaml   # Pre-commit hooks
├─ .ruff.toml                # Ruff config
├─ docs/                     # Sphinx documentation
├─ gui/src/                  # React/Redux GUI app - uses code-story service
├─ infra/                    # Docker, compose, Bicep (added P8)
├─ prompts/                  # Prompty templates
├─ README.md                 # Project overview
├─ scripts/                  # Helper scripts used for automation
├─ specs/                    # Markdown specifications (including this this file)
├─ src/                      # Python package root
│  └─ codestory/             # Python service that runs the ingestion pipeline and exposes the graph service
│  └─ codestory-cli/         # CLI app that uses code-story service built with Rich
│  └─ codestory-gui/         # React/Redux GUI app that uses code-story service
└─ tests/                    # pytest + testcontainers
```

## 2.3 Toolchain Versions

| Area       | Tool              | Version | Purpose                   |
| ---------- | ----------------- | ------- | ------------------------- |
| Python     | Poetry            | ^1.8    | Dependency & venv manager |
|            | Ruff              | latest  | Lint + format             |
|            | mypy              | latest  | Static typing (–strict)   |
| JS / TS    | pnpm              | latest  | Workspace manager         |
| Containers | Docker Engine     | ≥ 24.0  | Runtime                   |
| CI         | GitHub Actions    | n/a     | Lint + tests              |
| Dev        | devcontainer spec | 0.336.0 | Unified IDE env           |

## 2.4 Configuration Conventions

| File                | Role                     | Precedence |
| ------------------- | ------------------------ | ---------- |
| `.env` and `.env-template`              | secrets & host specifics |  1         |
| `.codestory.toml`   | project defaults         |  2         |
| hard‑coded defaults | safe fallbacks           |  3         |

`src/codestory/config.py` exposes a singleton `settings: Settings` (Pydantic BaseSettings).

## 2.5 Implementation Steps

| #  | Action                                                                               |
| -- | ------------------------------------------------------------------------------------ |
|  1 | `git init code-story && cd code-story`                                               |
|  2 | `poetry new src/codestory --name codestory`                                          |
|  3 | `poetry add pydantic rich typer[all] testcontainers pytest pytest-asyncio ruff mypy` |
|  4 | `pnpm init -y && pnpm add -w vite typescript @types/node`                            |
|  5 | Add `.env.example` placeholders (`OPENAI_API_KEY=` etc.)                             |
|  6 | Add `.pre-commit-config.yaml` – Ruff + mypy                                          |
|  7 | Add `.github/workflows/ci.yml` – setup‑python, `poetry install`, Ruff, mypy, pytest  |
|  8 | Root `docker-compose.yaml` with Neo4j & Redis stubs                                  |
|  9 | `.devcontainer/devcontainer.json` pointing to compose services                       |
| 10 | Commit & push – CI green                                                             |

A helper script `scripts/bootstrap.sh` may automate steps 1‑9.

## 2.6 Testing & Acceptance

* **Unit** – pytest; verify config precedence & validation.
* **Lint** – Ruff, mypy (strict).
* **Acceptance**

  * `pytest` passes ≥ 90 % coverage on P0 modules.
  * `ruff check` clean; `mypy --strict` clean.
  * `docker compose up -d` starts Neo4j & Redis healthy.

---

# 3.0 Configuration Module

## 3.1 Purpose

The configuration module is a singleton that loads the configuration from the `.env` file and exposes it to the rest of the application. Configuration variables are in the form of key-value pairs formatted like bash shell environment variables so that they can be evaluated across languages. There is a python module that reads and writes the configuration to the `.env` file. The configuration module is used by all other modules in the application to access the configuration values. The .env file is not committed to the repository and is used to store secrets and environment-specific values. There will be a .env-template that is checked in and contains the default values. The configuration module also provides a way to override the default values with environment variables. Secrets can also be read from an Azure KeyVault if so configured. 

## 3.2 Responsibilities

- Load the configuration from the `.env` file and expose it to the rest of the application.
- Provide a way to override the default values with environment variables.
- Provide a way to write the configuration to the `.env` file.
- Ensure that the configuration module is a singleton.
- Provide a way to configure an Azure KeyVault to read secrets from the KeyVault.

## 3.3 User Stories and Acceptance Criteria

| User Story | Acceptance Criteria |
|------------|---------------------|
| As a developer I want to be able to read and write the configration of the application by accessing the config object, so that I can access configuration consistently and transparently.| • The configuration module is a singleton.<br>• The configuration module loads the configuration from the `.env` file.<br>• The configuration module exposes the configuration values to the rest of the application. <br>• The configuration module provides a way to write the configuration to the `.env` file. |
| As a developer I want to be able to store secrets in environment variables, in the .env file, or in an Azure KeyVault so that I can manage sensitive information securely.| • The configuration module provides a way to override the default values with environment variables..<br>• The configuration module provides a way to configure an Azure KeyVault to read secrets from the KeyVault. | 
| As a developer, I want to ensure that the configuration module is well-documented so that I can understand its usage and capabilities easily.| • The configuration module includes comprehensive documentation and examples for usage. | 

---

# 4.0 Graph Database Service

## 4.1 Purpose

Provide a self‑hosted **Neo4j 5.x** backend with semantic index and vector search, APOC, capable of running in a container locally or in Azure Container Apps, with mounted `plugins/` (APOC, n10s). Data persisted in named volume `neo4j_data`.

## 4.2 Responsibilities

* Create and adapt the db schema, constraints, and indexes.
* Expose a Neo4JConector module that can be used by other components to connect to the Neo4j database plus APOC Core and perform graph operations and cypher queries. 
* Docker container and compose file to run the Neo4j database and expose the graph service.
* Start and Stop scripts for Neo4J and its supporting services.

## 4.3 Code Structure

```text
src/codestory/graphdb/
├── __init__.py
├── neo4j_connector.py          # Neo4jConnector class
├── schema.py             # DDL + constraints
```

## 4.4 Data Model (abridged)

The schema needs to be dynamic as new graph nodes and relationships are added by the ingestion pipeline. Key types of information that the graphmust store include:

* AST/symbol nodes from Blarify
* File‑system nodes
* Summary & embedding nodes
* Documentation nodes
* **Semantic Index** (full‑text + vector) for combined structured + similarity search
* Edges between nodes to represent relationships between the nodes.

## 4.5 Testing Strategy

* **Unit** - ensure that the full api of the Neo4J Connector module is correct and functioning. Ensure that the schema can be initialized successfully. 
* **Integration** - ensure that the Neo4J database can be stopped and started successfully. Ensure that the schema can be initialized successfully. Ensure that the Neo4J database can be queried successfully. Ensure that the Neo4J database can be queried with cypher queries successfully.

## 4.6 User Stories and Acceptance Criteria

| User Story | Acceptance Criteria |
|------------|---------------------|
| As a developer, I want to be able to run the Neo4J database in a container so that I can develop and test the graph service locally. | • The Neo4J database can be started and stopped using the provided scripts.<br>• The Neo4J database can be queried using the Neo4J Connector module. |
| As a developer, I want to be able to run the Neo4J database in Azure Container Apps so that I can deploy the graph service in Azure. | • The Neo4J database can be started and stopped using the provided scripts.<br>• The Neo4J database can be queried using the Neo4J Connector module. |
| As a developer, I want to be able to run cypher queries against the graph service so that I can retrieve relevant data. | • The Neo4J database can be queried using cypher queries. |
| As a developer, I want to be able to access the APOC features of Neo4J so that I can use the graph service to its full potential. | • The Neo4J database can be queried using the APOC Core features. |
| As a developer, I want to be able to run the Neo4J database with a mounted volume so that I can persist data across runs. | • The Neo4J database data persists between container restarts. |
| As a developer, I want to be able to use advanced search capabilities with the graph database. | • The Neo4J database can be queried using the semantic index.<br>• The Neo4J database can be queried using the vector search index. |

## 4.7 Implementation Steps

__TODO__

# 5.0 AI Client

## 5.1 Purpose

Using the Azure OpenAI Library and bearer-token authentication, provide low‑level async/sync access to Azure OpenAI completions, embeddings, and chat—with retry, throttling back‑off, and metrics. Domain summarisation logic lives elsewhere.  Allow for multiple models to be used for different tasks. Allow the same code to use either chat completion or reasoning models. Support at least o1/o3 reasoning, gpt‑4o chat, and `text‑embedding‑3-small` embeddings.

## 5.2 Responsibilities

\| OC‑R1 | Bearer‑token auth via `AZURE_OAI_KEY`, `AZURE_OAI_ENDPOINT`. |
\| OC‑R2 | Support o1/o3 reasoning, gpt‑4o chat, `text‑embedding‑3-small`. |
\| OC‑R3 | Retry on 429 with exponential back‑off (tenacity). |
\| OC‑R4 | Public methods: `complete`, `embed`, `chat`. |
\| OC‑R5 | Prometheus metrics & OTEL traces. |
\| OC‑R6 | Support both chat completion and reasoning models. |
\| OC‑R7 | Support multiple models for different tasks. |
\| OC‑R8 | Support both async and sync requests. |


## 5.3 Architecture

```
src/codestory/llm/
├── __init__.py
├── client.py
├── models.py
└── backoff.py
```

## 5.4 Implementation Steps

1. `poetry add openai azure-core prompty tenacity prometheus-client`
2. Implement each code file
3. Ensure all components are integrated and functioning as expected.

## 5.5 Example Code

```python
from codestory.llm.client import OpenAIClient
client = OpenAIClient()
response = client.complete(
    prompt="What is the capital of France?",
    model="gpt-4o",
    max_tokens=50,
    temperature=0.7
)
print(response)
```

Note that reasoning models do not have max_tokens or temperature parameters but instead have different parameters. The client should be able to handle this automatically based on the model type.

### 6 Testing & Acceptance

* Unit mock for retry; branch coverage ≥ 95 %.
* Integration with real Azure OpenAI;

---

# 6.0 Ingestion Pipeline

## 6.1 Purpose

**Ingestion Pipeline** is a library that can be embedded into the a service such as the code-story service that runs all of the steps in the ingestion workflow. Each step is a plug‑in. System can be extended by adding new plugins.  Each step in the workflow is an independent module that is not part of the ingestion pipeline. The order of execution is governed by a configuration file. Ingestion module workflow steps are python modules that implement the `PipelineStep` interface. The pipeline is a Celery task queue and workers for running the ingestion pipeline. The pipeline will run in a container locally or in Azure Container Apps.

## 6.2 Responsibilities

- When a new ingestion job is started, the pipeline will run all of the steps in the ingestion workflow in the order specified in the configuration file.
- The Ingestion Pipeline library will have methods for starting, stopping, and managing the status of ingestion jobs.
- The Ingestion Pipeline will consist of multiple workflow steps that can be added or modified as needed.
- The Ingestion Pipeline will have a configuration file that specifies the order of execution of the workflow steps.
- When workflows fail, the pipeline will be able to retry the failed steps or the entire workflow.
- Workflow steps can optionally have an "Ingestion Update" mode that will update the graph with the results of the step without running the entire pipeline.
- Each workflow step will log its execution status and any errors encountered during processing.

## 6.3 Architecture and Code Structure

* uses Celery for task queue and workers
__TODO__

## 6.4 Ingestion Pipeline Workflow Steps

The following steps are the default workflow of the ingestion pipeline but are separate modules, not part of the Ingestion Pipeline module. 

   - *BlarifyStep* runs [Blarify](https://github.com/blarApp/blarify) to parse the codebase and store the raw AST in the **Graph Service**.
   - *Summariser* computes a DAG of code dependencies and walks from leaf nodes to the top and computes summaries for each module using the Azure AI model endpoints and stores them in the **Graph Service**.
   - *FileSystemStep* creates a graph of the filesystem layout of the codebase and links it to the AST nodes.
   - *DocumentationGrapher* creates a knowledge graph of the documentation and links it to the relevant AST, Filesystem, and Summary nodes.

## 6.5 Workflow Steps API

Each workflow step must implement the following operations, inherited from the `PipelineStep` interface:
- `run(repository)`: Run the workflow step with the specified configuration and input data (location of the repo, neo4j connection information, etc.). The operation returns an identifier for the job that can be used to check the status of the job.
- `status(job_id)`: Check the status of the workflow step. The operation returns the current status of the job (e.g., running (% complete), completed, failed).
- `stop(job_id)`: Stop the workflow step. The operation returns the current status of the job (e.g., running, completed, failed).
- `cancel(job_id)`: Cancel the workflow step. The operation returns the current status of the job (e.g., running, completed, failed).
- `ingestion_update(repository)`: Update the graph with the results of the workflow step without running the entire pipeline. The operation returns a job_id that can be used to check the status of the job.

## 6.6 Code Example of calling the Ingestion Pipeline

__TODO__

## 6.7 User Stories and Acceptance Criteria

| User Story | Acceptance Criteria |
|------------|---------------------|
| As a developer, I want the ingestion pipeline to execute workflow steps in a configurable order so that I can easily manage and modify the ingestion process. | • Workflow steps execute in the order specified by the configuration file.<br>• Changing the configuration file updates the execution order without code changes. |
| As a developer, I want to be able to start, stop, and monitor ingestion jobs so that I can control and track the ingestion process effectively. | • Methods exist to start, stop, and check the status of ingestion jobs.<br>• Job statuses are accurately reported and logged. |
| As a developer, I want the ingestion pipeline to support adding new workflow steps as plugins so that I can extend the system functionality without modifying core pipeline code. | • New workflow steps can be added as plugins without altering existing pipeline code.<br>• Newly added plugins are recognized and executed by the pipeline. |
| As a developer, I want the ingestion pipeline to retry failed workflow steps or entire workflows so that transient errors do not require manual intervention. | • Failed workflow steps can be retried individually.<br>• Entire workflows can be retried from the beginning.<br>• Retry attempts are logged clearly. |
| As a developer, I want workflow steps to optionally support an "Ingestion Update" mode so that I can update the graph incrementally without rerunning the entire pipeline. | • Workflow steps can be executed individually in "Ingestion Update" mode.<br>• Graph updates occur correctly without executing unrelated steps. |
| As a developer, I want detailed logging of workflow step execution and errors so that I can easily diagnose and resolve issues. | • Execution status and errors for each workflow step are logged clearly.<br>• Logs contain sufficient context to diagnose issues quickly. |

---

# 7.0 Blarify Workflow Step

## 7.1 Purpose

**BlarifyStep** is a workflow step in the ingestion pipeline that runs [Blarify](https://github.com/blarApp/blarify) in a linux container to parse the codebase and store the raw AST in the **Graph Service** with bindings to the symbol table derived from LSPs by blarify. Blarify directly parses the codebase and generates a graph of the codebase in neo4j. Thus the Blarify Step depends upon the Neo4J Graph Database Service. The BlarifyStep will run in Docker locally or in Azure Container Apps. 

## 7.2 Responsibilities

- Implement the `PipelineStep` interface.
- Run the Blarify tool in a linux container to parse the codebase and store the raw AST and symbol bindings in the **Graph Service**.
- The BlarifyStep will run in a container locally or in Azure Container Apps.
- Estimate the status of the job based on the progress of the Blarify tool.

## 7.3 Code Structure

___TODO___

## 7.4 Testing strategy

- **Unit** - unit tests for each method of the BlarifyStep class.
- **Integration** - integration tests depend on the actual database and Blarify tool. Ensure that the BlarifyStep can be started and stopped successfully. Ensure that the BlarifyStep can be queried successfully. Ensure that the resulting data in the graph database is correct. Use a small known repository for the ingestion testing. 


---

# 8.0 FileSystem Workflow Step

## 8.1 Purpose

**FileSystemStep** is a workflow step in the ingestion pipeline that creates a graph of the filesystem layout of the codebase and links it to the AST+symbol nodes. Its operation is very simple:
- Obtain the filesystem layout of the codebase, and create a corresponding graph of the filesystem layout in Neo4J
- Link the filesystem nodes to the related AST+symbol nodes in the graph database (eg linking a file to the class it implements, or the function it contains, etc.)

The FileSystemStep depends upon the Neo4J Graph Database Service, the BlarifyStep, and the Ingestion Pipeline.

## 8.2 Responsibilities
- Implement the `PipelineStep` interface.
- Create a graph of the filesystem layout of the codebase and link it to the AST+symbol nodes in the **Graph Service**.
- Estimate the status of the job based on the progress of the filesystem graph creation process.

---

# 9.0 Summarizer Workflow Step

## 9.1 Purpose

**Summarizer** is a workflow step in the ingestion pipeline that computes a DAG of code dependencies and walks from leaf nodes to the top and computes natural language English summaries for each AST or filesystem node using an LLM (from the ai module) and stores them in the **Graph Service** with links to the nodes they describe. Each directory or larger module of the code base should have an overall summary as well, along with a top level summary of the whole repository. The Summarizer will run in a container locally or in Azure Container Apps.  Every leaf node shall be processed in parallel up to a configurable limit (default = 5), and the DAG will be traversed in parallel as well. 

## 9.2 Responsibilities

- Implement the `PipelineStep` interface.
- Using the contents of the code, compute natural language English summaries or explanations for each AST or filesystem node.
- Process leaf nodes in parallel up to a configurable limit.
- Store summaries in the **Graph Service** with links to the nodes they describe.
- Compute a top level summary of the whole repository.
- Compute a summary for each directory or larger module of the code base.
- Estimate the status of the job based on the progress of the summarization process.

## 9.3 Architecture and Code Structure

__TODO__

## 9.4 Testing strategy
- **Unit** - unit tests for each method of the Summarizer class.
- **Integration** - integration tests depend on the actual database and OpenAI API. Ensure that the Summarizer can be started and stopped successfully. Ensure that the Summarizer can be queried successfully. Ensure that the resulting data in the graph database is correct. Use a small known repository for the ingestion testing.

---

# 10.0 Documentation Grapher Workflow Step

## 10.1 Purpose

**DocumentationGrapher** is a workflow step in the ingestion pipeline that creates a knowledge graph of the documentation and links it to the relevant AST, Filesystem, and Summary nodes. It searches the repository for any documentation files (e.g., README, markdown files, etc.) and parses them to extract relevant information. The extracted information is then stored in the **Graph Service** with links to the parts of the software that they describe. 

## 10.2 Responsibilities
- Implement the `PipelineStep` interface.
- Search the repository for any documentation files (e.g., README, markdown files, etc.) and parse them to extract relevant information.
- Create a knowledge graph of the documentation and link it to the relevant AST, Filesystem, and Summary nodes in the **Graph Service**.

## 10.3 Code Structure

___TODO___

## 10.4 Testing strategy
- **Unit** - unit tests for each method of the DocumentationGrapher class.
- **Integration** - integration tests depend on the actual database and OpenAI API. Ensure that the DocumentationGrapher can be started and stopped successfully. Ensure that the DocumentationGrapher can be queried successfully. Ensure that the resulting data in the graph database is correct. Use a small known repository for the ingestion testing.

---



# 11.0 Code Story Service

## 11.1 Purpose

Provide a self‑hosted API service that is responsible for running the ingestion pipeline and exposing the graph service to the CLI, GUI, and MCP adapter. It will also handle the OpenAI API calls for LLM inference.  This will depend upon other components such as the Graph Database Service, Ingestion Pipeline, and OpenAI Client.  It will run in a container locally or in Azure Container Apps. The code-story service uses the **Ingestion Pipeline** library to run the ingestion pipeline and the **Graph Database Service** to query the graph database. The code-story service will also handle authentication and authorization for the REST API using Entra-ID or tokens embedded in the environment when in local dev mode. 

## 11.2 Responsibilities

- Expose a REST API for the MCP, CLI, and GUI to interact with the graph service. Including:
  - support for querying and managing graph data
  - authentication mechanisms
  - start, stop, manage status of ingestion jobs
  - manage configuration and secrets
  - health check endpoint for service, ingestion, database, and OpenAI API
  - local dev mode with token auth passed to clients through the environment
- logging and monitoring capabilities
- error handling and response formatting
- Docker container and compose file to run the service and its dependencies.
- Start and Stop scripts for the service and its supporting services.

## 11.3 Architecture and Code Structure

__TODO__

## 11.4 API Endpoints

__TODO__

## 11.5 User Stories and Acceptance Criteria

| User Story | Acceptance Criteria |
|------------|---------------------|
| As a developer, I want to be able to run the code-story service in a container so that I can develop and test the service locally. | • The code-story service can be started and stopped using the provided scripts.<br>• The code-story service can be queried using the REST API. |
| As a developer, I want to be able to run the code-story service in Azure Container Apps so that I can deploy the service in Azure. | • The code-story service can be started and stopped using the provided scripts.<br>• The code-story service can be queried using the REST API. |
| As a developer, I want to query and manage graph data using cypher queries through a REST API so that I can interact with the graph service programmatically. | • The REST API provides endpoints for querying and managing graph data with cypher queries.<br>• Queries return correctly formatted responses. |
| As a developer, I want Entra-ID authentication mechanisms for the REST API so that I can secure access to the graph service. | • The REST API endpoints require valid authentication tokens.<br>• Unauthorized requests are rejected with appropriate HTTP status codes. |
| As a developer, I want to start, stop, and manage the status of ingestion jobs via the REST API so that I can control ingestion workflows. | • The REST API provides endpoints to start, stop, and check the status of ingestion jobs.<br>• Job statuses are accurately reported. |
| As a developer, I want to manage configuration and secrets through the REST API so that I can dynamically adjust service settings. | • The REST API provides endpoints to retrieve and update configuration and secrets.<br>• Configuration changes take effect without service restarts when possible. |
| As a developer, I want a health check endpoint so that I can verify the operational status of the service, ingestion pipeline, database, and OpenAI API. | • The health check endpoint accurately reports the status of all components.<br>• Health check responses clearly indicate the status of each component. |
| As a developer, I want logging and monitoring capabilities so that I can observe and troubleshoot the service effectively. | • Logs are generated for key events and errors.<br>• Monitoring metrics are exposed for integration with observability tools. |
| As a developer, I want consistent error handling and response formatting so that I can reliably handle API responses. | • Errors are returned with clear, consistent formatting.<br>• API responses follow a documented schema. |
| As a developer, I want a local development mode with token authentication passed through the environment so that I can easily test the service locally. | • Local development mode can be enabled via configuration.<br>• Authentication tokens are correctly passed and validated in local mode. |


## 11.6 Testing Strategy

- **Unit** - unit tests for each method of API
- **Integration** - integration tests depend on the actual database and OpenAI API. Ensure that the service can be started and stopped successfully. Ensure that the service can be queried successfully. Ensure that the service can be queried with cypher queries successfully. Validate all acceptance criteria.

## 11.7 Implementation Steps

1. install dependencies __TODO__
2. implement each code file
3. ensure all components are integrated and functioning as expected.
4. ensure all tests pass
5. ensure all acceptance criteria are met

---
# 12.0 MCP Adapter

## 12.1 Purpose

*MCP Adapter* exposes the graph service to LLM agents [secured by Entra ID](https://den.dev/blog/auth-modelcontextprotocol-entra-id/) using the [mcp-neo4j-cypher](https://github.com/neo4j-contrib/mcp-neo4j/tree/main/servers/mcp-neo4j-cypher) adapter. 

## 12.2 Responsibilities

| ID     | Description                                                                                                                                                                                                                |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| MCP-R1 | Implement MCP Tool Server spec (gRPC + HTTP) backed by GraphService queries.                                                                                                                                               |
| MCP-R2 | Secure endpoints with Microsoft Entra ID (MSAL) using auth flow described in [https://den.dev/blog/auth-modelcontextprotocol-entra-id/](https://den.dev/blog/auth-modelcontextprotocol-entra-id/) (bearer JWT validation). |
| MCP-R3 | Map high‑level MCP tool names to Cypher queries and vector searches: `searchGraph`, `summarizeNode`, `pathTo`, `similarCode`.                                                                                              |
| MCP-R4 | Provide usage quota & basic analytics (requests, latency) exposed via Prometheus. |                                                                                                             
### 12.3 Testing Strategy

* **Unit** – mock GraphSCode Story Service; test each tool handler returns expected payload.
* **Auth** – generate signed JWT with test key; ensure `auth.verify` accepts valid token and rejects invalid scope.
* **Integration** – compose NeoCode Story Service + MCP; Validate data access through MCP service. 

---

# 13.0 CLI

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

## 13.4 Testing

- **Unit** - ensure cli commands parse and invoke the correct methods
- **Integration** - run CLI commands against a real Code-story instance; validate output format and data integrity.

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

# 14.0 GUI

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

__TODO__

## 14.5 Implementation Steps

1. `pnpm create vite gui --template react-ts`
2. Add deps: `redux toolkit`, `react-redux`, `mantine`, `@vasturiano/force-graph`, `three`, `axios`.
3. Set up RTK store slices: `graphApi`, `ingestApi`, `configSlice`.
4. Build `GraphViewer` component that queries `/v1/query` for subgraph, feeds to force‑graph, and opens side‑panel on click.
5. Build `IngestionPanel` subscribing to WebSocket `/ws/status`.
6. Config editor writes JSON to `/v1/config` which CLI & services read.
7. Deploy dev server on port 5173; include Dockerfile `gui.Dockerfile` for production build.

## 14.6 User Stories and Acceptance Criteria

| User Story | Acceptance Criteria |
|------------|---------------------|
| As a developer, I want to visualize the Neo4j graph in 3D so that I can understand the relationships between nodes and edges. | • The GUI displays a 3D force-directed graph of the Neo4j database.<br>• Nodes and edges show metadata on hover/click. |
| As a developer, I want to start and monitor ingestion runs so that I can track the progress of the ingestion process. | • The GUI provides a dashboard to start ingestion runs.<br>• The GUI shows progress per step in the ingestion process. |
| As a developer, I want to edit the configuration settings so that I can customize the behavior of the code-story service. | • The GUI provides a form to edit configuration settings.<br>• Changes are saved to `.env` or `.codestory.toml` file. |
| As a developer, I want to issue MCP tool calls and view the JSON responses so that I can interact with the graph service programmatically. | • The GUI provides a playground tab to issue MCP tool calls.<br>• The GUI displays the JSON responses in a readable format. |
| As a developer, I want to ask natural language questions about the graph and get answers back so that I can interact with the graph service in a more intuitive way. | • The GUI provides a tab to ask natural language questions.<br>• The GUI displays the answers in a readable format. |


---

# 15.0 Infra Module

## 15.1 Purpose

Provide infrastructure‑as‑code for local Docker‑Compose **and** Azure Container Apps deployment.

## 15.2 Deliverables

* simple script for starting everything locally
* `azd` setup for deploying to azure
* `docker-compose.yaml` (services: neo4j, redis, worker, mcp, gui)
* `Dockerfile` for Python services; `Dockerfile.gui`
* `bicep/*.bicep` template deploying services + secrets mapping
* `devcontainer.json` for Codespaces/local VS Code

## 15.3 Implementation Steps

__TODO__

### 15.4 Acceptance Criteria

* `azd up` succeeds.
__TODO__


---

# 16.0 Docs

## 16.1 Purpose

Generate Sphinx documentation from code docstrings and Markdown files in `docs/` folder.

__TODO__

---
