## 06 CLI (P6)

Rich/Typer CLI with commands: `ingest`, `status`, `query`, `config edit`, `ui`. Uses Redis subscription for live progress, opens GUI.

### Key Steps

`poetry add typer rich rich-markdown rich-click`; build Typer app; entry‑point `codestory`.

### Acceptance

`cs in .` shows coloured progress; `cs q` returns Rich table.
