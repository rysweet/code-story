## 02 OpenAI Client (P2)

### 1 Purpose

Provide low‑level async/sync access to Azure OpenAI completions, embeddings, and chat—with retry, throttling back‑off, and metrics. Domain summarisation logic lives elsewhere (P4).

### 2 Responsibilities

\| OC‑R1 | Bearer‑token auth via `AZURE_OAI_KEY`, `AZURE_OAI_ENDPOINT`. |
\| OC‑R2 | Support o1/o3 reasoning, gpt‑4o chat, `text‑embedding‑3-small`. |
\| OC‑R3 | Retry on 429 with exponential back‑off (tenacity). |
\| OC‑R4 | Public methods: `complete`, `embed`, `chat`. |
\| OC‑R5 | Prometheus metrics & OTEL traces.

### 3 Architecture

```
src/codestory/openai/
├── __init__.py
├── client.py
├── models.py
├── prompts/
└── backoff.py
```

### 4 Implementation Steps

1. `poetry add openai azure-core prompty tenacity prometheus-client`
2. Implement `backoff.retry_on_429`.
3. Build `OpenAIClient` loading defaults from `settings`.
4. Wire metrics & optional `/metrics` router.

### 5 Testing & Acceptance

* Unit mock for retry; branch coverage ≥ 95 %.
* Integration with mock server; histogram increments.
