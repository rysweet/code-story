## 05 MCP Adapter (P5)

### 1 Purpose

Serve graph data via **Model Context Protocol**, secured by Entra ID.

### 2 Responsibilities

MCP‑R1 implement MCP gRPC/HTTP · MCP‑R2 JWT auth · MCP‑R3 map tools to Cypher/Vector · MCP‑R4 Prometheus metrics.

### 3 Implementation Steps

1. `poetry add fastapi uvicorn[standard] grpcio grpcio-tools msal jose prometheus-client`
2. Compile MCP protos, implement auth, tool handlers, FastAPI+gRPC dual server.
3. Compose service `mcp` ports 9000/8080.

### 4 Testing & Acceptance

* Auth validation, tool returns, metrics counter present, P99 < 200 ms.
