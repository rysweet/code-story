# Shell Command History

## May 6, 2025
- `git checkout -b claude-1st-impl` - Creating a new branch for implementation
- `ls -la` - Listing project files to understand current structure
- `mkdir -p Specifications` - Creating the Specifications directory for tracking progress and status
- `mkdir -p .devcontainer .github/workflows docs/{api,architecture,user_guides,developer_guides} gui/{src,public} infra/{docker,scripts,azure} prompts scripts src/codestory/{config,graphdb,llm,ingestion_pipeline,cli} src/codestory_service src/codestory_blarify src/codestory_filesystem src/codestory_summarizer src/codestory_docgrapher tests/{unit,integration}` - Creating directory structure according to specification
- `ls -la src` - Checking the src directory structure
- `ls -la src/codestory` - Checking the codestory directory structure
- `chmod +x scripts/bootstrap.sh` - Making bootstrap script executable

## May 7, 2025
- `python -m pytest tests/unit/test_config.py::test_get_config_value -v` - Running the specific test_get_config_value test
- `python -m pytest tests/unit/test_config.py -v` - Running all tests in the configuration module
- `python -m pytest tests/unit/test_config_export.py -v` - Running tests for configuration export functionality
- `python -m pytest tests/unit/test_config_writer.py -v` - Running tests for configuration writer functionality
- `python -m pytest tests/unit/test_config.py tests/unit/test_config_export.py tests/unit/test_config_writer.py -v` - Running all configuration-related tests
- `python -m pytest` - Running all tests in the project
- `python -m pytest tests/unit/` - Running all unit tests in the project
- `mkdir -p src/codestory/graphdb` - Creating the graphdb directory for the Graph Database module