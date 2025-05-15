# Repository Mounting Guide

For Code Story to analyze a codebase, the repository must be accessible to both the service and worker containers.

## Using Volume Mounts

In Docker environments, this is achieved using volume mounts. The exact approach depends on how you're deploying Code Story.

## The `mount_repository.sh` Script

For convenience, Code Story provides a script to help with repository mounting:

```bash
# Make the script executable if needed
chmod +x scripts/mount_repository.sh

# Run the script with the path to your repository
./scripts/mount_repository.sh /path/to/your/repository
```

This script:
1. Sets up the `REPOSITORY_PATH` environment variable for docker-compose
2. Verifies the repository path exists
3. Provides the path to use when invoking the CLI for ingestion

## Manual Setup

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
docker run -v /absolute/path/to/repository:/repositories my-service-image

# For the worker container
docker run -v /absolute/path/to/repository:/repositories my-worker-image
```

## Path Reference

When using the CLI to ingest a repository, refer to its mounted path:

```bash
# If repository was mounted at /repositories
codestory ingest start /repositories/your-repo-name
```

## Production Environments

For production environments, consider:

1. **Shared Storage**: Use solutions like Azure Files, EFS, or NFS for persistence
2. **Mount Path Consistency**: Use the same mount paths across all containers
3. **Permissions**: Ensure the containers have read/write access to the mounted repositories
4. **Volume Management**: Consider using named volumes for better lifecycle management

## Common Issues

1. **Path Mismatch**: If the CLI reports a path doesn't exist, ensure:
   - The repository is mounted in both service and worker containers
   - You're using the correct path inside the container (e.g., `/repositories/...`)
   - Mount points are consistent between containers

2. **Permission Issues**: If you encounter permission errors:
   - Check that container processes have read/write access to the mounted directory
   - Verify ownership and permissions on the host directory

3. **Container Networking**: If containers can't communicate:
   - Ensure they're on the same Docker network
   - Check that container names match hostname references in your configuration