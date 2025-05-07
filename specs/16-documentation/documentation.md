# 16.0 Documentation

**Previous:** [Infrastructure](../15-infra/infra.md) | **Next:** None

**Dependencies:** 
- [Scaffolding](../02-scaffolding/scaffolding.md) 
- All other components (documents them)

**Used by:** End users and developers

## 16.1 Purpose

Provide comprehensive documentation for all aspects of the Code Story project, enabling users, developers, and contributors to understand, use, extend, and maintain the system effectively. Documentation includes API references generated from code docstrings, user guides for CLI and GUI interfaces, developer guides for extending the system, and architecture documentation for understanding the overall design.

## 16.2 Responsibilities

- Generate API documentation from code docstrings using Sphinx with Markdown support
- Provide user-facing guides for CLI and GUI usage
- Document architectural decisions and system design
- Include tutorials and examples for common workflows
- Maintain installation and deployment guides for different environments
- Document contribution processes and guidelines
- Ensure documentation stays in sync with code changes

## 16.3 Documentation Structure

```
docs/
├── _build/                        # Generated documentation output
├── _static/                       # Static assets (images, CSS)
├── _templates/                    # Custom Sphinx templates
├── conf.py                        # Sphinx configuration with Markdown support
├── index.md                       # Main documentation entry point
├── architecture/                  # System architecture documentation
│   ├── index.md                   # Architecture overview
│   ├── components.md              # Component interaction diagrams
│   ├── data_flow.md               # Data flow documentation
│   └── design_decisions.md        # Explanation of key design choices
├── user_guides/                   # End-user documentation
│   ├── index.md                   # User guides overview
│   ├── installation.md            # Installation instructions
│   ├── cli_guide.md               # CLI usage documentation
│   ├── gui_guide.md               # GUI usage documentation
│   └── workflows/                 # Common user workflows
│       ├── ingesting_repo.md      # How to ingest a repository
│       ├── querying_graph.md      # How to query the graph
│       └── configuration.md       # How to configure the system
├── developer_guides/              # Developer-focused documentation
│   ├── index.md                   # Developer guides overview
│   ├── environment_setup.md       # Development environment setup
│   ├── extending/                 # Extension documentation
│   │   ├── pipeline_steps.md      # Creating custom pipeline steps
│   │   ├── mcp_tools.md           # Adding new MCP tools
│   │   └── api_endpoints.md       # Adding new API endpoints
│   └── testing.md                 # Testing guidelines and procedures
├── api/                           # Auto-generated API documentation
│   ├── index.md                   # API documentation overview
│   ├── config.md                  # Configuration module API
│   ├── graphdb.md                 # Graph database service API
│   ├── ingestion_pipeline.md      # Ingestion pipeline API
│   ├── code_story_service.md      # Code Story service API
│   └── mcp_adapter.md             # MCP adapter API
├── deployment/                    # Deployment documentation
│   ├── index.md                   # Deployment overview
│   ├── local.md                   # Local deployment with Docker Compose
│   └── azure.md                   # Azure Container Apps deployment
└── contributing.md                # Contribution guidelines
```

## 16.4 Documentation Toolchain

### 16.4.1 Core Documentation Tools

- **Sphinx** - Primary documentation generator
- **myst-parser** - Markdown parser for Sphinx
- **sphinx-autodoc** - For API documentation from docstrings
- **sphinx-rtd-theme** - ReadTheDocs theme for consistent styling
- **sphinxcontrib-mermaid** - For sequence and architecture diagrams
- **sphinx-copybutton** - For copy buttons on code blocks
- **sphinx-design** - For responsive UI components and cards
- **sphinx-tabs** - For tabbed content (e.g., different OS instructions)

### 16.4.2 Documentation Build Process

1. Documentation is generated from:
   - Code docstrings (Google style format)
   - Dedicated Markdown files in `docs/` directory
   - README files from various components

2. CI/CD pipeline automatically:
   - Builds documentation on every commit
   - Checks for broken links and references
   - Deploys to GitHub Pages on main branch changes

3. Local build process:
   ```bash
   cd docs
   make html      # Build HTML documentation
   make linkcheck # Verify links are valid
   make clean     # Clean build artifacts
   ```

## 16.5 Docstring Standards

All code in the project follows Google-style docstrings for consistency:

```python
def function_with_types_in_docstring(param1: int, param2: str) -> bool:
    """Example function with PEP 484 type annotations.
    
    Args:
        param1: The first parameter.
        param2: The second parameter.
        
    Returns:
        The return value. True for success, False otherwise.
        
    Raises:
        ValueError: If param1 is negative.
    
    Example:
        >>> function_with_types_in_docstring(1, '2')
        True
    """
    if param1 < 0:
        raise ValueError("param1 must be non-negative.")
    return param1 < len(param2)
```

## 16.6 Documentation Types

### 16.6.1 API Reference

Generated automatically from docstrings in Python code and TypeScript/JavaScript using appropriate tools:
- Python API docs via sphinx-autodoc
- TypeScript/JavaScript API docs via TypeDoc

### 16.6.2 User Guides

Written in Markdown to explain how to use the system:
- CLI command reference and examples
- GUI interface walkthrough
- Configuration options and management
- Troubleshooting common issues

### 16.6.3 Developer Guides

Written in Markdown to explain how to extend or modify the system:
- Architecture overviews and component interactions
- Development environment setup
- Testing procedures and guidelines
- Code organization and conventions
- Extending the system (new pipeline steps, API endpoints, etc.)

### 16.6.4 Tutorials and Examples

Step-by-step guides in Markdown for common tasks:
- Ingesting a new repository
- Querying and exploring the graph
- Asking natural language questions
- Creating visualizations
- Extending with custom processing steps

## 16.7 Implementation Steps

1. **Set up documentation framework**
   - Configure Sphinx with myst-parser for Markdown support
   - Set up documentation directory structure
   - Create base templates and index pages

2. **Configure API documentation generation**
   - Set up autodoc to extract docstrings
   - Configure TypeDoc for JavaScript/TypeScript documentation
   - Define appropriate groups and categories

3. **Write core documentation pages**
   - Create installation guides in Markdown
   - Write architecture overview using Mermaid diagrams
   - Document key components and their interactions

4. **Create user guides**
   - Document CLI commands and options
   - Create GUI usage walkthrough with screenshots
   - Write configuration guide

5. **Develop developer documentation**
   - Document code organization
   - Create extension guidelines
   - Write contribution workflow

6. **Set up documentation CI/CD**
   - Configure automatic builds in GitHub Actions
   - Set up GitHub Pages deployment
   - Add documentation status checks to PRs

7. **Create interactive examples**
   - Add runnable code examples where possible
   - Create tutorial notebooks for complex workflows
   - Include sample outputs and screenshots

8. **Review and refine**
   - Perform technical review of all documentation
   - Check for consistency across sections
   - Validate examples and commands
   - Ensure cross-linking between related sections

9. **Verification and Review**
   - Build the complete documentation and test all navigation paths
   - Verify that all API references are accurate and complete
   - Test all examples and code snippets to ensure they work as documented
   - Check that command examples and parameters match actual implementation
   - Verify all links are functional, both internal and external
   - Test documentation on different devices and screen sizes
   - Ensure search functionality works correctly
   - Verify documentation matches the current code state
   - Test that API documentation is properly generated from docstrings
   - Perform thorough review against all user stories and acceptance criteria
   - Test the documentation CI/CD pipeline
   - Make necessary adjustments based on review findings
   - Re-test documentation after any changes
   - Document issues found and their resolutions
   - Create detailed PR for final review

## 16.8 User Stories and Acceptance Criteria

| User Story | Acceptance Criteria |
|------------|---------------------|
| As a new user, I want to quickly understand how to install and use the system so I can get started right away. | • Documentation includes clear installation instructions.<br>• Quick start guide covers the basic workflow.<br>• Prerequisites and system requirements are clearly stated.<br>• Common issues have troubleshooting guidance. |
| As a CLI user, I want comprehensive command reference documentation so I can use all available features. | • All CLI commands are documented with syntax and examples.<br>• Command options and flags are explained.<br>• Common command combinations are illustrated in examples.<br>• Output formats are explained with example outputs. |
| As a GUI user, I want interface documentation so I can navigate and use all GUI features effectively. | • Each GUI screen has annotated screenshots.<br>• Interactive elements are explained.<br>• Common workflows are documented with step-by-step instructions.<br>• Configuration options in the GUI are documented. |
| As a developer, I want clear API documentation so I can understand and use the codebase. | • All public APIs have complete docstring-generated documentation.<br>• Classes, methods, and functions include parameter descriptions.<br>• Return values and exceptions are documented.<br>• Examples show typical usage patterns. |
| As a contributor, I want to understand the architecture so I can effectively extend the system. | • Architecture documentation includes component diagrams.<br>• Data flow between components is explained.<br>• Design patterns and decisions are documented.<br>• Extension points are clearly identified. |
| As a developer, I want to know how to create custom pipeline steps so I can extend the ingestion process. | • Step-by-step guide for creating custom pipeline steps exists.<br>• Interface requirements are clearly documented.<br>• Examples of custom steps are provided.<br>• Testing approach for custom steps is explained. |
| As a system administrator, I want deployment documentation so I can set up the system in different environments. | • Local deployment with Docker Compose is documented.<br>• Azure Container Apps deployment instructions are clear.<br>• Environment variables and configuration options are explained.<br>• Scaling considerations are documented. |
| As a user, I want searchable documentation so I can quickly find what I need. | • Documentation includes a search feature.<br>• Content is properly indexed for searching.<br>• Related topics are cross-linked.<br>• Navigation structure is intuitive. |

## 16.9 Testing Strategy

- **Link Validation** - Ensure all internal and external links are valid
- **Example Testing** - Verify that code examples execute correctly
