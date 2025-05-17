# Service Recovery Guide

This document explains how to recover from service issues using the Code Story CLI.

## Overview

The Code Story service consists of multiple containers (service, worker, neo4j, redis) that work together. Sometimes these containers can become unhealthy due to various issues such as resource constraints, networking problems, or application errors.

The CLI provides a `service recover` command to help diagnose and fix these issues.

## Using the Service Recovery Command

### Basic Usage

To check the status of your service and diagnose potential issues:

```bash
codestory service status
```

If the status shows unhealthy containers or the service is not responding, you can use the recovery command:

```bash
codestory service recover
```

This command will:
1. Identify any unhealthy containers
2. Show the logs for these containers
3. Attempt to restart the unhealthy containers
4. Verify the health status after restart

### Advanced Recovery Options

#### Worker-Only Recovery

If only the worker container is unhealthy, you can restart just that component:

```bash
codestory service recover --restart-worker
```

This is faster than restarting all containers and can resolve many common issues.

#### Force Recovery

For more serious issues, you can force a complete recovery:

```bash
codestory service recover --force
```

This option:
1. Stops all containers
2. Removes orphaned containers
3. Restarts the entire stack with health checks temporarily disabled
4. Works best when containers are stuck in an unhealthy state

## Common Issues and Solutions

### Worker Health Check Failures

**Symptom**: The worker container is marked as unhealthy in `service status`

**Possible causes**:
- Celery worker failed to start properly
- Redis connection issues
- Python environment problems

**Solution**:
```bash
codestory service recover --restart-worker
```

### Service Not Responding

**Symptom**: The service API is not reachable but containers appear to be running

**Possible causes**:
- Application error in the service container
- Network configuration issues
- Resource constraints

**Solution**:
1. Check the logs: `docker logs codestory-service`
2. Try restarting just the service: `docker restart codestory-service`
3. If that fails: `codestory service recover --force`

### Database Connection Issues

**Symptom**: Service reports Neo4j as unhealthy

**Possible causes**:
- Neo4j failed to start properly
- Authentication issues
- Database corruption

**Solution**:
1. Check Neo4j logs: `docker logs codestory-neo4j`
2. Try restarting Neo4j: `docker restart codestory-neo4j`
3. If that fails: `codestory service recover --force`

## Preventative Measures

To minimize service disruptions:

1. Ensure your system has adequate resources (CPU, memory, disk space)
2. Monitor service health periodically with `codestory service status`
3. Follow the proper shutdown procedure with `codestory service stop`
4. Keep your Code Story installation updated

## Advanced Troubleshooting

If the recovery commands don't resolve the issue:

1. Check container logs directly:
   ```bash
   docker logs codestory-service
   docker logs codestory-worker
   docker logs codestory-neo4j
   docker logs codestory-redis
   ```

2. Verify network connectivity between containers:
   ```bash
   docker exec codestory-service ping neo4j
   docker exec codestory-service ping redis
   ```

3. Check configuration:
   ```bash
   docker exec codestory-service cat /app/.codestory.toml
   ```

4. For persistent issues, try a clean slate:
   ```bash
   codestory service stop
   docker volume rm codestory_neo4j_data codestory_redis_data
   codestory service start
   ```
   Note: This will delete all data in the database!