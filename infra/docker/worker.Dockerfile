# Use the service Dockerfile with the worker target
FROM service:worker

# Note: This Dockerfile exists for backward compatibility.
# For new deployments, use:
# docker build -f infra/docker/service.Dockerfile --target worker .