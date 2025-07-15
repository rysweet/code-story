2025-07-13 22:10:02 - User Prompt:
High-priority compliance sweep — finish all remaining TODOs and eliminate skips/failures.

Context
• Branch: feature/codestory-scaffold  
• Pending items 21-24:  
  21. Remove any lingering Black references (we removed hook; confirm pyproject clean).  
  22. Un-skip tests now implementable: Settings attrs, AIClient `chat`/`embed`, GraphService context manager/handshake.  
  23. Provide an E2E demo doc that ingests the codebase and shows MCP queries.  
  24. Add integration test exercising MCPAdapter end-to-end with a dummy GraphService.

Tasks (implement all):

A. codestory/config/__init__.py  
   • Add properties `neo4j_uri`, `neo4j_user`, `neo4j_password` to Settings (read from env, default placeholders).  
   • Update tests to assert these now present; remove `pytest.skip`.

B. codestory/ai/__init__.py  
   • Implement async stub methods:
     ```python
     async def chat(self, prompt: str) -> str: return f"Echo: {prompt}"
     async def embed(self, text: str) -> list[float]: return [0.0]
     ```
   • Remove skip marker in tests/ai/test_ai_client.py.

C. codestory/graph/__init__.py  
   • Implement async context manager (`__aenter__`, `__aexit__`) returning self.  
   • Implement `_handshake` that raises RuntimeError if missing env var `NEO4J_PASSWORD`; call from constructor so handshake tests cover both pass/skip paths.  
   • Remove skips in tests/graph/test_graph_service.py.

D. Remove any Black config remnants from pyproject.toml (verify).

E. docs/demo/e2e_demo.md  
   • Step-by-step: install, ingest repo via CLI, sample `mcp searchGraph` query, summarize node. Include code blocks.

F. Integration test `tests/integration/test_mcp_e2e.py`  
   • Create DummyGraphService with in-memory dict; monkeypatch MCPAdapter.graph_service to dummy; call `searchGraph`, `summarizeNode`, etc.; assert returns expected stubs.

G. Ensure editable install in tests: add to `tests/__init__.py`  
   ```python
   import sys, pathlib, os
   sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
   ```

H. Run:
   ```
   uv run ruff format .
   uv run pre-commit run --all-files
   uv run pytest -q
   uv run mkdocs build --strict
   ```
   No failures / unexpected skips.

I. Commit & push:
   `feat(e2e): final feature completeness, all tests green`

Return via attempt_completion:
• Files modified/created  
• Test/CI results summary (0 failed, 0 skipped except neo4j secret skip)  
• Confirm no remaining TODOs or skips.

These instructions override defaults; implement exactly as above.