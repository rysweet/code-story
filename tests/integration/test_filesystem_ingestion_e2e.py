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
from typing import Dict, List, Optional, Set
from unittest.mock import patch

import pytest
from neo4j import GraphDatabase

from codestory.cli.main import main as cli_main
from codestory.config.settings import get_settings
from codestory.graphdb.neo4j_connector import Neo4jConnector

# Configure logging for detailed test diagnostics
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class FilesystemIngestionTestHelper:
    """Helper class for filesystem ingestion testing."""
    
    def __init__(self, test_repo_path: Path):
        self.test_repo_path = test_repo_path
        self.ingestion_logs: List[str] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        
    def create_test_repository(self) -> None:
        """Create a comprehensive test repository structure."""
        logger.info(f"Creating test repository at {self.test_repo_path}")
        
        # Create directory structure
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
            "node_modules/some-package",  # Should be ignored
            ".git/objects",  # Should be ignored
            "build/output",  # Should be ignored
            "deep/nested/directory/structure/level5/level6/level7/level8/level9/level10",
            "empty_directory",
            "unicode_测试_directory",
            "directory with spaces",
            "special-chars_!@#$%^&()_directory"
        ]
        
        for dir_path in dirs:
            (self.test_repo_path / dir_path).mkdir(parents=True, exist_ok=True)
            
        # Create .gitignore file
        gitignore_content = """
# Compiled Python files
*.pyc
__pycache__/
*.pyo
*.pyd

# Node modules
node_modules/
npm-debug.log*

# Build directories
build/
dist/
*.egg-info/

# IDE files
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Git directory
.git/

# Log files
*.log
logs/

# Temporary files
*.tmp
*.temp
temp/

# Large files (for testing)
*.large
        """.strip()
        
        (self.test_repo_path / ".gitignore").write_text(gitignore_content)
        
        # Create various file types
        self._create_python_files()
        self._create_javascript_files()
        self._create_documentation_files()
        self._create_config_files()
        self._create_data_files()
        self._create_ignored_files()
        self._create_edge_case_files()
        self._create_large_files()
        self._create_symlinks()
        
        logger.info(f"Test repository created with {len(list(self.test_repo_path.rglob('*')))} total items")
    
    def _create_python_files(self) -> None:
        """Create Python source files."""
        # Main application file
        (self.test_repo_path / "src/main/python/app.py").write_text('''"""Main application module."""

import os
import sys
from typing import List, Dict, Optional

class DataProcessor:
    """Process various types of data."""
    
    def __init__(self, config: Dict[str, str]):
        self.config = config
        
    def process_data(self, data: List[str]) -> Optional[Dict[str, int]]:
        """Process input data and return statistics."""
        if not data:
            return None
            
        return {
            "total_items": len(data),
            "total_length": sum(len(item) for item in data),
            "unique_items": len(set(data))
        }

def main():
    """Main entry point."""
    processor = DataProcessor({"mode": "production"})
    result = processor.process_data(["test", "data", "items"])
    print(f"Processing result: {result}")

if __name__ == "__main__":
    main()
''')
        
        # Utils module
        (self.test_repo_path / "src/main/python/utils.py").write_text('''"""Utility functions."""

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

def load_config(config_path: Path) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Config file not found: {config_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        return {}

def save_data(data: Dict[str, Any], output_path: Path) -> bool:
    """Save data to JSON file."""
    try:
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save data: {e}")
        return False
''')
        
        # Test files
        (self.test_repo_path / "src/test/unit/test_app.py").write_text('''"""Unit tests for app module."""

import pytest
from src.main.python.app import DataProcessor

class TestDataProcessor:
    """Test cases for DataProcessor class."""
    
    def test_process_data_empty_input(self):
        """Test processing with empty input."""
        processor = DataProcessor({})
        result = processor.process_data([])
        assert result is None
        
    def test_process_data_valid_input(self):
        """Test processing with valid input."""
        processor = DataProcessor({})
        result = processor.process_data(["a", "b", "c"])
        
        assert result is not None
        assert result["total_items"] == 3
        assert result["total_length"] == 3
        assert result["unique_items"] == 3
        
    def test_process_data_duplicate_items(self):
        """Test processing with duplicate items."""
        processor = DataProcessor({})
        result = processor.process_data(["a", "b", "a"])
        
        assert result is not None
        assert result["total_items"] == 3
        assert result["unique_items"] == 2
''')
    
    def _create_javascript_files(self) -> None:
        """Create JavaScript source files."""
        # Main JS file
        (self.test_repo_path / "src/main/javascript/main.js").write_text('''/**
 * Main JavaScript application module.
 */

class APIClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
        this.timeout = 5000;
    }
    
    async fetchData(endpoint) {
        const url = `${this.baseUrl}/${endpoint}`;
        
        try {
            const response = await fetch(url, {
                method: 'GET',
                timeout: this.timeout,
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }
    
    async postData(endpoint, data) {
        const url = `${this.baseUrl}/${endpoint}`;
        
        try {
            const response = await fetch(url, {
                method: 'POST',
                timeout: this.timeout,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            return await response.json();
        } catch (error) {
            console.error('API post failed:', error);
            throw error;
        }
    }
}

// Export for Node.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { APIClient };
}

// Global for browser
if (typeof window !== 'undefined') {
    window.APIClient = APIClient;
}
''')
        
        # Package.json
        (self.test_repo_path / "src/main/javascript/package.json").write_text('''{
  "name": "test-app",
  "version": "1.0.0",
  "description": "Test application for filesystem ingestion",
  "main": "main.js",
  "scripts": {
    "start": "node main.js",
    "test": "jest",
    "lint": "eslint *.js"
  },
  "dependencies": {
    "axios": "^0.27.2",
    "lodash": "^4.17.21"
  },
  "devDependencies": {
    "jest": "^28.1.0",
    "eslint": "^8.0.0"
  },
  "keywords": ["test", "filesystem", "ingestion"],
  "author": "Test Author",
  "license": "MIT"
}
''')
    
    def _create_documentation_files(self) -> None:
        """Create documentation files."""
        # README
        (self.test_repo_path / "README.md").write_text('''# Test Repository

This is a comprehensive test repository for validating filesystem ingestion functionality.

## Overview

This repository contains various file types and directory structures designed to test:

- Multiple programming languages (Python, JavaScript)
- Documentation files (Markdown, reStructuredText)
- Configuration files (JSON, YAML, TOML)
- Data files (CSV, JSON)
- Binary files
- Special characters in filenames
- Deep directory structures
- Symlinks
- .gitignore pattern respect

## Structure

```
├── src/
│   ├── main/
│   │   ├── python/
│   │   └── javascript/
│   └── test/
├── docs/
├── config/
├── scripts/
└── data/
```

## Testing

This repository is used for integration testing of the filesystem ingestion step.

### Edge Cases Tested

1. **Unicode characters** in filenames and directories
2. **Spaces and special characters** in paths
3. **Deep directory nesting** (10+ levels)
4. **Large files** for performance testing
5. **Symlinks** and their handling
6. **Empty directories**
7. **Files that should be ignored** (.gitignore patterns)

## Performance Considerations

The repository includes files of various sizes to test:
- Small text files (< 1KB)
- Medium files (1KB - 100KB)
- Large files (> 1MB)

## .gitignore Testing

Common patterns tested:
- `*.pyc` - Compiled Python files
- `node_modules/` - Node.js dependencies
- `build/` - Build output directories
- `.git/` - Git metadata
- `*.log` - Log files
''')
        
        # API documentation
        (self.test_repo_path / "docs/api/README.md").write_text('''# API Documentation

## Overview

This document describes the API endpoints available in the test application.

## Endpoints

### GET /api/data

Retrieve data from the server.

**Response:**
```json
{
  "data": [],
  "total": 0,
  "page": 1
}
```

### POST /api/data

Submit new data to the server.

**Request:**
```json
{
  "items": ["item1", "item2"],
  "metadata": {
    "source": "test"
  }
}
```

**Response:**
```json
{
  "success": true,
  "id": "12345"
}
```

## Authentication

All API endpoints require authentication via Bearer token.

```
Authorization: Bearer <token>
```

## Error Handling

The API returns standard HTTP status codes:

- `200` - Success
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `500` - Internal Server Error
''')
        
        # User guide
        (self.test_repo_path / "docs/guides/user_guide.rst").write_text('''User Guide
==========

Getting Started
--------------

This section covers the basic usage of the test application.

Installation
^^^^^^^^^^^

1. Clone the repository::

    git clone https://github.com/example/test-repo.git

2. Install dependencies::

    pip install -r requirements.txt

3. Run the application::

    python src/main/python/app.py

Configuration
^^^^^^^^^^^^

The application can be configured using environment variables:

- ``APP_MODE`` - Application mode (development, production)
- ``LOG_LEVEL`` - Logging level (DEBUG, INFO, WARNING, ERROR)
- ``DATABASE_URL`` - Database connection string

Usage Examples
^^^^^^^^^^^^^

Basic usage::

    from src.main.python.app import DataProcessor
    
    processor = DataProcessor({"mode": "development"})
    result = processor.process_data(["sample", "data"])
    print(result)

Advanced usage::

    import json
    from pathlib import Path
    from src.main.python.utils import load_config, save_data
    
    config = load_config(Path("config/app.json"))
    processor = DataProcessor(config)
    
    data = ["item1", "item2", "item3"]
    result = processor.process_data(data)
    
    save_data(result, Path("output/results.json"))

Troubleshooting
^^^^^^^^^^^^^^

Common issues and solutions:

1. **Import errors**: Ensure all dependencies are installed
2. **Configuration errors**: Check environment variables
3. **Performance issues**: Monitor memory usage with large datasets

For more help, see the API documentation or contact support.
''')
    
    def _create_config_files(self) -> None:
        """Create configuration files."""
        # JSON config
        (self.test_repo_path / "config/app.json").write_text('''{
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "testdb",
    "user": "testuser",
    "password": "testpass"
  },
  "api": {
    "host": "0.0.0.0",
    "port": 8000,
    "timeout": 30,
    "max_requests": 1000
  },
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "logs/app.log"
  },
  "features": {
    "enable_cache": true,
    "enable_metrics": true,
    "enable_debug": false
  }
}
''')
        
        # YAML config
        (self.test_repo_path / "config/environments/production.yaml").write_text('''# Production environment configuration
database:
  host: prod-db.example.com
  port: 5432
  name: production_db
  user: prod_user
  password: ${DATABASE_PASSWORD}
  ssl_mode: require
  pool_size: 20

api:
  host: 0.0.0.0
  port: 8080
  timeout: 60
  max_requests: 10000
  rate_limit: 1000

logging:
  level: WARNING
  format: json
  file: /var/log/app/production.log
  rotation: daily
  retention: 30

features:
  enable_cache: true
  enable_metrics: true
  enable_debug: false
  cache_ttl: 3600

security:
  secret_key: ${SECRET_KEY}
  jwt_expiration: 86400
  cors_origins:
    - https://app.example.com
    - https://admin.example.com

monitoring:
  enable_health_check: true
  health_check_path: /health
  metrics_path: /metrics
  prometheus_enabled: true
''')
        
        # Environment file
        (self.test_repo_path / "config/.env.example").write_text('''# Environment variables example
DATABASE_PASSWORD=your_secure_password_here
SECRET_KEY=your_secret_key_here
API_KEY=your_api_key_here

# Application settings
APP_MODE=development
LOG_LEVEL=DEBUG
DEBUG=true

# External services
REDIS_URL=redis://localhost:6379
ELASTICSEARCH_URL=http://localhost:9200

# Email settings
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_email_password
''')
    
    def _create_data_files(self) -> None:
        """Create data files."""
        # CSV data
        (self.test_repo_path / "data/samples/users.csv").write_text('''id,name,email,age,city
1,John Doe,john.doe@example.com,25,New York
2,Jane Smith,jane.smith@example.com,30,Los Angeles
3,Bob Johnson,bob.johnson@example.com,35,Chicago
4,Alice Williams,alice.williams@example.com,28,Houston
5,Charlie Brown,charlie.brown@example.com,32,Phoenix
6,Diana Davis,diana.davis@example.com,27,Philadelphia
7,Eve Wilson,eve.wilson@example.com,29,San Antonio
8,Frank Miller,frank.miller@example.com,31,San Diego
9,Grace Taylor,grace.taylor@example.com,26,Dallas
10,Henry Anderson,henry.anderson@example.com,33,San Jose
''')
        
        # JSON data
        (self.test_repo_path / "data/samples/products.json").write_text('''{
  "products": [
    {
      "id": 1,
      "name": "Laptop Computer",
      "category": "Electronics",
      "price": 999.99,
      "in_stock": true,
      "specifications": {
        "cpu": "Intel i7",
        "ram": "16GB",
        "storage": "512GB SSD",
        "screen": "15.6 inch"
      },
      "tags": ["computer", "laptop", "portable", "business"]
    },
    {
      "id": 2,
      "name": "Wireless Mouse",
      "category": "Accessories",
      "price": 29.99,
      "in_stock": true,
      "specifications": {
        "connectivity": "Bluetooth",
        "battery_life": "12 months",
        "dpi": "1600",
        "buttons": 3
      },
      "tags": ["mouse", "wireless", "bluetooth", "ergonomic"]
    },
    {
      "id": 3,
      "name": "Monitor Stand",
      "category": "Accessories",
      "price": 79.99,
      "in_stock": false,
      "specifications": {
        "material": "Aluminum",
        "adjustable": true,
        "max_weight": "10kg",
        "compatibility": "VESA 100x100"
      },
      "tags": ["monitor", "stand", "adjustable", "ergonomic"]
    }
  ],
  "metadata": {
    "total_products": 3,
    "last_updated": "2025-05-28T19:00:00Z",
    "version": "1.0"
  }
}
''')
    
    def _create_ignored_files(self) -> None:
        """Create files that should be ignored by .gitignore."""
        # Python compiled files
        (self.test_repo_path / "src/main/python/__pycache__").mkdir(exist_ok=True)
        (self.test_repo_path / "src/main/python/__pycache__/app.cpython-39.pyc").write_bytes(b'\x00\x01\x02\x03' * 100)
        (self.test_repo_path / "src/main/python/utils.pyc").write_bytes(b'\x04\x05\x06\x07' * 50)
        
        # Node modules
        (self.test_repo_path / "node_modules/some-package/index.js").write_text('module.exports = {};')
        (self.test_repo_path / "node_modules/some-package/package.json").write_text('{"name": "some-package"}')
        
        # Build files
        (self.test_repo_path / "build/output/app.min.js").write_text('(function(){console.log("minified")})();')
        (self.test_repo_path / "build/output/styles.min.css").write_text('body{margin:0;padding:0}')
        
        # Log files
        (self.test_repo_path / "app.log").write_text('''2025-05-28 19:00:00,000 - INFO - Application started
2025-05-28 19:00:01,000 - DEBUG - Processing request
2025-05-28 19:00:02,000 - WARNING - Rate limit approaching
2025-05-28 19:00:03,000 - ERROR - Database connection failed
''')
        
        # Git directory
        (self.test_repo_path / ".git/objects/abc123").write_bytes(b'\x00\x01\x02\x03' * 200)
        (self.test_repo_path / ".git/refs/heads").mkdir(parents=True, exist_ok=True)
        (self.test_repo_path / ".git/refs/heads/main").write_text('abc123def456')
        
        # Temporary files
        (self.test_repo_path / "temp.tmp").write_text('Temporary data')
        (self.test_repo_path / "cache.temp").write_text('Cache data')
    
    def _create_edge_case_files(self) -> None:
        """Create files with edge case names and content."""
        # Unicode filenames
        (self.test_repo_path / "unicode_测试_文件.txt").write_text('Unicode content: 测试内容')
        (self.test_repo_path / "émoji_🚀_file.md").write_text('# Emoji File 🚀\n\nThis file has emojis in its name!')
        
        # Special characters
        (self.test_repo_path / "file with spaces.txt").write_text('Content of file with spaces')
        (self.test_repo_path / "file-with-dashes.txt").write_text('Content of file with dashes')
        (self.test_repo_path / "file_with_underscores.txt").write_text('Content of file with underscores')
        (self.test_repo_path / "file.with.dots.txt").write_text('Content of file with dots')
        (self.test_repo_path / "file!@#$%^&()special.txt").write_text('Content of file with special chars')
        
        # Very long filename
        long_name = "a" * 200 + ".txt"
        try:
            (self.test_repo_path / long_name).write_text('Content of very long filename')
        except OSError:
            # Filename too long, create a shorter one
            (self.test_repo_path / ("a" * 100 + ".txt")).write_text('Content of long filename')
        
        # Files with no extension
        (self.test_repo_path / "Makefile").write_text('''all: build test

build:
\techo "Building application"

test:
\techo "Running tests"

clean:
\techo "Cleaning build artifacts"

.PHONY: all build test clean
''')
        
        (self.test_repo_path / "Dockerfile").write_text('''FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "src/main/python/app.py"]
''')
        
        # Binary-like content
        (self.test_repo_path / "binary_data.bin").write_bytes(bytes(range(256)) * 10)
        
        # Empty file
        (self.test_repo_path / "empty_file.txt").touch()
        
        # File with only whitespace
        (self.test_repo_path / "whitespace_only.txt").write_text('   \n\n\t\t\n   ')
    
    def _create_large_files(self) -> None:
        """Create large files for performance testing."""
        # Medium file (100KB)
        medium_content = "This is a medium sized file for testing.\n" * 2500
        (self.test_repo_path / "data/medium_file.txt").write_text(medium_content)
        
        # Large file (1MB)
        large_content = "This is a large file for performance testing. " * 20000
        (self.test_repo_path / "data/large_file.txt").write_text(large_content)
        
        # Very large file marked for ignoring (5MB)
        very_large_content = "This file should be ignored due to .large extension. " * 100000
        (self.test_repo_path / "data/very_large_file.large").write_text(very_large_content)
    
    def _create_symlinks(self) -> None:
        """Create symbolic links for testing."""
        try:
            # Link to existing file
            (self.test_repo_path / "link_to_readme.md").symlink_to("README.md")
            
            # Link to directory
            (self.test_repo_path / "link_to_src").symlink_to("src")
            
            # Broken link
            (self.test_repo_path / "broken_link.txt").symlink_to("nonexistent_file.txt")
            
            # Link to link (chained)
            (self.test_repo_path / "link_to_link.md").symlink_to("link_to_readme.md")
            
        except OSError as e:
            logger.warning(f"Could not create symlinks: {e}")
    
    def capture_cli_logs(self, command: List[str]) -> tuple[int, str, str]:
        """Execute CLI command and capture all output."""
        logger.info(f"Executing CLI command: {' '.join(command)}")
        self.start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                cwd=self.test_repo_path,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            self.end_time = time.time()
            execution_time = self.end_time - self.start_time
            
            logger.info(f"Command completed in {execution_time:.2f} seconds")
            logger.info(f"Return code: {result.returncode}")
            logger.debug(f"STDOUT:\n{result.stdout}")
            
            if result.stderr:
                logger.warning(f"STDERR:\n{result.stderr}")
                
            self.ingestion_logs.extend(result.stdout.split('\n'))
            if result.stderr:
                self.ingestion_logs.extend(result.stderr.split('\n'))
                
            return result.returncode, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            self.end_time = time.time()
            logger.error("Command timed out after 5 minutes")
            raise
        except Exception as e:
            self.end_time = time.time()
            logger.error(f"Command execution failed: {e}")
            raise
    
    def get_execution_time(self) -> Optional[float]:
        """Get the execution time of the last command."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


class Neo4jTestValidator:
    """Validator for Neo4j graph content after ingestion."""
    
    def __init__(self):
        settings = get_settings()
        self.connector = Neo4jConnector(
            uri=settings.neo4j.uri,
            username=settings.neo4j.username,
            password=settings.neo4j.password.get_secret_value(),
            database=settings.neo4j.database
        )
    
    async def validate_graph_structure(self, repository_path: Path) -> Dict[str, any]:
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
            "errors": []
        }
        
        try:
            # Get all nodes from the graph
            query = """
            MATCH (n)
            RETURN 
                n.path as path,
                n.type as type,
                n.name as name,
                labels(n) as labels
            """
            
            async with self.connector.get_async_session() as session:
                result = await session.run(query)
                graph_nodes = await result.data()
                
            validation_results["total_nodes"] = len(graph_nodes)
            
            # Categorize nodes
            graph_files = set()
            graph_directories = set()
            
            for node in graph_nodes:
                if 'File' in node['labels']:
                    validation_results["file_nodes"] += 1
                    if node['path']:
                        graph_files.add(node['path'])
                elif 'Directory' in node['labels']:
                    validation_results["directory_nodes"] += 1
                    if node['path']:
                        graph_directories.add(node['path'])
                elif 'Repository' in node['labels']:
                    validation_results["repository_nodes"] += 1
                    
            # Get expected files and directories from filesystem
            expected_files = set()
            expected_directories = set()
            
            for item in repository_path.rglob('*'):
                relative_path = str(item.relative_to(repository_path))
                
                if item.is_file():
                    expected_files.add(relative_path)
                elif item.is_dir():
                    expected_directories.add(relative_path)
            
            # Load .gitignore patterns for validation
            gitignore_path = repository_path / ".gitignore"
            ignored_patterns = []
            if gitignore_path.exists():
                ignored_patterns = [
                    line.strip() for line in gitignore_path.read_text().split('\n')
                    if line.strip() and not line.startswith('#')
                ]
            
            # Check for files that should be ignored but are in the graph
            for file_path in graph_files:
                if self._should_be_ignored(file_path, ignored_patterns):
                    validation_results["ignored_files_present"].append(file_path)
                    validation_results["structure_valid"] = False
            
            # Filter expected files to remove ignored ones
            expected_files_filtered = {
                f for f in expected_files 
                if not self._should_be_ignored(f, ignored_patterns)
            }
            
            # Check for missing files
            validation_results["missing_files"] = list(expected_files_filtered - graph_files)
            
            # Check for extra files
            validation_results["extra_files"] = list(graph_files - expected_files_filtered)
            
            # Count relationships
            relationship_query = "MATCH ()-[r]->() RETURN count(r) as count"
            async with self.connector.get_async_session() as session:
                result = await session.run(relationship_query)
                rel_data = await result.single()
                validation_results["relationships"] = rel_data['count'] if rel_data else 0
            
            if validation_results["missing_files"] or validation_results["extra_files"]:
                validation_results["structure_valid"] = False
                
        except Exception as e:
            validation_results["errors"].append(f"Graph validation failed: {e!s}")
            validation_results["structure_valid"] = False
            logger.error(f"Graph validation error: {e}")
            
        return validation_results
    
    def _should_be_ignored(self, file_path: str, patterns: List[str]) -> bool:
        """Check if a file should be ignored based on .gitignore patterns."""
        for pattern in patterns:
            pattern = pattern.strip()
            if not pattern or pattern.startswith('#'):
                continue
                
            # Simple pattern matching (simplified .gitignore implementation)
            if pattern.endswith('/'):
                # Directory pattern
                if file_path.startswith(pattern[:-1]) or f"/{pattern[:-1]}" in file_path:
                    return True
            elif '*' in pattern:
                # Wildcard pattern (simplified)
                if pattern.startswith('*.'):
                    # Extension pattern
                    ext = pattern[2:]
                    if file_path.endswith(f'.{ext}'):
                        return True
            else:
                # Exact match or substring
                if pattern in file_path:
                    return True
                    
        return False


@pytest.mark.integration
@pytest.mark.slow
class TestFilesystemIngestionE2E:
    """Comprehensive end-to-end tests for filesystem ingestion."""
    
    @pytest.fixture(autouse=True)
    async def setup_and_cleanup(self):
        """Set up test environment and clean up afterwards."""
        # Create temporary directory for test repository
        self.temp_dir = tempfile.mkdtemp(prefix="codestory_fs_test_")
        self.test_repo_path = Path(self.temp_dir)
        
        logger.info(f"Created test directory: {self.temp_dir}")
        
        # Initialize helper and validator
        self.helper = FilesystemIngestionTestHelper(self.test_repo_path)
        self.validator = Neo4jTestValidator()
        
        # Start CodeStory services
        await self._start_codestory_services()
        
        yield
        
        # Stop services
        await self._stop_codestory_services()
        
        # Cleanup
        try:
            shutil.rmtree(self.temp_dir)
            logger.info(f"Cleaned up test directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up test directory: {e}")
    
    async def _start_codestory_services(self):
        """Start CodeStory services for testing.

        Refactored to skip starting the stack if all required containers are already running and healthy.
        """
        import re

        # Ensure Redis URI points at container before settings are loaded
        os.environ["REDIS__URI"] = "redis://redis:6380/0"
        os.environ["REDIS_URI"] = "redis://redis:6380/0"
        logger.info("Checking CodeStory service container status...")

        # Map service keys to both SERVICE column and container name
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
                        # Accept "Up" with "(healthy)" or "(health: starting)" or "Started" for service
                        if any(pat in line for pat in patterns) and (
                            ("Up" in line and ("(healthy)" in line or "(health: starting)" in line))
                            or "Started" in line
                        ):
                            found.add(svc)
                    else:
                        if any(pat in line for pat in patterns) and "Up" in line and "(healthy)" in line:
                            found.add(svc)
            return found

        # Check if all required services are running and healthy
        try:
            ps_proc = subprocess.run(
                ["docker", "compose", "ps", "--status=running"],
                capture_output=True,
                text=True,
                timeout=15
            )
            if ps_proc.returncode == 0:
                healthy_services = parse_ps_output(ps_proc.stdout)
        except Exception as e:
            logger.warning(f"Could not check docker compose status: {e}")

        if healthy_services == set(required_services.keys()):
            logger.info("All required CodeStory containers are already running and healthy. Skipping stack startup.")
            # Still wait for readiness in case services are not fully ready
            await self._wait_for_services_ready()
            return

        logger.info("Not all containers are healthy. Restarting stack...")

        # Stop any existing services first
        try:
            subprocess.run(["codestory", "stop"], capture_output=True, timeout=30)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass  # Ignore errors if services weren't running

        # Start services
        try:
            result = subprocess.run(
                ["codestory", "start"],
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout for service startup
            )

            if result.returncode != 0:
                logger.error(f"Failed to start services: {result.stderr}")
                # Try to start manually with docker compose
                logger.info("Attempting manual docker compose startup...")
                subprocess.run(
                    ["docker", "compose", "--env-file", ".env", "up", "-d"],
                    capture_output=True,
                    timeout=120
                )

            # Wait for services to be ready
            await self._wait_for_services_ready()

        except subprocess.TimeoutExpired:
            logger.error("Service startup timed out")
            raise
        except Exception as e:
            logger.error(f"Error starting services: {e}")
            raise
    
    async def _stop_codestory_services(self):
        """Stop CodeStory services after testing."""
        logger.info("Stopping CodeStory services...")
        
        try:
            subprocess.run(
                ["codestory", "stop"],
                capture_output=True,
                timeout=60
            )
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            # Force stop with docker compose
            subprocess.run(
                ["docker", "compose", "down", "--remove-orphans"],
                capture_output=True,
                timeout=60
            )
    
    async def _wait_for_services_ready(self, max_wait=60):
        """Wait for all required services to be running and healthy."""
        import re

        logger.info("Waiting for all CodeStory containers to be running and healthy...")

        # Map service keys to both SERVICE column and container name
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
                        # Accept "Up" with "(healthy)" or "(health: starting)" or "Started" for service
                        if any(pat in line for pat in patterns) and (
                            ("Up" in line and ("(healthy)" in line or "(health: starting)" in line))
                            or "Started" in line
                        ):
                            found.add(svc)
                    else:
                        if any(pat in line for pat in patterns) and "Up" in line and "(healthy)" in line:
                            found.add(svc)
            return found

        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                ps_proc = subprocess.run(
                    ["docker", "compose", "ps", "--status=running"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if ps_proc.returncode == 0:
                    healthy_services = parse_ps_output(ps_proc.stdout)
                    if healthy_services == set(required_services.keys()):
                        logger.info("All required containers are running and healthy.")
                        return
            except Exception as e:
                logger.warning(f"Error checking container health: {e}")

            await asyncio.sleep(2)

        # If we get here, services didn't start properly
        docker_result = subprocess.run(
            ["docker", "ps", "-a"],
            capture_output=True,
            text=True
        )
        logger.error(f"Services not ready after {max_wait}s. Docker status:\n{docker_result.stdout}")

        # Check service logs for debugging
        try:
            service_logs = subprocess.run(
                ["docker", "logs", "codestory-service"],
                capture_output=True,
                text=True
            )
            logger.error(f"Service logs:\n{service_logs.stdout}\n{service_logs.stderr}")
        except Exception:
            pass

        raise TimeoutError(f"Services not ready after {max_wait} seconds")
    
    async def test_comprehensive_filesystem_ingestion(self):
        """Test comprehensive filesystem ingestion with realistic repository."""
        logger.info("Starting comprehensive filesystem ingestion test")
        
        # Step 1: Create test repository
        logger.info("Step 1: Creating test repository structure")
        self.helper.create_test_repository()
        
        # Verify test repository was created correctly
        total_items = len(list(self.test_repo_path.rglob('*')))
        assert total_items > 50, f"Test repository should have >50 items, got {total_items}"
        
        gitignore_exists = (self.test_repo_path / ".gitignore").exists()
        assert gitignore_exists, ".gitignore file should exist"
        
        # Step 2: Execute filesystem ingestion via CLI
        logger.info("Step 2: Executing filesystem ingestion via CLI")
        
        command = [
            "codestory", "ingest", "start",
            str(self.test_repo_path),
            "--steps", "filesystem",
            "--verbose"
        ]
        
        returncode, stdout, stderr = self.helper.capture_cli_logs(command)
        
        # Assert command completed successfully
        assert returncode == 0, f"CLI command failed with return code {returncode}. STDERR: {stderr}"
        
        # Step 3: Validate execution time
        logger.info("Step 3: Validating execution time")
        execution_time = self.helper.get_execution_time()
        assert execution_time is not None, "Execution time should be recorded"
        assert execution_time < 300, f"Ingestion took too long: {execution_time:.2f}s (max: 300s)"
        
        logger.info(f"Ingestion completed in {execution_time:.2f} seconds")
        
        # Step 4: Validate progress reporting
        logger.info("Step 4: Validating progress reporting")
        logs = '\n'.join(self.helper.ingestion_logs)
        
        # Check for progress indicators
        assert "progress" in logs.lower() or "processing" in logs.lower(), \
            "Logs should contain progress indicators"
            
        # Step 5: Validate Neo4j graph structure
        logger.info("Step 5: Validating Neo4j graph structure")
        validation_results = await self.validator.validate_graph_structure(self.test_repo_path)
        
        # Assert validation passed
        assert validation_results["structure_valid"], \
            f"Graph structure validation failed: {validation_results['errors']}"
        
        # Check node counts
        assert validation_results["total_nodes"] > 0, "Graph should contain nodes"
        assert validation_results["file_nodes"] > 0, "Graph should contain file nodes"
        assert validation_results["directory_nodes"] > 0, "Graph should contain directory nodes"
        assert validation_results["relationships"] > 0, "Graph should contain relationships"
        
        # Step 6: Validate .gitignore patterns are respected
        logger.info("Step 6: Validating .gitignore pattern respect")
        assert len(validation_results["ignored_files_present"]) == 0, \
            f"Ignored files found in graph: {validation_results['ignored_files_present']}"
        
        # Step 7: Validate completeness
        logger.info("Step 7: Validating ingestion completeness")
        
        max_missing = 5  # Allow some missing files for symlinks, etc.
        assert len(validation_results["missing_files"]) <= max_missing, \
            f"Too many missing files: {validation_results['missing_files']}"
            
        max_extra = 5  # Allow some extra files for metadata, etc.
        assert len(validation_results["extra_files"]) <= max_extra, \
            f"Too many extra files: {validation_results['extra_files']}"
        
        # Log summary
        logger.info("Test completed successfully!")
        logger.info(f"Execution time: {execution_time:.2f}s")
        logger.info(f"Total nodes: {validation_results['total_nodes']}")
        logger.info(f"File nodes: {validation_results['file_nodes']}")
        logger.info(f"Directory nodes: {validation_results['directory_nodes']}")
        logger.info(f"Relationships: {validation_results['relationships']}")
        
        # Assert overall success
        assert True, "Comprehensive filesystem ingestion test passed"
    
    async def test_gitignore_patterns_comprehensive(self):
        """Test comprehensive .gitignore pattern handling."""
        logger.info("Starting comprehensive .gitignore pattern test")
        
        # Create simplified test repository with focused ignore patterns
        simple_repo = self.test_repo_path / "simple"
        simple_repo.mkdir()
        
        # Create .gitignore with specific patterns to test
        gitignore_content = """
*.pyc
__pycache__/
node_modules/
build/
*.log
.git/
*.tmp
*.temp
temp/
        """.strip()
        
        (simple_repo / ".gitignore").write_text(gitignore_content)
        
        # Create files that should be ignored
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
        
        # Create files that should NOT be ignored
        (simple_repo / "main.py").write_text("python code")
        (simple_repo / "src").mkdir()
        (simple_repo / "src/app.js").write_text("js code")
        (simple_repo / "README.md").write_text("documentation")
        
        # Run ingestion
        command = [
            "codestory", "ingest", "start",
            str(simple_repo),
            "--steps", "filesystem"
        ]
        
        returncode, stdout, stderr = self.helper.capture_cli_logs(command)
        assert returncode == 0, f"Ingestion failed: {stderr}"
        
        # Validate graph respects .gitignore
        validation_results = await self.validator.validate_graph_structure(simple_repo)
        
        # Should have no ignored files in graph
        assert len(validation_results["ignored_files_present"]) == 0, \
            f"Found ignored files in graph: {validation_results['ignored_files_present']}"
        
        # Should have the non-ignored files
        assert validation_results["file_nodes"] >= 3, \
            "Should have at least main.py, app.js, README.md, and .gitignore"
    
    async def test_performance_large_repository(self):
        """Test performance with a large repository structure."""
        logger.info("Starting performance test with large repository")
        
        # Create large repository structure
        large_repo = self.test_repo_path / "large"
        large_repo.mkdir()
        
        # Create deep directory structure
        current_dir = large_repo
        for i in range(15):  # 15 levels deep
            current_dir = current_dir / f"level_{i}"
            current_dir.mkdir()
            
            # Add files at each level
            for j in range(5):
                (current_dir / f"file_{j}.txt").write_text(f"Content at level {i}, file {j}")
        
        # Create many files in root
        for i in range(100):
            (large_repo / f"root_file_{i}.py").write_text(f"def function_{i}():\n    return {i}")
        
        # Create large file (1MB)
        large_content = "Large file content line.\n" * 50000
        (large_repo / "large_file.txt").write_text(large_content)
        
        # Run ingestion with time limit
        command = [
            "codestory", "ingest", "start",
            str(large_repo),
            "--steps", "filesystem"
        ]
        
        start_time = time.time()
        returncode, stdout, stderr = self.helper.capture_cli_logs(command)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Assert reasonable performance
        assert returncode == 0, f"Large repository ingestion failed: {stderr}"
        assert execution_time < 120, f"Large repository took too long: {execution_time:.2f}s (max: 120s)"
        
        # Validate completeness
        validation_results = await self.validator.validate_graph_structure(large_repo)
        assert validation_results["structure_valid"], "Large repository structure should be valid"
        assert validation_results["file_nodes"] >= 100, "Should have many file nodes"
        
        logger.info(f"Large repository processed in {execution_time:.2f}s")
    
    async def test_edge_cases_and_error_handling(self):
        """Test edge cases and error handling scenarios."""
        logger.info("Starting edge cases and error handling test")
        
        # Create repository with edge cases
        edge_repo = self.test_repo_path / "edge"
        edge_repo.mkdir()
        
        # Empty directory
        (edge_repo / "empty").mkdir()
        
        # File with special characters
        (edge_repo / "special_chars_!@#$%^&().txt").write_text("special content")
        
        # Unicode filename
        (edge_repo / "unicode_测试.txt").write_text("unicode content")
        
        # Very long content
        long_content = "Very long line " * 10000
        (edge_repo / "long_content.txt").write_text(long_content)
        
        # Binary content
        (edge_repo / "binary.bin").write_bytes(bytes(range(256)) * 100)
        
        # Symlink (if supported)
        try:
            (edge_repo / "link.txt").symlink_to("special_chars_!@#$%^&().txt")
        except OSError:
            pass  # Symlinks not supported on this system
        
        # Run ingestion
        command = [
            "codestory", "ingest", "start",
            str(edge_repo),
            "--steps", "filesystem"
        ]
        
        returncode, stdout, stderr = self.helper.capture_cli_logs(command)
        
        # Should complete successfully despite edge cases
        assert returncode == 0, f"Edge case ingestion failed: {stderr}"
        
        # Validate graph was created
        validation_results = await self.validator.validate_graph_structure(edge_repo)
        assert validation_results["total_nodes"] > 0, "Should have nodes despite edge cases"
        
        logger.info("Edge cases handled successfully")


if __name__ == "__main__":
    # Allow running the test directly for debugging
    pytest.main([__file__, "-v", "-s"])