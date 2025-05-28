# Code Story CLI Demo Test Plan

## Overview

This document outlines a comprehensive plan for testing the Code Story CLI demo functionality as described in [`docs/demos/cli_demo.md`](docs/demos/cli_demo.md). The plan is organized with proper dependency ordering to ensure systematic validation of all components.

## Dependency Analysis

The system has the following dependency layers (must be resolved in order):

### Layer 1: Infrastructure & Configuration
- Docker environment setup
- Configuration file creation and validation
- Environment variable setup

### Layer 2: Core Services
- Neo4j database connectivity
- Redis connectivity
- Service startup and health checks

### Layer 3: Basic CLI Functionality
- CLI installation verification
- Command availability and help system
- Configuration management commands

### Layer 4: Ingestion Pipeline
- Repository mounting (if applicable)
- Celery worker health
- Ingestion job management

### Layer 5: Core Features
- Database queries (Cypher)
- Natural language queries
- Visualization generation

### Layer 6: Advanced Features
- Database management
- Service lifecycle management
- Integration workflows

## Detailed Test Plan

### Phase 1: Infrastructure Setup (Priority: Critical)

#### 1.1 Environment Preparation
- [ ] **Test**: Verify Docker is installed and running
  - Command: `docker --version && docker ps`
  - Expected: Version info and container list
  - Dependency: None

- [ ] **Test**: Verify project structure exists
  - Check: [`docker-compose.yml`](docker-compose.yml), [`Dockerfile.service`](Dockerfile.service), [`Dockerfile.worker`](Dockerfile.worker)
  - Expected: All Docker configuration files present
  - Dependency: None

#### 1.2 Configuration Setup
- [ ] **Test**: Create configuration from template
  - Command: Copy from [`.env.template`](.env.template) to `.env`
  - Expected: Configuration file created with required settings
  - Dependency: 1.1

- [ ] **Test**: Validate configuration file format
  - Check: Required settings (NEO4J, REDIS, SERVICE endpoints)
  - Expected: All required environment variables present
  - Dependency: 1.2.1

- [ ] **Test**: Docker vs localhost configuration
  - Verify: Docker hostnames (neo4j:7687) vs localhost (localhost:7689)
  - Expected: Appropriate configuration for environment
  - Dependency: 1.2.2

### Phase 2: Service Infrastructure (Priority: Critical)

#### 2.1 Docker Container Health
- [ ] **Test**: Start individual services
  - Command: `docker compose up -d neo4j redis`
  - Expected: Neo4j and Redis containers running
  - Dependency: 1.2

- [ ] **Test**: Neo4j connectivity
  - Command: Test connection to bolt://localhost:7689 or bolt://neo4j:7687
  - Expected: Successful database connection
  - Dependency: 2.1.1

- [ ] **Test**: Redis connectivity  
  - Command: Test connection to redis://localhost:6379 or redis://redis:6379
  - Expected: Successful Redis connection
  - Dependency: 2.1.1

#### 2.2 Service Container Health
- [ ] **Test**: Build and start main service
  - Command: `docker compose up -d service`
  - Expected: Service container running on port 8000
  - Dependency: 2.1

- [ ] **Test**: Build and start worker
  - Command: `docker compose up -d worker`
  - Expected: Celery worker container running
  - Dependency: 2.1

#### 2.3 Service Health Verification
- [ ] **Test**: Service endpoint availability
  - Command: `curl http://localhost:8000/health`
  - Expected: Health check response
  - Dependency: 2.2

### Phase 3: CLI Installation & Basic Commands (Priority: High)

#### 3.1 CLI Installation
- [ ] **Test**: CLI installation verification
  - Command: `codestory --version`
  - Expected: Version output (e.g., "codestory, version 0.1.0")
  - Dependency: 2.3

- [ ] **Test**: Python module fallback
  - Command: `python -m codestory.cli.main --version`
  - Expected: Same version output as above
  - Dependency: 3.1.1

#### 3.2 Help System
- [ ] **Test**: Main help command
  - Command: `codestory --help`
  - Expected: Command list and usage information
  - Dependency: 3.1

- [ ] **Test**: Subcommand help
  - Command: `codestory visualize help`
  - Expected: Detailed visualization help content
  - Dependency: 3.2.1

#### 3.3 Service Management Commands
- [ ] **Test**: Service start command
  - Command: `codestory service start --detach`
  - Expected: Services start successfully
  - Dependency: 3.1

- [ ] **Test**: Service status command
  - Command: `codestory service status`
  - Expected: Status table showing all services healthy
  - Dependency: 3.3.1

- [ ] **Test**: Service restart command
  - Command: `codestory service restart`
  - Expected: Services restart successfully
  - Dependency: 3.3.1

#### 3.4 Configuration Commands
- [ ] **Test**: Configuration display
  - Command: `codestory config show`
  - Expected: Current configuration settings displayed
  - Dependency: 3.3.1

- [ ] **Test**: Configuration shortcuts
  - Command: `codestory cfs` (alias for config show)
  - Expected: Same output as config show
  - Dependency: 3.4.1

### Phase 4: Ingestion Pipeline (Priority: High)

#### 4.1 Repository Mounting (if applicable)
- [ ] **Test**: Repository mount detection
  - Command: Check if auto-mount functionality works
  - Expected: Repository properly mounted for ingestion
  - Dependency: 3.3

#### 4.2 Celery Worker Health
- [ ] **Test**: Worker availability
  - Verify: Celery worker shows as "Healthy" in service status
  - Expected: Worker ready to process jobs
  - Dependency: 3.3.2

#### 4.3 Sample Project Ingestion
- [ ] **Test**: Create sample project
  - Create: Simple Python project in `/tmp/codestory_cli_demo`
  - Expected: Sample files created (hello.py, README.md)
  - Dependency: 4.2

- [ ] **Test**: Start ingestion with progress
  - Command: `codestory ingest start /tmp/codestory_cli_demo`
  - Expected: Real-time progress tracking via Redis
  - Dependency: 4.3.1

- [ ] **Test**: Ingestion without progress
  - Command: `codestory ingest start . --no-progress`
  - Expected: Ingestion starts without progress display
  - Dependency: 4.3.1

#### 4.4 Ingestion Job Management
- [ ] **Test**: List ingestion jobs
  - Command: `codestory ingest jobs` or `codestory ij`
  - Expected: List of current and completed jobs
  - Dependency: 4.3.2

- [ ] **Test**: Ingestion status
  - Command: `codestory ingest status`
  - Expected: Current ingestion status
  - Dependency: 4.3.2

- [ ] **Test**: Stop ingestion job
  - Command: `codestory ingest stop JOB_ID` or `codestory is JOB_ID`
  - Expected: Job stopped successfully
  - Dependency: 4.4.1

### Phase 5: Core Query Features (Priority: High)

#### 5.1 Cypher Queries
- [ ] **Test**: Basic Cypher query
  - Command: `codestory query run "MATCH (f:File) WHERE f.extension = 'py' RETURN f.path LIMIT 5"`
  - Expected: List of Python files
  - Dependency: 4.3.2

- [ ] **Test**: Query shortcuts
  - Command: `codestory q "MATCH (f:File) RETURN count(f)"`
  - Expected: Total file count
  - Dependency: 5.1.1

#### 5.2 Natural Language Queries
- [ ] **Test**: Ask about code functionality
  - Command: `codestory ask "What does the greeting function do?"`
  - Expected: AI-generated response about the function
  - Dependency: 4.3.2

- [ ] **Test**: Ask shortcuts
  - Command: `codestory gs "What Python files are in this project?"`
  - Expected: List of Python files in natural language
  - Dependency: 5.2.1

### Phase 6: Visualization Features (Priority: Medium)

#### 6.1 Visualization Generation
- [ ] **Test**: Generate visualization
  - Command: `codestory visualize generate --output test_viz.html`
  - Expected: HTML visualization file created
  - Dependency: 5.1

- [ ] **Test**: Visualization shortcuts
  - Command: `codestory vz --output test_viz2.html`
  - Expected: HTML visualization file created
  - Dependency: 6.1.1

#### 6.2 Direct API Access
- [ ] **Test**: API endpoint access
  - Command: `curl http://localhost:8000/v1/visualize > api_viz.html`
  - Expected: Visualization downloaded without authentication
  - Dependency: 5.1

- [ ] **Test**: Visualization file validation
  - Check: Generated HTML files are valid and contain expected content
  - Expected: Valid HTML with visualization components
  - Dependency: 6.1, 6.2.1

### Phase 7: Database Management (Priority: Medium)

#### 7.1 Database Commands
- [ ] **Test**: Database help
  - Command: `codestory database --help` or `codestory db --help`
  - Expected: Database command options
  - Dependency: 3.1

- [ ] **Test**: Database clear with confirmation
  - Command: `codestory database clear` (respond 'n' to not actually clear)
  - Expected: Confirmation prompt shown
  - Dependency: 5.1

- [ ] **Test**: Database clear shortcuts
  - Command: `codestory dbc --force` (in test environment only)
  - Expected: Database cleared without confirmation
  - Dependency: 7.1.2

### Phase 8: End-to-End Demo Scripts (Priority: Medium)

#### 8.1 Sample Project Demo Script
- [ ] **Test**: Run sample project demo
  - Command: `./scripts/run_cli_demo.sh`
  - Expected: Complete workflow from start to finish
  - Dependency: All previous phases

#### 8.2 CodeStory Codebase Demo Script
- [ ] **Test**: Run CodeStory demo
  - Command: `./scripts/run_codestory_demo.sh`
  - Expected: Complete workflow with larger dataset
  - Dependency: All previous phases

### Phase 9: Advanced Features & Edge Cases (Priority: Low)

#### 9.1 Error Handling
- [ ] **Test**: Service connection failures
  - Scenario: Stop services and try CLI commands
  - Expected: Graceful error messages
  - Dependency: 3.3

- [ ] **Test**: Invalid queries
  - Command: `codestory query run "INVALID CYPHER"`
  - Expected: Clear error message
  - Dependency: 5.1

#### 9.2 Authentication & Security
- [ ] **Test**: Unauthenticated visualization access
  - Verify: Visualization endpoint works without auth
  - Expected: Access granted for visualization
  - Dependency: 6.2

- [ ] **Test**: Protected endpoint access
  - Verify: Ingestion endpoints require authentication
  - Expected: Proper authentication enforcement
  - Dependency: 4.3

#### 9.3 Performance & Scalability
- [ ] **Test**: Large repository ingestion
  - Test: Ingest a larger codebase
  - Expected: System handles larger datasets appropriately
  - Dependency: 4.3

## Issue Categories & Prioritization

### Critical Issues (Must Fix Before Any Demo)
- Service startup failures
- Database connectivity problems
- CLI installation issues
- Basic command execution failures

### High Priority Issues (Fix Before Full Demo)
- Ingestion pipeline failures
- Query execution problems
- Progress tracking issues
- Worker health problems

### Medium Priority Issues (Fix Before Production)
- Visualization generation failures
- Database management issues
- Demo script failures
- API endpoint access problems

### Low Priority Issues (Enhancement/Polish)
- Error message improvements
- Performance optimizations
- Advanced feature edge cases
- Documentation updates

## Execution Strategy

1. **Sequential Testing**: Execute phases in order due to dependencies
2. **Stop on Critical Failures**: Don't proceed if critical infrastructure fails
3. **Document All Issues**: Track every problem found with reproduction steps
4. **Environment Isolation**: Test in clean environment to avoid state issues
5. **Automated Validation**: Where possible, create scripts to validate functionality

## Success Criteria

- [ ] All CLI commands work as documented
- [ ] Demo scripts run successfully end-to-end
- [ ] Ingestion pipeline processes repositories correctly
- [ ] Queries return expected results
- [ ] Visualizations generate properly
- [ ] Error handling is graceful and informative
- [ ] Documentation accurately reflects system behavior

## Test Environment Requirements

- Docker and Docker Compose installed
- Python 3.12+ with Poetry
- Network access for downloading dependencies
- Sufficient disk space for Neo4j database
- Ports 7689, 6379, 8000 available
- OpenAI API key (for AI features)