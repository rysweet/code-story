# Shell Command History

## May 22, 2025 (Comprehensive Logging for Azure OpenAI Diagnostics)
- `codestory stop` - Stop all Code Story services using docker compose down
- `docker compose build` - Rebuild Docker images with updated code

## May 20, 2025 (Ingestion Pipeline Parameter Filtering)
- `cd /Users/ryan/src/msec/code-story && find tests -name "test_*.py" | grep -i ingestion` - Find ingestion-related test files
- `cd /Users/ryan/src/msec/code-story && git status` - Check git status
- `cd /Users/ryan/src/msec/code-story && python -m pytest tests/integration/test_ingestion_pipeline/test_filesystem_simple.py -v` - Run filesystem simple test
- `cd /Users/ryan/src/msec/code-story && python -m pytest tests/integration/test_ingestion_pipeline/test_filesystem_direct.py -v` - Run filesystem direct test
- `cd /Users/ryan/src/msec/code-story && python -m pytest tests/unit/test_codestory_service/test_infrastructure.py::TestCeleryAdapter::test_parameter_filtering -v` - Run parameter filtering test
- `cd /Users/ryan/src/msec/code-story && python -m pytest tests/integration/test_ingestion_pipeline/test_filesystem_simple.py -v` - Run simple filesystem test again
- `cd /Users/ryan/src/msec/code-story && git add src/codestory_service/infrastructure/celery_adapter.py src/codestory/ingestion_pipeline/tasks.py specs/06-ingestion-pipeline/ingestion-pipeline.md tests/unit/test_codestory_service/test_infrastructure.py` - Stage all changes
- `cd /Users/ryan/src/msec/code-story && git commit -m "Add parameter filtering to CeleryAdapter and ingestion pipeline tasks"` - Commit changes
- `cd /Users/ryan/src/msec/code-story && git push origin llm-ingestion-pipeline` - Push changes
- `cd /Users/ryan/src/msec/code-story && bash scripts/check_ci_status.sh` - Check CI status
- `cd /Users/ryan/src/msec/code-story && gh run view 15150025165 --log-failed` - Check failed CI logs

## May 19, 2025 (OpenAI Adapter Resilience Enhancement)
- `cd /Users/ryan/src/msec/code-story && python -m pytest -v` - Run all pytest tests in the project
- `cd /Users/ryan/src/msec/code-story && python -m pytest tests/unit -v` - Run only unit tests
- `cd /Users/ryan/src/msec/code-story && python -m pytest tests/unit/test_llm/test_client.py -v` - Run unit tests for the OpenAI client
- `cd /Users/ryan/src/msec/code-story && python -m pytest tests/unit/test_llm/test_metrics.py -v` - Run unit tests for the LLM metrics
- `cd /Users/ryan/src/msec/code-story && python -m pytest tests/unit/test_llm/test_backoff.py -v` - Run unit tests for the LLM backoff functionality
- `cd /Users/ryan/src/msec/code-story && python -m pytest tests/integration/test_llm/test_client_integration.py -v` - Run integration tests for the LLM client
- `cd /Users/ryan/src/msec/code-story && python -m pytest tests/unit/test_codestory_service/test_infrastructure.py -v` - Run tests for the OpenAI adapter in the service
- `cd /Users/ryan/src/msec/code-story && python -m pytest tests/unit/test_llm/ -v` - Run all unit tests for the LLM module
- `cd /Users/ryan/src/msec/code-story && git status` - Check git status
- `cd /Users/ryan/src/msec/code-story && git add src/codestory_service/infrastructure/openai_adapter.py tests/unit/test_codestory_service/test_infrastructure.py` - Add changed files
- `cd /Users/ryan/src/msec/code-story && python -m pytest tests/unit/test_llm/ tests/unit/test_codestory_service/test_infrastructure.py -v` - Run relevant tests
- `cd /Users/ryan/src/msec/code-story && python -m ruff format src/codestory_service/infrastructure/openai_adapter.py` - Format the changed file
- `cd /Users/ryan/src/msec/code-story && git push origin llm-ingestion-pipeline` - Push changes to remote
- `cd /Users/ryan/src/msec/code-story && gh pr checks 13` - Check PR status

## May 16, 2025 (Azure Authentication Resilience Implementation)
- `cd /Users/ryan/src/msec/code-story && ls -la scripts/ingest_script.py` - Checking if the ingest script already exists
- `cd /Users/ryan/src/msec/code-story && ls -la scripts/mount_repository.sh` - Checking if mount_repository.sh exists and is executable
- `cd /Users/ryan/src/msec/code-story && ls -la ~/repositories` - Checking for available repositories or creating directory
- `cd /Users/ryan/src/msec/code-story && docker-compose ps` - Checking the status of containers
- `cd /Users/ryan/src/msec/code-story && chmod +x /Users/ryan/src/msec/code-story/scripts/ingest_script.py` - Making the ingest script executable
- `cd /Users/ryan/src/msec/code-story && mkdir -p /Users/ryan/src/msec/code-story/tests/unit/test_scripts` - Creating test directory structure
- `cd /Users/ryan/src/msec/code-story && python -m unittest tests/unit/test_scripts/test_ingest_script.py` - Testing ingest script functionality
- `cd /Users/ryan/src/msec/code-story && docker-compose ps` - Checking final container status

## May 16, 2025 (Fixing Integration Test Failures)
- `cd /Users/ryan/src/msec/code-story && python3 scripts/check_ci_status.sh` - Trying to check CI status with Python script
- `cd /Users/ryan/src/msec/code-story && bash scripts/check_ci_status.sh` - Checking CI status with bash script
- `cd /Users/ryan/src/msec/code-story && gh run view 15075546551 --log-failed` - Checking detailed logs for failed CI run
- `cd /Users/ryan/src/msec/code-story && cat /Users/ryan/src/msec/code-story/tests/integration/test_ingestion_pipeline/test_filesystem_integration.py` - Examining failing test file
- `cd /Users/ryan/src/msec/code-story && cat /Users/ryan/src/msec/code-story/tests/integration/conftest.py` - Checking integration test configuration
- `cd /Users/ryan/src/msec/code-story && cat /Users/ryan/src/msec/code-story/src/codestory/ingestion_pipeline/celery_app.py` - Checking Celery app implementation
- `cd /Users/ryan/src/msec/code-story && cat /Users/ryan/src/msec/code-story/tests/unit/conftest.py` - Examining unit test fixture setup

## May 15, 2025 (Fixing Mount Verification Issues)
- `cd /Users/ryan/src/msec/code-story && docker inspect codestory-service --format '{{json .Mounts}}'` - Inspecting actual container mounts
- `cd /Users/ryan/src/msec/code-story && docker exec codestory-service ls -la /repositories` - Checking accessible repositories in container
- `cd /Users/ryan/src/msec/code-story && docker-compose down` - Stopping containers for remounting
- `cd /Users/ryan/src/msec/code-story && codestory ingest start . --auto-mount` - Testing updated CLI with auto-mount
- `cd /Users/ryan/src/msec/code-story && python scripts/auto_mount.py . --debug --force-remount` - Testing improved auto-mount script with debugging
- `cd /Users/ryan/src/msec/code-story && cat docker-compose.override.yml` - Checking generated override file with specific mounts
- `cd /Users/ryan/src/msec/code-story && grep -n "REPOSITORY_PATH" docker-compose.yml` - Finding repository path references

## May 15, 2025 (Testing Auto-Mount Functionality)
- `cd /Users/ryan/src/msec/code-story && mkdir -p tests/unit/test_cli/test_scripts` - Creating test directory structure
- `cd /Users/ryan/src/msec/code-story && python -m pytest -xvs tests/unit/test_cli/test_commands/test_auto_mount.py` - Running unit tests for auto-mount
- `cd /Users/ryan/src/msec/code-story && python -m pytest -xvs tests/unit/test_cli/test_scripts/test_auto_mount_script.py` - Running unit tests for auto_mount.py script
- `cd /Users/ryan/src/msec/code-story && python -m pytest -xvs tests/integration/test_cli/test_repository_mounting.py -k "test_auto_mount_script"` - Running integration test for auto-mount script
- `cd /Users/ryan/src/msec/code-story && docker-compose down` - Cleaning up Docker containers after tests

## May 15, 2025 (Full Repository Mounting Automation)
- `cd /Users/ryan/src/msec/code-story && codestory ingest start .` - Testing ingest command with initial mount issue
- `cd /Users/ryan/src/msec/code-story && docker ps` - Checking running containers
- `cd /Users/ryan/src/msec/code-story && docker inspect codestory-service --format '{{json .Mounts}}'` - Checking service container mounts
- `cd /Users/ryan/src/msec/code-story && python scripts/auto_mount.py .` - Testing new auto-mount script
- `cd /Users/ryan/src/msec/code-story && chmod +x scripts/auto_mount.py` - Making auto-mount script executable
- `cd /Users/ryan/src/msec/code-story && pip install -e .` - Installing package with new auto-mount feature
- `cd /Users/ryan/src/msec/code-story && docker-compose down` - Stopping containers for testing
- `cd /Users/ryan/src/msec/code-story && codestory ingest start . --auto-mount` - Testing explicit auto-mount flag
- `cd /Users/ryan/src/msec/code-story && docker exec codestory-service ls -la /repositories` - Checking mounted repositories in container

## May 15, 2025 (Repository Mounting Fix)
- `cd /Users/ryan/src/msec/code-story && codestory ingest start .` - Testing ingest command to reproduce repository mounting issue
- `cd /Users/ryan/src/msec/code-story && cat docker-compose.yml | grep -A2 volume` - Checking Docker volume mounts
- `cd /Users/ryan/src/msec/code-story && cat scripts/mount_repository.sh` - Reviewing the repository mount script
- `cd /Users/ryan/src/msec/code-story && cat src/codestory/cli/commands/ingest.py | grep -A10 start_ingestion` - Examining ingest command implementation
- `cd /Users/ryan/src/msec/code-story && cat docs/deployment/repository_mounting.md` - Reviewing mount documentation
- `cd /Users/ryan/src/msec/code-story && pip install -e .` - Installing package in development mode
- `cd /Users/ryan/src/msec/code-story && ./scripts/mount_repository.sh . --restart` - Testing enhanced mount script with restart
- `cd /Users/ryan/src/msec/code-story && codestory ingest start . --container` - Testing with container flag

## May 15, 2025 (Console Debug Bug Fix)
- `cd /Users/ryan/src/msec/code-story && python -m codestory.cli.run ingest /some/path` - Testing ingest command to reproduce the bug
- `cd /Users/ryan/src/msec/code-story && grep -r "console.debug" src/` - Finding all instances of console.debug() in the codebase
- `cd /Users/ryan/src/msec/code-story && grep -r "Console" tests/unit` - Checking how Console is mocked in tests
- `cd /Users/ryan/src/msec/code-story && pip install -e .` - Installing package in development mode to test fix
- `cd /Users/ryan/src/msec/code-story && python -m pytest -xvs tests/unit/test_cli/client/test_service_client.py` - Running new unit tests
- `cd /Users/ryan/src/msec/code-story && python -m codestory.cli.run ingest /some/path` - Testing command after fix
- `cd /Users/ryan/src/msec/code-story && git add src/codestory/cli/client/service_client.py` - Staging the bug fix
- `cd /Users/ryan/src/msec/code-story && git commit -m "Fix console.debug() calls in ServiceClient"` - Committing the bug fix
- `cd /Users/ryan/src/msec/code-story && git add tests/unit/test_cli/client/__init__.py tests/unit/test_cli/client/test_service_client.py` - Staging the new tests
- `cd /Users/ryan/src/msec/code-story && git commit -m "Add tests to catch invalid Console API usage"` - Committing new tests

## May 15, 2025 (CLI Improvements)
- `cd /Users/ryan/src/msec/code-story && python -m codestory.cli.run invalidcommand` - Testing invalid command behavior
- `cd /Users/ryan/src/msec/code-story && python test_cli.py invalidcommand` - Testing invalid command behavior with direct script
- `cd /Users/ryan/src/msec/code-story && pip install -e .` - Installing package in development mode
- `cd /Users/ryan/src/msec/code-story && python test_cli.py invalidcommand` - Testing invalid command behavior with updated class
- `cd /Users/ryan/src/msec/code-story && codestory invalidcommand` - Testing installed CLI with invalid command
- `cd /Users/ryan/src/msec/code-story && codestory service badcommand` - Testing subcommand error handling
- `cd /Users/ryan/src/msec/code-story && codestory service stat` - Testing subcommand similar name
- `cd /Users/ryan/src/msec/code-story && git status` - Checking git status
- `cd /Users/ryan/src/msec/code-story && git diff` - View the changes to be committed
- `cd /Users/ryan/src/msec/code-story && ls -l test_cli.py` - Check the untracked test_cli.py file
- `cd /Users/ryan/src/msec/code-story && git add src/codestory/cli/main.py src/codestory/cli/run.py` - Stage the main CLI files
- `cd /Users/ryan/src/msec/code-story && git commit -m "Improve CLI error handling and command discovery"` - Creating commit with detailed message
- `cd /Users/ryan/src/msec/code-story && git log -1 --stat` - View the commit details

## May 15, 2025 (CI Test Fixes - Second Attempt)
- `cd /Users/ryan/src/msec/code-story && python -m pytest -xvs tests/unit/test_cli/test_main.py::TestCliMain::test_no_command_shows_help` - Testing modified conftest.py
- `cd /Users/ryan/src/msec/code-story && git add tests/integration/conftest.py` - Staging fixed conftest.py
- `cd /Users/ryan/src/msec/code-story && git commit -m "Fix syntax error in conftest.py Neo4j port configuration"` - Committing conftest.py fix
- `cd /Users/ryan/src/msec/code-story && git push origin cli-implementation` - Pushing conftest.py fix

## May 15, 2025 (CI Test Fixes - First Attempt)
- `cd /Users/ryan/src/msec/code-story && scripts/check_ci_status.sh` - Checking CI status for the branch
- `cd /Users/ryan/src/msec/code-story && gh run view 15057372896` - Viewing details of the failed CI run
- `cd /Users/ryan/src/msec/code-story && gh run view 15057372896 --log-failed` - Viewing logs of failed CI steps
- `cd /Users/ryan/src/msec/code-story && grep -r "localhost:7688" --include="*.py" .` - Finding files with incorrect Neo4j port
- `cd /Users/ryan/src/msec/code-story && chmod +x ci_test_fix.py` - Making CI test fix script executable
- `cd /Users/ryan/src/msec/code-story && python ci_test_fix.py` - Running script to fix Neo4j port configuration
- `cd /Users/ryan/src/msec/code-story && git add ci_test_fix.py FIXED_CI_TESTS.md` - Staging CI test fix files
- `cd /Users/ryan/src/msec/code-story && git status` - Checking git status
- `cd /Users/ryan/src/msec/code-story && git add scripts/run_filesystem_test.py scripts/run_test_directly.py tests/integration/conftest.py tests/integration/test_config.py tests/integration/test_config_api.py tests/integration/test_graphdb/test_neo4j_connectivity.py tests/integration/test_graphdb/test_neo4j_integration.py tests/integration/test_ingestion_pipeline/test_blarify_integration.py tests/integration/test_ingestion_pipeline/test_docgrapher_integration.py tests/integration/test_ingestion_pipeline/test_filesystem_direct.py tests/integration/test_ingestion_pipeline/test_filesystem_integration.py tests/integration/test_ingestion_pipeline/test_full_pipeline_integration.py tests/integration/test_ingestion_pipeline/test_pipeline_integration.py tests/integration/test_ingestion_pipeline/test_summarizer_integration.py` - Adding modified test files
- `cd /Users/ryan/src/msec/code-story && git commit -m "Fix Neo4j port configuration in tests for CI environment"` - Committing CI test fixes
- `cd /Users/ryan/src/msec/code-story && git push origin cli-implementation` - Pushing CI test fixes

## May 15, 2025 (Additional Improvements)
- `cd /Users/ryan/src/msec/code-story && git status` - Checking the status of the repo
- `cd /Users/ryan/src/msec/code-story && git diff docs/deployment/index.md` - Viewing changes to deployment documentation
- `cd /Users/ryan/src/msec/code-story && git diff src/codestory/cli/commands/ingest.py` - Viewing changes to ingestion command
- `cd /Users/ryan/src/msec/code-story && git diff src/codestory_service/infrastructure/celery_adapter.py` - Viewing changes to CeleryAdapter
- `cd /Users/ryan/src/msec/code-story && git add docs/deployment/repository_mounting.md scripts/mount_repository.sh` - Adding repository mounting files
- `cd /Users/ryan/src/msec/code-story && git commit -m "Add repository mounting documentation and script"` - Committing repository mounting changes
- `cd /Users/ryan/src/msec/code-story && git add src/codestory/cli/run.py` - Adding CLI entry point
- `cd /Users/ryan/src/msec/code-story && git commit -m "Add dedicated entry point for CLI to avoid circular imports"` - Committing CLI entry point
- `cd /Users/ryan/src/msec/code-story && git add src/codestory_service/infrastructure/celery_adapter.py` - Adding CeleryAdapter improvements
- `cd /Users/ryan/src/msec/code-story && git commit -m "Refactor CeleryAdapter to require Celery and fix parameter mapping"` - Committing CeleryAdapter changes
- `cd /Users/ryan/src/msec/code-story && git add src/codestory/cli/commands/ingest.py docs/deployment/index.md` - Adding ingest command and deployment docs
- `cd /Users/ryan/src/msec/code-story && git commit -m "Improve error handling in ingest command and update deployment docs"` - Committing ingest and docs changes
- `cd /Users/ryan/src/msec/code-story && git add scripts/run_cli_demo.sh scripts/run_codestory_demo.sh` - Adding demo script improvements
- `cd /Users/ryan/src/msec/code-story && git commit -m "Improve demo scripts with better error handling and sample data import"` - Committing demo script changes
- `cd /Users/ryan/src/msec/code-story && git add src/codestory_service/api/health.py src/codestory_service/settings.py` - Adding health check improvements
- `cd /Users/ryan/src/msec/code-story && git commit -m "Consolidate health check endpoints and improve Redis connection"` - Committing health check changes
- `cd /Users/ryan/src/msec/code-story && git add src/codestory/cli/__init__.py src/codestory/cli/client/service_client.py src/codestory/config/settings.py src/codestory/llm/client.py src/codestory_service/application/graph_service.py src/codestory_service/infrastructure/msal_validator.py src/codestory_service/infrastructure/openai_adapter.py src/codestory_service/main.py` - Adding remaining changes
- `cd /Users/ryan/src/msec/code-story && git commit -m "Fix service client, visualization endpoints, and adapt service components for robust operation"` - Committing remaining changes
- `cd /Users/ryan/src/msec/code-story && git push origin cli-implementation` - Pushing all changes to remote repository

## May 21, 2025 (CLI Demo Verification)

- `pip install -e .` - Install the Code Story CLI in editable mode as specified in cli_demo.md
- `codestory --version` - Verify that the Code Story CLI is installed and available on the PATH as specified in the CLI demo step 2

## May 22, 2025 (Prompt 62)

- No shell commands executed for this prompt## Shell History

### azd auth login --scope https://cognitiveservices.azure.com/.default
# Refreshed Azure authentication token to fix expired credentials for Azure OpenAI access

### python test_azure_openai_config.py  
# Created and ran integration test to verify Azure OpenAI configuration without Docker overhead
# Identified that Azure authentication works but deployment 'o1' returns 404 nginx error
# This confirms the issue is with the Azure OpenAI deployment configuration, not the client code

## May 27, 2025 (Prompt 36 - E501 Line Length Violations Fix)

- `ruff check --select=E501 | head -20` - Check current E501 violations to continue fixing
- `ruff check --select=E501 | wc -l` - Count total remaining E501 violations
- `cd /Users/ryan/src/msec/code-story && sed -n '420p' src/codestory_filesystem/step.py | wc -c` - Check exact character count of line 420
- `grep -c "^## Prompt" /Users/ryan/src/msec/code-story/Specifications/prompt-history.md` - Count total prompts to determine next prompt number
- `find /Users/ryan/src/msec/code-story -name "*.md" -path "*/docs/*" | head -10` - List documentation files
- `grep -rn "TODO\|FIXME\|HACK\|BUG" /Users/ryan/src/msec/code-story/src --include="*.py" | head -20` - Find TODO/FIXME comments using grep

## May 28, 2025 (GitHub Issues Creation for Backlog Items)

- `gh label list` - Check available GitHub labels in repository before creating issues
- `gh issue create --title "Fix Type Safety Issues - Remove type ignore comments" --body "Priority: High..." --label "bug,enhancement"` - Create GitHub issue #16 for type safety fixes
- `gh issue create --title "Implement Comprehensive Azure Authentication Resilience" --body "Priority: High..." --label "enhancement,bug"` - Create GitHub issue #17 for Azure auth resilience
- `gh issue create --title "Add Input Validation and Sanitization for API Endpoints" --body "Priority: High..." --label "enhancement,bug"` - Create GitHub issue #18 for API input validation
- `gh issue create --title "Implement Progress Tracking for Long-Running Operations" --body "Priority: High..." --label "enhancement"` - Create GitHub issue #19 for progress tracking
- `gh issue create --title "Add Retry Logic and Circuit Breakers for External Services" --body "Priority: High..." --label "enhancement,bug"` - Create GitHub issue #20 for retry logic
- `gh label create "auto-backlog" --description "Issues automatically created from backlog analysis" --color "0052cc"` - Create new label for backlog-generated issues
- `gh issue edit 16 --add-label "auto-backlog"` - Add auto-backlog label to issue 16
- `gh issue edit 17 --add-label "auto-backlog" && gh issue edit 18 --add-label "auto-backlog" && gh issue edit 19 --add-label "auto-backlog" && gh issue edit 20 --add-label "auto-backlog"` - Add auto-backlog label to issues 17-20
- `gh issue create --title "Improve CLI Error Messages and User Guidance" --body "Priority: High..." --label "enhancement,auto-backlog"` - Create GitHub issue #21 for CLI error messages
- `gh issue create --title "Implement Configuration Management and Environment-Specific Settings" --body "Priority: Medium..." --label "enhancement,auto-backlog"` - Create GitHub issue #22 for configuration management
- `gh issue create --title "Add Comprehensive Logging and Structured Log Management" --body "Priority: Medium..." --label "enhancement,auto-backlog"` - Create GitHub issue #23 for logging improvements
- `gh issue create --title "Optimize Database Queries and Add Connection Pooling" --body "Priority: Medium..." --label "enhancement,auto-backlog"` - Create GitHub issue #24 for database optimization
- `gh issue create --title "Implement API Rate Limiting and Request Throttling" --body "Priority: Medium..." --label "enhancement,auto-backlog"` - Create GitHub issue #25 for API rate limiting
- `gh issue create --title "Add File Type Detection and Improved Content Processing" --body "Priority: Medium..." --label "enhancement,auto-backlog"` - Create GitHub issue #26 for file type detection
- `gh issue create --title "Implement Comprehensive Testing Strategy and CI/CD Pipeline" --body "Priority: Medium..." --label "enhancement,auto-backlog"` - Create GitHub issue #27 for testing strategy
- `gh issue create --title "Add Caching Layer for Expensive Operations" --body "Priority: Medium..." --label "enhancement,auto-backlog"` - Create GitHub issue #28 for caching layer
- `gh issue create --title "Implement Backup and Disaster Recovery Procedures" --body "Priority: Low..." --label "enhancement,auto-backlog"` - Create GitHub issue #29 for backup procedures
- `gh issue create --title "Add Comprehensive API Documentation with OpenAPI/Swagger" --body "Priority: Low..." --label "documentation,auto-backlog"` - Create GitHub issue #30 for API documentation
- `gh issue create --title "Implement Health Checks and System Monitoring" --body "Priority: Medium..." --label "enhancement,auto-backlog"` - Create GitHub issue #31 for health checks and monitoring
- `gh issue create --title "Add Search and Filtering Capabilities for Graph Data" --body "Priority: Medium..." --label "enhancement,auto-backlog"` - Create GitHub issue #32 for search and filtering
- `gh issue create --title "Implement User Management and Role-Based Access Control" --body "Priority: Low..." --label "enhancement,auto-backlog"` - Create GitHub issue #33 for user management
- `gh issue create --title "Add Export and Import Functionality for Graph Data" --body "Priority: Low..." --label "enhancement,auto-backlog"` - Create GitHub issue #34 for export/import functionality
- `gh issue create --title "Implement Memory Management for Large Codebase Processing" --body "Priority: Medium..." --label "enhancement,auto-backlog"` - Create GitHub issue #35 for memory management
- `gh issue list --label "auto-backlog" --limit 25 --state open --json title` - List all auto-backlog issues to identify missing items
- `gh issue create --title "Implement Multi-Repository Support and Workspace Management" --body "Priority: Medium..." --label "enhancement,auto-backlog"` - Create GitHub issue #36 for multi-repository support
- `gh issue create --title "Implement Incremental Updates and Smart Processing" --body "Priority: Medium..." --label "enhancement,auto-backlog"` - Create GitHub issue #37 for incremental updates
- `gh issue create --title "Implement Custom Analysis Rules and Plugin System" --body "Priority: Medium..." --label "enhancement,auto-backlog"` - Create GitHub issue #38 for custom analysis rules
- `gh issue create --title "Improve Interactive Graph Navigation and Visualization" --body "Priority: Medium..." --label "enhancement,auto-backlog"` - Create GitHub issue #39 for graph navigation
- `gh issue create --title "Create Dashboard and Analytics for Codebase Metrics" --body "Priority: Medium..." --label "enhancement,auto-backlog"` - Create GitHub issue #40 for dashboard analytics
- `gh issue create --title "Implement IDE Plugin Support and Development Tool Integration" --body "Priority: Medium..." --label "enhancement,auto-backlog"` - Create GitHub issue #41 for IDE integration
- `gh issue create --title "Implement Async Operation Management and Task Control" --body "Priority: High..." --label "enhancement,auto-backlog"` - Create GitHub issue #42 for async operation management
- `gh issue create --title "Enhance Ingestion Pipeline Robustness and Recovery" --body "Priority: High..." --label "enhancement,auto-backlog"` - Create GitHub issue #43 for pipeline robustness
