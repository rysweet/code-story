"""Comprehensive end-to-end integration tests for filesystem ingestion.

This module provides comprehensive validation of the filesystem ingestion step,
including real-world scenarios, edge cases, and performance validation.
"""
import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from unittest.mock import patch

import pytest
from neo4j import GraphDatabase

from codestory.cli.main import main as cli_main
from codestory.config.settings import get_settings
from codestory.graphdb.neo4j_connector import Neo4jConnector

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class FilesystemIngestionTestHelper:
    """Helper class for filesystem ingestion testing."""

    def __init__(self: Any, test_repo_path: Path) -> None:
        self.test_repo_path = test_repo_path
        self.ingestion_logs: List[str] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def create_test_repository(self: Any) -> None:
        """Create a comprehensive test repository structure."""
        logger.info(f"Creating test repository at {self.test_repo_path}")
        dirs = [
            "src/main/python",
            "src/main/javascript",
            "src/test/unit",
            "src/test/integration",
            "docs/api",
            "docs/guides",
            "config/environments",
            "scripts/deployment",
            "data/samples",
            "node_modules/some-package",
            ".git/objects",
            "build/output",
            "deep/nested/directory/structure/level5/level6/level7/level8/level9/level10",
            "empty_directory",
            "unicode_测试_directory",
            "directory with spaces",
            "special-chars_!@#$%^&()_directory",
        ]
        for dir_path in dirs:
            (self.test_repo_path / dir_path).mkdir(parents=True, exist_ok=True)
        gitignore_content = "\n# Compiled Python files\n*.pyc\n__pycache__/\n*.pyo\n*.pyd\n\n# Node modules\nnode_modules/\nnpm-debug.log*\n\n# Build directories\nbuild/\ndist/\n*.egg-info/\n\n# IDE files\n.vscode/\n.idea/\n*.swp\n*.swo\n\n# OS files\n.DS_Store\nThumbs.db\n\n# Git directory\n.git/\n\n# Log files\n*.log\nlogs/\n\n# Temporary files\n*.tmp\n*.temp\ntemp/\n\n# Large files (for testing)\n*.large\n        ".strip()
        (self.test_repo_path / ".gitignore").write_text(gitignore_content)
        self._create_python_files()
        self._create_javascript_files()
        self._create_documentation_files()
        self._create_config_files()
        self._create_data_files()
        self._create_ignored_files()
        self._create_edge_case_files()
        self._create_large_files()
        self._create_symlinks()
        logger.info(
            f"Test repository created with {len(list(self.test_repo_path.rglob('*')))} total items"
        )

    def _create_python_files(self: Any) -> None:
        """Create Python source files."""
        (self.test_repo_path / "src/main/python/app.py").write_text(
            '"""Main application module."""\n\nimport os\nimport sys\nfrom typing import List, Dict, Optional\n\nclass DataProcessor:\n    """Process various types of data."""\n    \n    def __init__(self, config: Dict[str, str]):\n        self.config = config\n        \n    def process_data(self, data: List[str]) -> Optional[Dict[str, int]]:\n        """Process input data and return statistics."""\n        if not data:\n            return None\n            \n        return {\n            "total_items": len(data),\n            "total_length": sum(len(item) for item in data),\n            "unique_items": len(set(data))\n        }\n\ndef main():\n    """Main entry point."""\n    processor = DataProcessor({"mode": "production"})\n    result = processor.process_data(["test", "data", "items"])\n    print(f"Processing result: {result}")\n\nif __name__ == "__main__":\n    main()\n'
        )
        (self.test_repo_path / "src/main/python/utils.py").write_text(
            '"""Utility functions."""\n\nimport json\nimport logging\nfrom pathlib import Path\nfrom typing import Any, Dict\n\nlogger = logging.getLogger(__name__)\n\ndef load_config(config_path: Path) -> Dict[str, Any]:\n    """Load configuration from JSON file."""\n    try:\n        with open(config_path, \'r\') as f:\n            return json.load(f)\n    except FileNotFoundError:\n        logger.warning(f"Config file not found: {config_path}")\n        return {}\n    except json.JSONDecodeError as e:\n        logger.error(f"Invalid JSON in config file: {e}")\n        return {}\n\ndef save_data(data: Dict[str, Any], output_path: Path) -> bool:\n    """Save data to JSON file."""\n    try:\n        with open(output_path, \'w\') as f:\n            json.dump(data, f, indent=2)\n        return True\n    except Exception as e:\n        logger.error(f"Failed to save data: {e}")\n        return False\n'
        )
        (self.test_repo_path / "src/test/unit/test_app.py").write_text(
            '"""Unit tests for app module."""\n\nimport pytest\nfrom src.main.python.app import DataProcessor\n\nclass TestDataProcessor:\n    """Test cases for DataProcessor class."""\n    \n    def test_process_data_empty_input(self):\n        """Test processing with empty input."""\n        processor = DataProcessor({})\n        result = processor.process_data([])\n        assert result is None\n        \n    def test_process_data_valid_input(self):\n        """Test processing with valid input."""\n        processor = DataProcessor({})\n        result = processor.process_data(["a", "b", "c"])\n        \n        assert result is not None\n        assert result["total_items"] == 3\n        assert result["total_length"] == 3\n        assert result["unique_items"] == 3\n        \n    def test_process_data_duplicate_items(self):\n        """Test processing with duplicate items."""\n        processor = DataProcessor({})\n        result = processor.process_data(["a", "b", "a"])\n        \n        assert result is not None\n        assert result["total_items"] == 3\n        assert result["unique_items"] == 2\n'
        )

    def _create_javascript_files(self: Any) -> None:
        """Create JavaScript source files."""
        (self.test_repo_path / "src/main/javascript/main.js").write_text(
            "/**\n * Main JavaScript application module.\n */\n\nclass APIClient {\n    constructor(baseUrl) {\n        this.baseUrl = baseUrl;\n        this.timeout = 5000;\n    }\n    \n    async fetchData(endpoint) {\n        const url = `${this.baseUrl}/${endpoint}`;\n        \n        try {\n            const response = await fetch(url, {\n                method: 'GET',\n                timeout: this.timeout,\n                headers: {\n                    'Content-Type': 'application/json'\n                }\n            });\n            \n            if (!response.ok) {\n                throw new Error(`HTTP error! status: ${response.status}`);\n            }\n            \n            return await response.json();\n        } catch (error) {\n            console.error('API request failed:', error);\n            throw error;\n        }\n    }\n    \n    async postData(endpoint, data) {\n        const url = `${this.baseUrl}/${endpoint}`;\n        \n        try {\n            const response = await fetch(url, {\n                method: 'POST',\n                timeout: this.timeout,\n                headers: {\n                    'Content-Type': 'application/json'\n                },\n                body: JSON.stringify(data)\n            });\n            \n            return await response.json();\n        } catch (error) {\n            console.error('API post failed:', error);\n            throw error;\n        }\n    }\n}\n\n// Export for Node.js\nif (typeof module !== 'undefined' && module.exports) {\n    module.exports = { APIClient };\n}\n\n// Global for browser\nif (typeof window !== 'undefined') {\n    window.APIClient = APIClient;\n}\n"
        )
        (self.test_repo_path / "src/main/javascript/package.json").write_text(
            '{\n  "name": "test-app",\n  "version": "1.0.0",\n  "description": "Test application for filesystem ingestion",\n  "main": "main.js",\n  "scripts": {\n    "start": "node main.js",\n    "test": "jest",\n    "lint": "eslint *.js"\n  },\n  "dependencies": {\n    "axios": "^0.27.2",\n    "lodash": "^4.17.21"\n  },\n  "devDependencies": {\n    "jest": "^28.1.0",\n    "eslint": "^8.0.0"\n  },\n  "keywords": ["test", "filesystem", "ingestion"],\n  "author": "Test Author",\n  "license": "MIT"\n}\n'
        )

    def _create_documentation_files(self: Any) -> None:
        """Create documentation files."""
        (self.test_repo_path / "README.md").write_text(
            "# Test Repository\n\nThis is a comprehensive test repository for validating filesystem ingestion functionality.\n\n## Overview\n\nThis repository contains various file types and directory structures designed to test:\n\n- Multiple programming languages (Python, JavaScript)\n- Documentation files (Markdown, reStructuredText)\n- Configuration files (JSON, YAML, TOML)\n- Data files (CSV, JSON)\n- Binary files\n- Special characters in filenames\n- Deep directory structures\n- Symlinks\n- .gitignore pattern respect\n\n## Structure\n\n```\n├── src/\n│   ├── main/\n│   │   ├── python/\n│   │   └── javascript/\n│   └── test/\n├── docs/\n├── config/\n├── scripts/\n└── data/\n```\n\n## Testing\n\nThis repository is used for integration testing of the filesystem ingestion step.\n\n### Edge Cases Tested\n\n1. **Unicode characters** in filenames and directories\n2. **Spaces and special characters** in paths\n3. **Deep directory nesting** (10+ levels)\n4. **Large files** for performance testing\n5. **Symlinks** and their handling\n6. **Empty directories**\n7. **Files that should be ignored** (.gitignore patterns)\n\n## Performance Considerations\n\nThe repository includes files of various sizes to test:\n- Small text files (< 1KB)\n- Medium files (1KB - 100KB)\n- Large files (> 1MB)\n\n## .gitignore Testing\n\nCommon patterns tested:\n- `*.pyc` - Compiled Python files\n- `node_modules/` - Node.js dependencies\n- `build/` - Build output directories\n- `.git/` - Git metadata\n- `*.log` - Log files\n"
        )
        (self.test_repo_path / "docs/api/README.md").write_text(
            '# API Documentation\n\n## Overview\n\nThis document describes the API endpoints available in the test application.\n\n## Endpoints\n\n### GET /api/data\n\nRetrieve data from the server.\n\n**Response:**\n```json\n{\n  "data": [],\n  "total": 0,\n  "page": 1\n}\n```\n\n### POST /api/data\n\nSubmit new data to the server.\n\n**Request:**\n```json\n{\n  "items": ["item1", "item2"],\n  "metadata": {\n    "source": "test"\n  }\n}\n```\n\n**Response:**\n```json\n{\n  "success": true,\n  "id": "12345"\n}\n```\n\n## Authentication\n\nAll API endpoints require authentication via Bearer token.\n\n```\nAuthorization: Bearer <token>\n```\n\n## Error Handling\n\nThe API returns standard HTTP status codes:\n\n- `200` - Success\n- `400` - Bad Request\n- `401` - Unauthorized\n- `404` - Not Found\n- `500` - Internal Server Error\n'
        )
        (self.test_repo_path / "docs/guides/user_guide.rst").write_text(
            'User Guide\n==========\n\nGetting Started\n--------------\n\nThis section covers the basic usage of the test application.\n\nInstallation\n^^^^^^^^^^^\n\n1. Clone the repository::\n\n    git clone https://github.com/example/test-repo.git\n\n2. Install dependencies::\n\n    pip install -r requirements.txt\n\n3. Run the application::\n\n    python src/main/python/app.py\n\nConfiguration\n^^^^^^^^^^^^\n\nThe application can be configured using environment variables:\n\n- ``APP_MODE`` - Application mode (development, production)\n- ``LOG_LEVEL`` - Logging level (DEBUG, INFO, WARNING, ERROR)\n- ``DATABASE_URL`` - Database connection string\n\nUsage Examples\n^^^^^^^^^^^^^\n\nBasic usage::\n\n    from src.main.python.app import DataProcessor\n    \n    processor = DataProcessor({"mode": "development"})\n    result = processor.process_data(["sample", "data"])\n    print(result)\n\nAdvanced usage::\n\n    import json\n    from pathlib import Path\n    from src.main.python.utils import load_config, save_data\n    \n    config = load_config(Path("config/app.json"))\n    processor = DataProcessor(config)\n    \n    data = ["item1", "item2", "item3"]\n    result = processor.process_data(data)\n    \n    save_data(result, Path("output/results.json"))\n\nTroubleshooting\n^^^^^^^^^^^^^^\n\nCommon issues and solutions:\n\n1. **Import errors**: Ensure all dependencies are installed\n2. **Configuration errors**: Check environment variables\n3. **Performance issues**: Monitor memory usage with large datasets\n\nFor more help, see the API documentation or contact support.\n'
        )

    def _create_config_files(self: Any) -> None:
        """Create configuration files."""
        (self.test_repo_path / "config/app.json").write_text(
            '{\n  "database": {\n    "host": "localhost",\n    "port": 5432,\n    "name": "testdb",\n    "user": "testuser",\n    "password": "testpass"\n  },\n  "api": {\n    "host": "0.0.0.0",\n    "port": 8000,\n    "timeout": 30,\n    "max_requests": 1000\n  },\n  "logging": {\n    "level": "INFO",\n    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",\n    "file": "logs/app.log"\n  },\n  "features": {\n    "enable_cache": true,\n    "enable_metrics": true,\n    "enable_debug": false\n  }\n}\n'
        )
        (self.test_repo_path / "config/environments/production.yaml").write_text(
            "# Production environment configuration\ndatabase:\n  host: prod-db.example.com\n  port: 5432\n  name: production_db\n  user: prod_user\n  password: ${DATABASE_PASSWORD}\n  ssl_mode: require\n  pool_size: 20\n\napi:\n  host: 0.0.0.0\n  port: 8080\n  timeout: 60\n  max_requests: 10000\n  rate_limit: 1000\n\nlogging:\n  level: WARNING\n  format: json\n  file: /var/log/app/production.log\n  rotation: daily\n  retention: 30\n\nfeatures:\n  enable_cache: true\n  enable_metrics: true\n  enable_debug: false\n  cache_ttl: 3600\n\nsecurity:\n  secret_key: ${SECRET_KEY}\n  jwt_expiration: 86400\n  cors_origins:\n    - https://app.example.com\n    - https://admin.example.com\n\nmonitoring:\n  enable_health_check: true\n  health_check_path: /health\n  metrics_path: /metrics\n  prometheus_enabled: true\n"
        )
        (self.test_repo_path / "config/.env.example").write_text(
            "# Environment variables example\nDATABASE_PASSWORD=your_secure_password_here\nSECRET_KEY=your_secret_key_here\nAPI_KEY=your_api_key_here\n\n# Application settings\nAPP_MODE=development\nLOG_LEVEL=DEBUG\nDEBUG=true\n\n# External services\nREDIS_URL=redis://localhost:6379\nELASTICSEARCH_URL=http://localhost:9200\n\n# Email settings\nSMTP_HOST=smtp.gmail.com\nSMTP_PORT=587\nSMTP_USER=your_email@example.com\nSMTP_PASSWORD=your_email_password\n"
        )

    def _create_data_files(self: Any) -> None:
        """Create data files."""
        (self.test_repo_path / "data/samples/users.csv").write_text(
            "id,name,email,age,city\n1,John Doe,john.doe@example.com,25,New York\n2,Jane Smith,jane.smith@example.com,30,Los Angeles\n3,Bob Johnson,bob.johnson@example.com,35,Chicago\n4,Alice Williams,alice.williams@example.com,28,Houston\n5,Charlie Brown,charlie.brown@example.com,32,Phoenix\n6,Diana Davis,diana.davis@example.com,27,Philadelphia\n7,Eve Wilson,eve.wilson@example.com,29,San Antonio\n8,Frank Miller,frank.miller@example.com,31,San Diego\n9,Grace Taylor,grace.taylor@example.com,26,Dallas\n10,Henry Anderson,henry.anderson@example.com,33,San Jose\n"
        )
        (self.test_repo_path / "data/samples/products.json").write_text(
            '{\n  "products": [\n    {\n      "id": 1,\n      "name": "Laptop Computer",\n      "category": "Electronics",\n      "price": 999.99,\n      "in_stock": true,\n      "specifications": {\n        "cpu": "Intel i7",\n        "ram": "16GB",\n        "storage": "512GB SSD",\n        "screen": "15.6 inch"\n      },\n      "tags": ["computer", "laptop", "portable", "business"]\n    },\n    {\n      "id": 2,\n      "name": "Wireless Mouse",\n      "category": "Accessories",\n      "price": 29.99,\n      "in_stock": true,\n      "specifications": {\n        "connectivity": "Bluetooth",\n        "battery_life": "12 months",\n        "dpi": "1600",\n        "buttons": 3\n      },\n      "tags": ["mouse", "wireless", "bluetooth", "ergonomic"]\n    },\n    {\n      "id": 3,\n      "name": "Monitor Stand",\n      "category": "Accessories",\n      "price": 79.99,\n      "in_stock": false,\n      "specifications": {\n        "material": "Aluminum",\n        "adjustable": true,\n        "max_weight": "10kg",\n        "compatibility": "VESA 100x100"\n      },\n      "tags": ["monitor", "stand", "adjustable", "ergonomic"]\n    }\n  ],\n  "metadata": {\n    "total_products": 3,\n    "last_updated": "2025-05-28T19:00:00Z",\n    "version": "1.0"\n  }\n}\n'
        )

    def _create_ignored_files(self: Any) -> None:
        """Create files that should be ignored by .gitignore."""
        (self.test_repo_path / "src/main/python/__pycache__").mkdir(exist_ok=True)
        (
            self.test_repo_path / "src/main/python/__pycache__/app.cpython-39.pyc"
        ).write_bytes(b"\x00\x01\x02\x03" * 100)
        (self.test_repo_path / "src/main/python/utils.pyc").write_bytes(
            b"\x04\x05\x06\x07" * 50
        )
        (self.test_repo_path / "node_modules/some-package/index.js").write_text(
            "module.exports = {};"
        )
        (self.test_repo_path / "node_modules/some-package/package.json").write_text(
            '{"name": "some-package"}'
        )
        (self.test_repo_path / "build/output/app.min.js").write_text(
            '(function(){console.log("minified")})();'
        )
        (self.test_repo_path / "build/output/styles.min.css").write_text(
            "body{margin:0;padding:0}"
        )
        (self.test_repo_path / "app.log").write_text(
            "2025-05-28 19:00:00,000 - INFO - Application started\n2025-05-28 19:00:01,000 - DEBUG - Processing request\n2025-05-28 19:00:02,000 - WARNING - Rate limit approaching\n2025-05-28 19:00:03,000 - ERROR - Database connection failed\n"
        )
        (self.test_repo_path / ".git/objects/abc123").write_bytes(
            b"\x00\x01\x02\x03" * 200
        )
        (self.test_repo_path / ".git/refs/heads").mkdir(parents=True, exist_ok=True)
        (self.test_repo_path / ".git/refs/heads/main").write_text("abc123def456")
        (self.test_repo_path / "temp.tmp").write_text("Temporary data")
        (self.test_repo_path / "cache.temp").write_text("Cache data")

    def _create_edge_case_files(self: Any) -> None:
        """Create files with edge case names and content."""
        (self.test_repo_path / "unicode_测试_文件.txt").write_text("Unicode content: 测试内容")
        (self.test_repo_path / "émoji_🚀_file.md").write_text(
            "# Emoji File 🚀\n\nThis file has emojis in its name!"
        )
        (self.test_repo_path / "file with spaces.txt").write_text(
            "Content of file with spaces"
        )
        (self.test_repo_path / "file-with-dashes.txt").write_text(
            "Content of file with dashes"
        )
        (self.test_repo_path / "file_with_underscores.txt").write_text(
            "Content of file with underscores"
        )
        (self.test_repo_path / "file.with.dots.txt").write_text(
            "Content of file with dots"
        )
        (self.test_repo_path / "file!@#$%^&()special.txt").write_text(
            "Content of file with special chars"
        )
        long_name = "a" * 200 + ".txt"
        try:
            (self.test_repo_path / long_name).write_text(
                "Content of very long filename"
            )
        except OSError:
            (self.test_repo_path / ("a" * 100 + ".txt")).write_text(
                "Content of long filename"
            )
        (self.test_repo_path / "Makefile").write_text(
            'all: build test\n\nbuild:\n\techo "Building application"\n\ntest:\n\techo "Running tests"\n\nclean:\n\techo "Cleaning build artifacts"\n\n.PHONY: all build test clean\n'
        )
        (self.test_repo_path / "Dockerfile").write_text(
            'FROM python:3.9-slim\n\nWORKDIR /app\n\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\n\nCOPY . .\n\nEXPOSE 8000\n\nCMD ["python", "src/main/python/app.py"]\n'
        )
        (self.test_repo_path / "binary_data.bin").write_bytes(bytes(range(256)) * 10)
        (self.test_repo_path / "empty_file.txt").touch()
        (self.test_repo_path / "whitespace_only.txt").write_text("   \n\n\t\t\n   ")

    def _create_large_files(self: Any) -> None:
        """Create large files for performance testing."""
        medium_content = "This is a medium sized file for testing.\n" * 2500
        (self.test_repo_path / "data/medium_file.txt").write_text(medium_content)
        large_content = "This is a large file for performance testing. " * 20000
        (self.test_repo_path / "data/large_file.txt").write_text(large_content)
        very_large_content = (
            "This file should be ignored due to .large extension. " * 100000
        )
        (self.test_repo_path / "data/very_large_file.large").write_text(
            very_large_content
        )

    def _create_symlinks(self: Any) -> None:
        """Create symbolic links for testing."""
        try:
            (self.test_repo_path / "link_to_readme.md").symlink_to("README.md")
            (self.test_repo_path / "link_to_src").symlink_to("src")
            (self.test_repo_path / "broken_link.txt").symlink_to("nonexistent_file.txt")
            (self.test_repo_path / "link_to_link.md").symlink_to("link_to_readme.md")
        except OSError as e:
            logger.warning(f"Could not create symlinks: {e}")

    def capture_cli_logs(self: Any, command: List[str]) -> tuple[int, str, str]:
        """Execute CLI command and capture all output."""
        logger.info(f"Executing CLI command: {' '.join(command)}")
        self.start_time = time.time()
        try:
            result = subprocess.run(
                command,
                cwd=self.test_repo_path,
                capture_output=True,
                text=True,
                timeout=300,
            )
            self.end_time = time.time()
            execution_time = self.end_time - self.start_time
            logger.info(f"Command completed in {execution_time:.2f} seconds")
            logger.info(f"Return code: {result.returncode}")
            logger.debug(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                logger.warning(f"STDERR:\n{result.stderr}")
            self.ingestion_logs.extend(result.stdout.split("\n"))
            if result.stderr:
                self.ingestion_logs.extend(result.stderr.split("\n"))
            return (result.returncode, result.stdout, result.stderr)
        except subprocess.TimeoutExpired:
            self.end_time = time.time()
            logger.error("Command timed out after 5 minutes")
            raise
        except Exception as e:
            self.end_time = time.time()
            logger.error(f"Command execution failed: {e}")
            raise

    def get_execution_time(self: Any) -> Optional[float]:
        """Get the execution time of the last command."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


class Neo4jTestValidator:
    """Validator for Neo4j graph content after ingestion."""

    def __init__(self: Any) -> None:
        settings = get_settings()
        self.connector = Neo4jConnector(
            uri=settings.neo4j.uri,
            username=settings.neo4j.username,
            password=settings.neo4j.password.get_secret_value(),
            database=settings.neo4j.database,
        )

    async def validate_graph_structure(
        self: Any, repository_path: Path
    ) -> Dict[str, any]:
        """Validate the graph structure matches the repository."""
        logger.info("Validating Neo4j graph structure")
        validation_results = {
            "total_nodes": 0,
            "file_nodes": 0,
            "directory_nodes": 0,
            "repository_nodes": 0,
            "relationships": 0,
            "ignored_files_present": [],
            "missing_files": [],
            "extra_files": [],
            "structure_valid": True,
            "errors": [],
        }
        try:
            query = "\n            MATCH (n)\n            RETURN \n                n.path as path,\n                n.type as type,\n                n.name as name,\n                labels(n) as labels\n            "
            async with self.connector.get_async_session() as session:
                result = await session.run(query)
                graph_nodes = await result.data()
            validation_results["total_nodes"] = len(graph_nodes)
            graph_files = set()
            graph_directories = set()
            for node in graph_nodes:
                if "File" in node["labels"]:
                    validation_results["file_nodes"] += 1
                    if node["path"]:
                        graph_files.add(node["path"])
                elif "Directory" in node["labels"]:
                    validation_results["directory_nodes"] += 1
                    if node["path"]:
                        graph_directories.add(node["path"])
                elif "Repository" in node["labels"]:
                    validation_results["repository_nodes"] += 1
            expected_files = set()
            expected_directories = set()
            for item in repository_path.rglob("*"):
                relative_path = str(item.relative_to(repository_path))
                if item.is_file():
                    expected_files.add(relative_path)
                elif item.is_dir():
                    expected_directories.add(relative_path)
            gitignore_path = repository_path / ".gitignore"
            ignored_patterns = []
            if gitignore_path.exists():
                ignored_patterns = [
                    line.strip()
                    for line in gitignore_path.read_text().split("\n")
                    if line.strip() and (not line.startswith("#"))
                ]
            for file_path in graph_files:
                if self._should_be_ignored(file_path, ignored_patterns):
                    validation_results["ignored_files_present"].append(file_path)
                    validation_results["structure_valid"] = False
            expected_files_filtered = {
                f
                for f in expected_files
                if not self._should_be_ignored(f, ignored_patterns)
            }
            validation_results["missing_files"] = list(
                expected_files_filtered - graph_files
            )
            validation_results["extra_files"] = list(
                graph_files - expected_files_filtered
            )
            relationship_query = "MATCH ()-[r]->() RETURN count(r) as count"
            async with self.connector.get_async_session() as session:
                result = await session.run(relationship_query)
                rel_data = await result.single()
                validation_results["relationships"] = (
                    rel_data["count"] if rel_data else 0
                )
            if validation_results["missing_files"] or validation_results["extra_files"]:
                validation_results["structure_valid"] = False
        except Exception as e:
            validation_results["errors"].append(f"Graph validation failed: {e!s}")
            validation_results["structure_valid"] = False
            logger.error(f"Graph validation error: {e}")
        return validation_results

    def _should_be_ignored(self: Any, file_path: str, patterns: List[str]) -> bool:
        """Check if a file should be ignored based on .gitignore patterns."""
        for pattern in patterns:
            pattern = pattern.strip()
            if not pattern or pattern.startswith("#"):
                continue
            if pattern.endswith("/"):
                if (
                    file_path.startswith(pattern[:-1])
                    or f"/{pattern[:-1]}" in file_path
                ):
                    return True
            elif "*" in pattern:
                if pattern.startswith("*."):
                    ext = pattern[2:]
                    if file_path.endswith(f".{ext}"):
                        return True
            elif pattern in file_path:
                return True
        return False


@pytest.mark.integration
@pytest.mark.slow
class TestFilesystemIngestionE2E:
    """Comprehensive end-to-end tests for filesystem ingestion."""

    @pytest.fixture(autouse=True)
    async def setup_and_cleanup(self: Any) -> None:
        """Set up test environment and clean up afterwards."""
        self.temp_dir = tempfile.mkdtemp(prefix="codestory_fs_test_")
        self.test_repo_path = Path(self.temp_dir)
        logger.info(f"Created test directory: {self.temp_dir}")
        self.helper = FilesystemIngestionTestHelper(self.test_repo_path)
        self.validator = Neo4jTestValidator()
        await self._start_codestory_services()
        yield
        await self._stop_codestory_services()
        try:
            shutil.rmtree(self.temp_dir)
            logger.info(f"Cleaned up test directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up test directory: {e}")

    async def _start_codestory_services(self: Any) -> None:
        """Start CodeStory services for testing.

        Refactored to skip starting the stack if all required containers are already running and healthy.
        """
        import re

        os.environ["REDIS__URI"] = os.environ["REDIS_URI"]
        logger.info("Checking CodeStory service container status...")
        required_services = {
            "neo4j": ["neo4j", "codestory-neo4j"],
            "redis": ["redis", "codestory-redis"],
            "worker": ["worker", "codestory-worker"],
            "service": ["service", "codestory-service"],
        }
        healthy_services = set()

        def parse_ps_output(output: str):
            found = set()
            for line in output.splitlines():
                for svc, patterns in required_services.items():
                    if svc == "service":
                        if any(pat in line for pat in patterns) and (
                            (
                                "Up" in line
                                and (
                                    "(healthy)" in line or "(health: starting)" in line
                                )
                            )
                            or "Started" in line
                        ):
                            found.add(svc)
                    elif (
                        any(pat in line for pat in patterns)
                        and "Up" in line
                        and ("(healthy)" in line)
                    ):
                        found.add(svc)
            return found

        try:
            ps_proc = subprocess.run(
                ["docker", "compose", "ps", "--status=running"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if ps_proc.returncode == 0:
                healthy_services = parse_ps_output(ps_proc.stdout)
        except Exception as e:
            logger.warning(f"Could not check docker compose status: {e}")
        if healthy_services == set(required_services.keys()):
            logger.info(
                "All required CodeStory containers are already running and healthy. Skipping stack startup."
            )
            await self._wait_for_services_ready()
            return
        logger.info("Not all containers are healthy. Restarting stack...")
        try:
            subprocess.run(["codestory", "stop"], capture_output=True, timeout=30)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass
        try:
            result = subprocess.run(
                ["codestory", "start"], capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                logger.error(f"Failed to start services: {result.stderr}")
                logger.info("Attempting manual docker compose startup...")
                subprocess.run(
                    ["docker", "compose", "--env-file", ".env", "up", "-d"],
                    capture_output=True,
                    timeout=120,
                )
            await self._wait_for_services_ready()
        except subprocess.TimeoutExpired:
            logger.error("Service startup timed out")
            raise
        except Exception as e:
            logger.error(f"Error starting services: {e}")
            raise

    async def _stop_codestory_services(self: Any) -> None:
        """Stop CodeStory services after testing."""
        logger.info("Stopping CodeStory services...")
        try:
            subprocess.run(["codestory", "stop"], capture_output=True, timeout=60)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            subprocess.run(
                ["docker", "compose", "down", "--remove-orphans"],
                capture_output=True,
                timeout=60,
            )

    async def _wait_for_services_ready(self: Any, max_wait: Any = 60) -> None:
        """Wait for all required services to be running and healthy."""
        import re

        logger.info("Waiting for all CodeStory containers to be running and healthy...")
        required_services = {
            "neo4j": ["neo4j", "codestory-neo4j"],
            "redis": ["redis", "codestory-redis"],
            "worker": ["worker", "codestory-worker"],
            "service": ["service", "codestory-service"],
        }

        def parse_ps_output(output: str):
            found = set()
            for line in output.splitlines():
                for svc, patterns in required_services.items():
                    if svc == "service":
                        if any(pat in line for pat in patterns) and (
                            (
                                "Up" in line
                                and (
                                    "(healthy)" in line or "(health: starting)" in line
                                )
                            )
                            or "Started" in line
                        ):
                            found.add(svc)
                    elif (
                        any(pat in line for pat in patterns)
                        and "Up" in line
                        and ("(healthy)" in line)
                    ):
                        found.add(svc)
            return found

        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                ps_proc = subprocess.run(
                    ["docker", "compose", "ps", "--status=running"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if ps_proc.returncode == 0:
                    healthy_services = parse_ps_output(ps_proc.stdout)
                    if healthy_services == set(required_services.keys()):
                        logger.info("All required containers are running and healthy.")
                        return
            except Exception as e:
                logger.warning(f"Error checking container health: {e}")
            await asyncio.sleep(2)
        docker_result = subprocess.run(
            ["docker", "ps", "-a"], capture_output=True, text=True
        )
        logger.error(
            f"Services not ready after {max_wait}s. Docker status:\n{docker_result.stdout}"
        )
        try:
            service_logs = subprocess.run(
                ["docker", "logs", "codestory-service"], capture_output=True, text=True
            )
            logger.error(f"Service logs:\n{service_logs.stdout}\n{service_logs.stderr}")
        except Exception:
            pass
        raise TimeoutError(f"Services not ready after {max_wait} seconds")

    async def test_comprehensive_filesystem_ingestion(self: Any) -> None:
        """Test comprehensive filesystem ingestion with realistic repository."""
        logger.info("Starting comprehensive filesystem ingestion test")
        logger.info("Step 1: Creating test repository structure")
        self.helper.create_test_repository()
        total_items = len(list(self.test_repo_path.rglob("*")))
        assert (
            total_items > 50
        ), f"Test repository should have >50 items, got {total_items}"
        gitignore_exists = (self.test_repo_path / ".gitignore").exists()
        assert gitignore_exists, ".gitignore file should exist"
        logger.info("Step 2: Executing filesystem ingestion via CLI")
        command = [
            "codestory",
            "ingest",
            "start",
            str(self.test_repo_path),
            "--steps",
            "filesystem",
            "--verbose",
        ]
        returncode, stdout, stderr = self.helper.capture_cli_logs(command)
        assert (
            returncode == 0
        ), f"CLI command failed with return code {returncode}. STDERR: {stderr}"
        logger.info("Step 3: Validating execution time")
        execution_time = self.helper.get_execution_time()
        assert execution_time is not None, "Execution time should be recorded"
        assert (
            execution_time < 300
        ), f"Ingestion took too long: {execution_time:.2f}s (max: 300s)"
        logger.info(f"Ingestion completed in {execution_time:.2f} seconds")
        logger.info("Step 4: Validating progress reporting")
        logs = "\n".join(self.helper.ingestion_logs)
        assert (
            "progress" in logs.lower() or "processing" in logs.lower()
        ), "Logs should contain progress indicators"
        logger.info("Step 5: Validating Neo4j graph structure")
        validation_results = await self.validator.validate_graph_structure(
            self.test_repo_path
        )
        assert validation_results[
            "structure_valid"
        ], f"Graph structure validation failed: {validation_results['errors']}"
        assert validation_results["total_nodes"] > 0, "Graph should contain nodes"
        assert validation_results["file_nodes"] > 0, "Graph should contain file nodes"
        assert (
            validation_results["directory_nodes"] > 0
        ), "Graph should contain directory nodes"
        assert (
            validation_results["relationships"] > 0
        ), "Graph should contain relationships"
        logger.info("Step 6: Validating .gitignore pattern respect")
        assert (
            len(validation_results["ignored_files_present"]) == 0
        ), f"Ignored files found in graph: {validation_results['ignored_files_present']}"
        logger.info("Step 7: Validating ingestion completeness")
        max_missing = 5
        assert (
            len(validation_results["missing_files"]) <= max_missing
        ), f"Too many missing files: {validation_results['missing_files']}"
        max_extra = 5
        assert (
            len(validation_results["extra_files"]) <= max_extra
        ), f"Too many extra files: {validation_results['extra_files']}"
        logger.info("Test completed successfully!")
        logger.info(f"Execution time: {execution_time:.2f}s")
        logger.info(f"Total nodes: {validation_results['total_nodes']}")
        logger.info(f"File nodes: {validation_results['file_nodes']}")
        logger.info(f"Directory nodes: {validation_results['directory_nodes']}")
        logger.info(f"Relationships: {validation_results['relationships']}")
        assert True, "Comprehensive filesystem ingestion test passed"

    async def test_gitignore_patterns_comprehensive(self: Any) -> None:
        """Test comprehensive .gitignore pattern handling."""
        logger.info("Starting comprehensive .gitignore pattern test")
        simple_repo = self.test_repo_path / "simple"
        simple_repo.mkdir()
        gitignore_content = "\n*.pyc\n__pycache__/\nnode_modules/\nbuild/\n*.log\n.git/\n*.tmp\n*.temp\ntemp/\n        ".strip()
        (simple_repo / ".gitignore").write_text(gitignore_content)
        (simple_repo / "test.pyc").write_text("compiled python")
        (simple_repo / "__pycache__").mkdir()
        (simple_repo / "__pycache__/module.pyc").write_text("cache")
        (simple_repo / "node_modules").mkdir()
        (simple_repo / "node_modules/package").mkdir()
        (simple_repo / "node_modules/package/index.js").write_text("js")
        (simple_repo / "build").mkdir()
        (simple_repo / "build/output.js").write_text("built")
        (simple_repo / "app.log").write_text("logs")
        (simple_repo / ".git").mkdir()
        (simple_repo / ".git/config").write_text("git config")
        (simple_repo / "temp.tmp").write_text("temp")
        (simple_repo / "cache.temp").write_text("temp")
        (simple_repo / "temp").mkdir()
        (simple_repo / "temp/file.txt").write_text("temp file")
        (simple_repo / "main.py").write_text("python code")
        (simple_repo / "src").mkdir()
        (simple_repo / "src/app.js").write_text("js code")
        (simple_repo / "README.md").write_text("documentation")
        command = [
            "codestory",
            "ingest",
            "start",
            str(simple_repo),
            "--steps",
            "filesystem",
        ]
        returncode, stdout, stderr = self.helper.capture_cli_logs(command)
        assert returncode == 0, f"Ingestion failed: {stderr}"
        validation_results = await self.validator.validate_graph_structure(simple_repo)
        assert (
            len(validation_results["ignored_files_present"]) == 0
        ), f"Found ignored files in graph: {validation_results['ignored_files_present']}"
        assert (
            validation_results["file_nodes"] >= 3
        ), "Should have at least main.py, app.js, README.md, and .gitignore"

    async def test_performance_large_repository(self: Any) -> None:
        """Test performance with a large repository structure."""
        logger.info("Starting performance test with large repository")
        large_repo = self.test_repo_path / "large"
        large_repo.mkdir()
        current_dir = large_repo
        for i in range(15):
            current_dir = current_dir / f"level_{i}"
            current_dir.mkdir()
            for j in range(5):
                (current_dir / f"file_{j}.txt").write_text(
                    f"Content at level {i}, file {j}"
                )
        for i in range(100):
            (large_repo / f"root_file_{i}.py").write_text(
                f"def function_{i}():\n    return {i}"
            )
        large_content = "Large file content line.\n" * 50000
        (large_repo / "large_file.txt").write_text(large_content)
        command = [
            "codestory",
            "ingest",
            "start",
            str(large_repo),
            "--steps",
            "filesystem",
        ]
        start_time = time.time()
        returncode, stdout, stderr = self.helper.capture_cli_logs(command)
        end_time = time.time()
        execution_time = end_time - start_time
        assert returncode == 0, f"Large repository ingestion failed: {stderr}"
        assert (
            execution_time < 120
        ), f"Large repository took too long: {execution_time:.2f}s (max: 120s)"
        validation_results = await self.validator.validate_graph_structure(large_repo)
        assert validation_results[
            "structure_valid"
        ], "Large repository structure should be valid"
        assert validation_results["file_nodes"] >= 100, "Should have many file nodes"
        logger.info(f"Large repository processed in {execution_time:.2f}s")

    async def test_edge_cases_and_error_handling(self: Any) -> None:
        """Test edge cases and error handling scenarios."""
        logger.info("Starting edge cases and error handling test")
        edge_repo = self.test_repo_path / "edge"
        edge_repo.mkdir()
        (edge_repo / "empty").mkdir()
        (edge_repo / "special_chars_!@#$%^&().txt").write_text("special content")
        (edge_repo / "unicode_测试.txt").write_text("unicode content")
        long_content = "Very long line " * 10000
        (edge_repo / "long_content.txt").write_text(long_content)
        (edge_repo / "binary.bin").write_bytes(bytes(range(256)) * 100)
        try:
            (edge_repo / "link.txt").symlink_to("special_chars_!@#$%^&().txt")
        except OSError:
            pass
        command = [
            "codestory",
            "ingest",
            "start",
            str(edge_repo),
            "--steps",
            "filesystem",
        ]
        returncode, stdout, stderr = self.helper.capture_cli_logs(command)
        assert returncode == 0, f"Edge case ingestion failed: {stderr}"
        validation_results = await self.validator.validate_graph_structure(edge_repo)
        assert (
            validation_results["total_nodes"] > 0
        ), "Should have nodes despite edge cases"
        logger.info("Edge cases handled successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
