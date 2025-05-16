# Repository Mounting Guide

For Code Story to analyze a codebase, the repository must be accessible to both the service and worker containers. This guide explains how to mount your repositories correctly.

## Automatic Repository Mounting (Recommended)

The easiest way to mount a repository is to use the provided script:

```bash
# Make the script executable if needed
chmod +x scripts/mount_repository.sh

# Mount repository and setup environment variables
./scripts/mount_repository.sh /path/to/your/repository

# Or mount and restart containers in one step
./scripts/mount_repository.sh /path/to/your/repository --restart
```

This script performs several important tasks:
1. Sets up the `REPOSITORY_PATH` environment variable for docker-compose
2. Creates a repository configuration file for the CLI
3. Verifies the repository path exists
4. Optionally restarts containers with the new mount
5. Provides the exact CLI command to use for ingestion

## Using the CLI with Docker Deployments

When your service is running in Docker, use one of these approaches for ingestion:

### Approach 1: Automatic Container Path Detection (Recommended)

```bash
# The CLI automatically detects Docker deployment and maps paths
codestory ingest start /path/to/your/repository
```

The CLI will:
1. Detect that you're connecting to a containerized service
2. Convert your local path to the correct container path
3. Show you both paths for verification

### Approach 2: Explicit Container Flag

```bash
# Explicitly tell the CLI to use container path mapping
codestory ingest start /path/to/your/repository --container
```

### Approach 3: Direct Container Path

```bash
# Use the container path directly
codestory ingest start /repositories/your-repo-name
```

## Manual Setup Options

If you prefer manual setup, follow these steps:

### For `docker-compose`

1. Set the `REPOSITORY_PATH` environment variable:
   ```bash
   export REPOSITORY_PATH=/absolute/path/to/repository
   ```

2. Start the containers:
   ```bash
   docker-compose up -d
   ```

3. Or combine both commands:
   ```bash
   REPOSITORY_PATH=/absolute/path/to/repository docker-compose up -d
   ```

### For Individual Docker Containers

```bash
# For the service container
docker run -v /absolute/path/to/repository:/repositories/repo-name my-service-image

# For the worker container - must use the same mount path
docker run -v /absolute/path/to/repository:/repositories/repo-name my-worker-image
```

## How Repository Mounting Works

1. **Volume Mounts**: Docker maps directories from your host system into containers
2. **Standard Path Mapping**: 
   - Host path: `/path/to/your/repository`
   - Container path: `/repositories/repo-name`
3. **Path Translation**: The CLI handles mapping between these different paths
4. **Environment Variables**: `REPOSITORY_PATH` tells docker-compose what to mount

## Production Environments

For production environments, consider:

1. **Shared Storage**: Use solutions like Azure Files, EFS, or NFS for persistence
2. **Mount Path Consistency**: Use the same mount paths across all containers
3. **Permissions**: Ensure the containers have read/write access to the mounted repositories
4. **Volume Management**: Consider using named volumes for better lifecycle management

## Troubleshooting

### "Repository does not exist" Errors

If you see errors about the repository path not existing:

1. **Verify Docker mounting**
   ```bash
   # Check if your repository is properly mounted
   docker exec codestory-service ls -la /repositories
   ```

2. **Check container logs**
   ```bash
   docker logs codestory-service
   docker logs codestory-worker
   ```

3. **Restart with proper mounting**
   ```bash
   # Use the helper script
   ./scripts/mount_repository.sh /path/to/your/repository --restart
   ```

4. **Try explicit container mode**
   ```bash
   codestory ingest start /path/to/your/repository --container
   ```

### Permission Issues

If you encounter permission errors:

1. **Check file permissions on the host**
   ```bash
   ls -la /path/to/your/repository
   ```

2. **Check permissions inside container**
   ```bash
   docker exec codestory-service ls -la /repositories
   ```

3. **Fix permissions if needed**
   ```bash
   # On host
   sudo chmod -R a+r /path/to/your/repository
   ```

## Best Practices

1. **Use absolute paths** when mounting repositories
2. **Keep repository name in path structure** for easier identification
3. **Use the mounting script** to ensure proper configuration
4. **Use the `--container` flag** with the CLI for Docker deployments
5. **Create one mount per repository** rather than mounting parent directories