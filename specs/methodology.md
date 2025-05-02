# Iterative Spec-First Development Method
*(playbook + detailed deliverables matrix + prompt snippets)*

3. Component specs (one per major part)
   1. Create micro-spec for P0 Scaffolding under `specs/01_scaffolding.md`.
   2. Implement scaffolding: layout, toolchain configs.
   3. **Validate scaffolding:** immediately run `ruff check .`, `mypy .`, and `pytest` to ensure lint, type, and test coverage are clean before moving on.
   4. For each subsequent component (P1, P2, …):
      - Implement according to its micro-spec.
      - **Validate component:** run `ruff check .`, `mypy .`, and `pytest` (or component-specific tests) to ensure all quality gates pass before proceeding.
      - **Open a pull request:** create a PR against `main`, with description of changes.
      - **Conduct code review:** review PR against specs, coding guidelines, and test coverage; address any feedback and ensure CI passes.
      - **Merge PR:** merge into `main` only after code review approval and passing all checks.

5. Micro‑specs (≤8 K tokens each) under specs/Pn_component/ℹ️
