code-story – Session Re‑Hydration Summary

This file condenses all essential context from the original ChatGPT session so a fresh model can pick up the project instantly.

⸻

1. Vision

Build a service (“code‑story”) that ingests a code repo, produces a Neo4j knowledge graph + LLM summaries, and exposes that knowledge via MCP, CLI, and GUI.

2. Component Overview

Tag	Component	Key Tech	Spec Path
P0	Scaffolding	Poetry, pnpm, Docker Compose	specs/01_scaffolding.md
P1	Graph Service	Neo4j 5, vector index	specs/P1_graph_service/
P2	OpenAI Client	Azure OpenAI wrapper	specs/P2_openai_client/
P3	Ingestion Pipeline	Celery, Blarify, pluggable steps	specs/P3_ingestion_pipeline/
P4	DAG & Summariser	NetworkX, LLM summaries	specs/P4_dag_summariser/
P5	MCP Adapter	FastAPI + gRPC, Entra ID	specs/P5_mcp_adapter/
P6	CLI	Rich + Click	specs/P6_cli/
P7	GUI	React + Redux, 3d-force-graph	specs/P7_gui/
P8	Infra	Docker‑Compose, Azure Bicep	specs/P8_infra/
P9	Docs & Prompts	MkDocs, prompt templates	specs/P9_docs_prompts/
CA	Coding‑Agent	Iterative gen/test loop	specs/coding-agent/
PMA	Program‑Manager Agent	Drives spec workflow	specs/program-manager-agent_spec.md

3. Methodology

Documented in specs/methodology.md
	1.	Rough sketch → Overall spec
	2.	Refinement loop (Q&A)
	3.	Component specs (one per major part)
	4.	Micro‑specs (≤8 K tokens each) under specs/Pn_component/ℹ️
	5.	Backlog & review (backlog.md, review.md)
	6.	Coding‑Agent loop: generate → static‑check (Ruff/mypy/ESLint) → tests → iterate.
	7.	Git PR automation when tests pass.

4. Coding Guidelines

Stored in specs/coding-guidelines.md — PEP 8 + mypy‑strict, ESLint + Prettier, docstrings, 90 % coverage.

5. Agents

Agent	Role	Key Specs
Coding‑Agent	Generates code per micro‑spec, runs tests, retries, commits branch, optional PR.	specs/coding-agent/*
Program‑Manager Agent (PMA)	Orchestrates methodology phases, maintains backlog, triggers coding‑agent.	specs/program-manager-agent_spec.md

6. Backlog Snapshot

Open improvements for coding‑agent recorded in specs/coding-agent-backlog.md (diff‑aware regeneration, patch output, cache, etc.).

7. Repo Reconstruction

Three batch scripts (batch-1.sh, batch-2.sh, batch-3.sh) recreate all spec files locally by echoing their content. After running them you’ll have the full code-story/specs/ tree ready for git.

⸻

Use this summary + the specs folder to re‑hydrate the project in any new ChatGPT session.