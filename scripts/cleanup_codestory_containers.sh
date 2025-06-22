#!/bin/bash
# Remove all codestory containers in any state (Created, Exited, Running)
docker rm -f $(docker ps -a --filter "name=codestory-neo4j" --filter "name=codestory-redis" --filter "name=codestory-service" --filter "name=codestory-worker" -q) 2>/dev/null || true