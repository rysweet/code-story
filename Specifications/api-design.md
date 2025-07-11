# Code Story: API Design

This document outlines the API design for the Code Story simplified architecture. It defines the HTTP endpoints, request/response formats, and authentication approach for the API service.

## API Overview

The Code Story API provides RESTful access to the code knowledge graph, allowing clients to:

1. Manage repositories
2. Control ingestion processes
3. Query the knowledge graph
4. Access code summaries and documentation

The API follows RESTful principles with consistent resource naming, proper HTTP method usage, and clear response structures.

## API Base URL

All API endpoints are under the `/api/v1` base path to allow for versioning.

## Authentication

For local development, authentication is optional and can be disabled. When enabled, the API supports:

- API key authentication (via `X-API-Key` header)
- Bearer token authentication (via `Authorization: Bearer <token>` header)

Authentication configuration:

```yaml
api:
  auth:
    enabled: true|false
    api_key: "your-api-key"  # Only for development
    # Additional auth settings
```

## Common Response Format

All API responses follow a consistent format:

```json
{
  "success": true|false,
  "data": { ... },  // Main response data (when success=true)
  "error": {  // Present only when success=false
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": { ... }  // Optional additional error details
  }
}
```

## Error Handling

The API uses standard HTTP status codes:

- `200 OK` - Successful request
- `201 Created` - Resource created
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource conflict (e.g., duplicate repository)
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

Error responses include details to help with debugging:

```json
{
  "success": false,
  "error": {
    "code": "INVALID_REPOSITORY_PATH",
    "message": "Repository path does not exist or is not accessible",
    "details": {
      "path": "/path/to/nonexistent/repo",
      "reason": "Directory does not exist"
    }
  }
}
```

## API Endpoints

### Repository Management

#### List Repositories

```
GET /api/v1/repositories
```

**Query Parameters:**
- `limit` (optional) - Maximum number of results (default: 50)
- `offset` (optional) - Pagination offset (default: 0)
- `status` (optional) - Filter by status (`active`, `ingesting`, `error`)

**Response:**
```json
{
  "success": true,
  "data": {
    "repositories": [
      {
        "id": "repo-uuid",
        "path": "/path/to/repo",
        "name": "repo-name",
        "status": "active",
        "last_ingestion": "2023-07-15T12:34:56Z",
        "file_count": 1234,
        "node_count": 5678
      },
      ...
    ],
    "total": 10,
    "limit": 50,
    "offset": 0
  }
}
```

#### Get Repository Details

```
GET /api/v1/repositories/{id}
```

**Path Parameters:**
- `id` - Repository UUID

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "repo-uuid",
    "path": "/path/to/repo",
    "name": "repo-name",
    "status": "active",
    "last_ingestion": "2023-07-15T12:34:56Z",
    "file_count": 1234,
    "node_count": 5678,
    "ingestion_history": [
      {
        "job_id": "job-uuid",
        "start_time": "2023-07-15T12:00:00Z",
        "end_time": "2023-07-15T12:34:56Z",
        "status": "succeeded"
      },
      ...
    ],
    "statistics": {
      "language_breakdown": {
        "Python": 45.2,
        "JavaScript": 30.1,
        "HTML": 15.7,
        "CSS": 9.0
      },
      "file_types": {
        ".py": 234,
        ".js": 123,
        ".html": 56,
        ".css": 45
      }
    }
  }
}
```

#### Add Repository

```
POST /api/v1/repositories
```

**Request Body:**
```json
{
  "path": "/path/to/repo",
  "name": "repo-name",  // Optional, defaults to directory name
  "auto_ingest": true  // Optional, start ingestion automatically
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "repo-uuid",
    "path": "/path/to/repo",
    "name": "repo-name",
    "status": "pending",
    "job_id": "job-uuid"  // Only present if auto_ingest=true
  }
}
```

#### Remove Repository

```
DELETE /api/v1/repositories/{id}
```

**Path Parameters:**
- `id` - Repository UUID

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "repo-uuid",
    "message": "Repository removed successfully"
  }
}
```

### Ingestion Control

#### Start Ingestion

```
POST /api/v1/repositories/{id}/ingest
```

**Path Parameters:**
- `id` - Repository UUID

**Request Body:**
```json
{
  "steps": ["filesystem", "blarify", "summarizer", "docgrapher"],  // Optional
  "config": {  // Optional step-specific configuration
    "blarify": {
      "language_filter": ["python", "javascript"]
    },
    "summarizer": {
      "max_tokens": 200
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "job_id": "job-uuid",
    "repository_id": "repo-uuid",
    "status": "pending",
    "steps": ["filesystem", "blarify", "summarizer", "docgrapher"]
  }
}
```

#### Get Job Status

```
GET /api/v1/jobs/{id}
```

**Path Parameters:**
- `id` - Job UUID

**Response:**
```json
{
  "success": true,
  "data": {
    "job_id": "job-uuid",
    "repository_id": "repo-uuid",
    "status": "running",
    "current_step": "blarify",
    "progress": 0.45,
    "start_time": "2023-07-15T12:00:00Z",
    "estimated_completion": "2023-07-15T12:30:00Z",
    "steps": [
      {
        "name": "filesystem",
        "status": "completed",
        "start_time": "2023-07-15T12:00:00Z",
        "end_time": "2023-07-15T12:05:00Z",
        "result": {
          "file_count": 1234
        }
      },
      {
        "name": "blarify",
        "status": "running",
        "start_time": "2023-07-15T12:05:01Z",
        "progress": 0.45
      },
      {
        "name": "summarizer",
        "status": "pending"
      },
      {
        "name": "docgrapher",
        "status": "pending"
      }
    ]
  }
}
```

#### Cancel Job

```
POST /api/v1/jobs/{id}/cancel
```

**Path Parameters:**
- `id` - Job UUID

**Response:**
```json
{
  "success": true,
  "data": {
    "job_id": "job-uuid",
    "repository_id": "repo-uuid",
    "status": "cancelled",
    "message": "Job cancelled successfully"
  }
}
```

#### List Jobs

```
GET /api/v1/jobs
```

**Query Parameters:**
- `repository_id` (optional) - Filter by repository
- `status` (optional) - Filter by status (`pending`, `running`, `completed`, `failed`, `cancelled`)
- `limit` (optional) - Maximum number of results (default: 50)
- `offset` (optional) - Pagination offset (default: 0)

**Response:**
```json
{
  "success": true,
  "data": {
    "jobs": [
      {
        "job_id": "job-uuid",
        "repository_id": "repo-uuid",
        "repository_name": "repo-name",
        "status": "running",
        "current_step": "blarify",
        "progress": 0.45,
        "start_time": "2023-07-15T12:00:00Z"
      },
      ...
    ],
    "total": 5,
    "limit": 50,
    "offset": 0
  }
}
```

### Graph Querying

#### Execute Graph Query

```
POST /api/v1/graph/query
```

**Request Body:**
```json
{
  "query": "MATCH (f:File)-[:CONTAINS]->(c:Class) WHERE f.path CONTAINS 'models' RETURN f.path, c.name",
  "parameters": {
    "path_pattern": "models"
  },
  "limit": 100  // Optional
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "f.path": "src/models/user.py",
        "c.name": "User"
      },
      {
        "f.path": "src/models/product.py",
        "c.name": "Product"
      },
      ...
    ],
    "count": 15
  }
}
```

#### Get Node by ID

```
GET /api/v1/nodes/{id}
```

**Path Parameters:**
- `id` - Node UUID

**Query Parameters:**
- `include_relationships` (optional) - Include relationships (default: false)
- `relationship_depth` (optional) - Depth of relationships to include (default: 1)

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "node-uuid",
    "labels": ["Class"],
    "properties": {
      "name": "User",
      "path": "src/models/user.py",
      "line_number": 15,
      "summary": "User class representing application users"
    },
    "relationships": [
      {
        "id": "rel-uuid",
        "type": "CONTAINS",
        "direction": "incoming",
        "node": {
          "id": "file-node-uuid",
          "labels": ["File"],
          "properties": {
            "path": "src/models/user.py",
            "name": "user.py"
          }
        }
      },
      {
        "id": "rel-uuid",
        "type": "DEFINES",
        "direction": "outgoing",
        "node": {
          "id": "method-node-uuid",
          "labels": ["Method"],
          "properties": {
            "name": "authenticate",
            "line_number": 25
          }
        }
      },
      ...
    ]
  }
}
```

#### Search Nodes

```
GET /api/v1/nodes/search
```

**Query Parameters:**
- `q` - Search query string
- `type` (optional) - Filter by node type(s) (e.g., `File,Class,Method`)
- `limit` (optional) - Maximum number of results (default: 50)
- `offset` (optional) - Pagination offset (default: 0)

**Response:**
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "id": "node-uuid",
        "labels": ["Class"],
        "properties": {
          "name": "UserAuthentication",
          "path": "src/auth/user_auth.py",
          "summary": "Handles user authentication and session management"
        },
        "score": 0.92
      },
      ...
    ],
    "total": 25,
    "limit": 50,
    "offset": 0
  }
}
```

### File Access

#### Get File Content

```
GET /api/v1/repositories/{repo_id}/files
```

**Path Parameters:**
- `repo_id` - Repository UUID

**Query Parameters:**
- `path` - File path relative to repository root

**Response:**
```json
{
  "success": true,
  "data": {
    "path": "src/models/user.py",
    "name": "user.py",
    "content": "class User:\n    def __init__(self, username, email):\n        self.username = username\n        self.email = email\n",
    "size": 1234,
    "last_modified": "2023-07-15T12:34:56Z",
    "language": "python"
  }
}
```

#### Get File Structure

```
GET /api/v1/repositories/{repo_id}/structure
```

**Path Parameters:**
- `repo_id` - Repository UUID

**Query Parameters:**
- `path` (optional) - Starting directory path (default: repository root)
- `depth` (optional) - Directory depth to traverse (default: 1)
- `include_files` (optional) - Include files in response (default: true)

**Response:**
```json
{
  "success": true,
  "data": {
    "path": "/",
    "type": "directory",
    "name": "repo-name",
    "children": [
      {
        "path": "/src",
        "type": "directory",
        "name": "src",
        "children": [
          {
            "path": "/src/models",
            "type": "directory",
            "name": "models",
            "children": [
              {
                "path": "/src/models/user.py",
                "type": "file",
                "name": "user.py",
                "size": 1234,
                "language": "python"
              },
              ...
            ]
          },
          ...
        ]
      },
      ...
    ]
  }
}
```

### Summaries and Documentation

#### Get Code Summary

```
GET /api/v1/repositories/{repo_id}/summary
```

**Path Parameters:**
- `repo_id` - Repository UUID

**Query Parameters:**
- `path` (optional) - File or directory path to summarize (default: repository root)
- `max_tokens` (optional) - Maximum length of summary (default: 500)

**Response:**
```json
{
  "success": true,
  "data": {
    "path": "/src/models",
    "name": "models",
    "summary": "This directory contains data models for the application. Key classes include User for authentication and session management, Product for inventory tracking, and Order for purchase processing. Models handle data validation, persistence, and business logic related to their domain.",
    "components": [
      {
        "path": "/src/models/user.py",
        "name": "user.py",
        "type": "file",
        "summary": "Defines the User class for authentication and profile management."
      },
      ...
    ]
  }
}
```

#### Get Node Documentation

```
GET /api/v1/nodes/{id}/documentation
```

**Path Parameters:**
- `id` - Node UUID

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "node-uuid",
    "name": "authenticate",
    "type": "Method",
    "documentation": {
      "description": "Authenticates a user with the provided credentials.",
      "parameters": [
        {
          "name": "username",
          "type": "str",
          "description": "The user's username or email"
        },
        {
          "name": "password",
          "type": "str",
          "description": "The user's password"
        }
      ],
      "returns": {
        "type": "bool",
        "description": "True if authentication succeeds, False otherwise"
      },
      "examples": [
        {
          "code": "user.authenticate('john', 'secret')",
          "description": "Basic authentication example"
        }
      ],
      "notes": "This method performs rate limiting to prevent brute force attacks."
    }
  }
}
```

## API Reference Documentation

The API includes built-in documentation using Swagger UI, available at:

```
/api/docs
```

This provides an interactive documentation interface where endpoints can be explored and tested.

## Versioning

The API uses a simple versioning scheme with the `/api/v1` prefix. Future versions will use `/api/v2`, etc.

Changes that maintain backward compatibility may be added to the current version. Breaking changes require a new version.

## Rate Limiting

For production deployments, rate limiting is available:

```yaml
api:
  rate_limiting:
    enabled: true
    default_limit: 100  # requests per minute
    token_limit: 1000   # requests per minute for authenticated users
```

Rate limiting headers are included in responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1626355212
```

## Pagination

List endpoints support consistent pagination using `limit` and `offset` parameters. Responses include pagination metadata:

```json
{
  "success": true,
  "data": {
    "items": [...],
    "total": 100,
    "limit": 20,
    "offset": 40,
    "has_more": true
  }
}
```

## CORS Support

Cross-Origin Resource Sharing is configurable:

```yaml
api:
  cors:
    enabled: true
    allow_origins: ["http://localhost:3000", "https://example.com"]
    allow_methods: ["GET", "POST", "PUT", "DELETE"]
    allow_headers: ["Content-Type", "Authorization"]
    max_age: 3600
```

## Monitoring and Health Check

The API includes endpoints for monitoring:

```
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "storage": "connected",
  "uptime_seconds": 3600,
  "timestamp": "2023-07-15T12:34:56Z"
}
```

## Implementation Considerations

1. **FastAPI Framework**: The API will be implemented using FastAPI for performance and ease of development
2. **Dependency Injection**: Components will be provided via FastAPI's dependency injection system
3. **Async Support**: Endpoints will use async/await for optimal performance
4. **OpenAPI Documentation**: API will be documented using OpenAPI annotations
5. **Input Validation**: Pydantic models will validate all inputs
6. **Error Handling**: Consistent error handling middleware will format all errors
7. **Logging**: Comprehensive request logging for debugging and monitoring
8. **Testing**: Extensive test coverage using pytest and FastAPI's TestClient
