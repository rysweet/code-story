## 08 Infra Module (P8)

### Deliverables

* `docker-compose.yaml` with neo4j, redis, worker, mcp, gui.
* `Dockerfile` for Python services; `Dockerfile.gui`.
* `bicep/aca.bicep` for Azure Container Apps.
* `devcontainer.json`.

### Acceptance

`docker compose up -d` brings stack healthy; Bicep deploy succeeds.
