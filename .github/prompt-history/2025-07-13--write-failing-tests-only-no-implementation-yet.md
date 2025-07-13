# Prompt History: 2025-07-13--write-failing-tests-only-no-implementation-yet

## 2025-07-13 15:43 PT

<task>
Context:
• Current branch: `feature/codestory-scaffold`  
• `codestory/cli/` package is empty.  
• Todo #6 “Write failing tests and implement CLI interface” is now in-progress.

Subtask 6a – **Write failing tests only** (no implementation yet):

1. Create `tests/cli/test_cli.py` that defines the initial contract:
   a. `import codestory.cli.app` should raise `ImportError` until implemented.  
   b. If import succeeds later, expect:  
      ‑ `app` is a `typer.Typer` instance  
      ‑ Running `codestory.cli.main` (entrypoint) should call `app()`; use `pytest.raises(SystemExit)` with code 0 stub.  
   (Mark interface checks with `pytest.skip` so only ImportError causes failure today.)

2. Ensure tests are self-contained (no external runtime). Use `pytest.importorskip` pattern.

3. Update/append `tests/__init__.py` with a comment referencing CLI contracts (no logic).

4. Stage, commit, push on the same branch with message:  
   `test(cli): add initial failing tests for CLI skeleton`

5. Do NOT implement CLI yet—just failing tests to drive TDD.

Output via `attempt_completion` after commit & push:  
• Confirm failing tests pushed (CI red expected).  
• List created/modified files.  
• Note that implementation will follow in next step.

These instructions supersede any conflicting general Code-mode rules. Perform only the actions listed.
</task>