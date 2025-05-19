# Repository Mounting for Code Story

This document explains how repositories can be mounted into the Code Story containers for ingestion and analysis.

## Overview

Code Story requires access to repository files for ingestion. When running as Docker containers, repositories must be mounted from the host system into the containers. This is accomplished through two mechanisms:

1. **Static Mounting** - Using Docker volume mounts at container startup
2. **Dynamic Mounting** - Adding mounts to running containers without a restart

## Automatic Repository Mounting

The CLI has built-in repository mounting capabilities that handle the details automatically.

### Using the CLI Directly

The CLI will automatically mount repositories when running the `ingest start` command:

```bash
codestory ingest start /path/to/your/repository
```

The CLI detects if you're connected to a containerized service and:
1. Checks if the repository is already mounted
2. If not, it mounts the repository automatically
3. Maps local paths to container paths for proper access inside the containers

### Mounting Without Ingestion

If you only want to mount a repository without starting ingestion:

```bash
codestory ingest mount /path/to/your/repository [options]
```

Options:
- `--force-remount`: Force remount even if the repository appears to be mounted
- `--debug`: Show additional debug information

### Additional Options for Ingest Start

The `ingest start` command supports several options for repository mounting:

```bash
codestory ingest start /path/to/your/repository [options]
```

Options:
- `--no-progress`: Don't show progress updates during ingestion
- `--container`: Force container path mapping
- `--path-prefix PATH`: Container path prefix where repositories are mounted (default: /repositories)
- `--auto-mount`: Automatically mount repository (enabled by default)
- `--no-auto-mount`: Disable automatic repository mounting
- `--force-remount`: Force remount even if repository appears to be mounted
- `--debug`: Show additional debug information

## How it Works

The mounting process creates a `docker-compose.override.yml` file with volume mappings and then:

1. If containers are not running, it starts them with the mount configuration
2. If containers are already running, it recreates them with the new mount configuration
3. Verifies that the mount was successful by checking file access inside the containers

## Manual Mounting

You can also manually mount repositories by:

1. Setting the `REPOSITORY_PATH` environment variable:
```bash
export REPOSITORY_PATH=/path/to/your/repository
```

2. Starting or restarting the containers:
```bash
docker-compose down
docker-compose up -d
```

## Troubleshooting

If you encounter mounting issues:

1. Check if the repository path exists and is accessible
2. Ensure Docker has permission to access the directory
3. Run the ingest command with the `--debug` flag for detailed information:
```bash
codestory ingest start /path/to/your/repository --debug
```

4. Try forcing a remount:
```bash
codestory ingest start /path/to/your/repository --force-remount
```

5. Check the container logs for any errors:
```bash
docker logs codestory-service
docker logs codestory-worker
```

6. Verify mount status:
```bash
docker exec codestory-service ls -la /repositories
```

## Path Mapping

When repositories are mounted, they follow this path mapping convention:

- Local path: `/path/to/your/repository`
- Container path: `/repositories/repository-name`

For example, a repository at `/Users/name/projects/my-project` would be mounted at `/repositories/my-project` inside the containers.