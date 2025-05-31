# MyPy Error Remediation Roadmap (as of latest check)

## Executive Summary

- **Total errors:** 1124
- **Files affected:** 141
- **Primary error types:**  
  - `[import-untyped]` (missing stubs/py.typed marker for internal modules)
  - `[no-untyped-def]` (missing function/return type annotations)
  - `[attr-defined]`, `[var-annotated]`, `[call-arg]`, `[arg-type]`, `[assignment]`, `[unreachable]`

## Phased Remediation Plan

### Phase 1: Core Production Code (`src/`)
**Goal:** Eliminate `[import-untyped]` and `[no-untyped-def]` in core modules.

- **Batch 1:**  
  - Add `py.typed` marker files to all internal packages in `src/` and `src/codestory_*`  
  - Add minimal stubs if needed for cross-module imports.
  - PR scope: Only marker files and stub scaffolding.

- **Batch 2-4:**  
  - Add function and return type annotations to high-traffic modules (e.g. `src/codestory_service`, `src/codestory_mcp`, `src/codestory/ingestion_pipeline`)
  - Target ≤200 errors per PR, focus on `[no-untyped-def]` and `[var-annotated]`
  - Enable `strict = True` in `mypy.ini` for one module per PR after cleanup.

- **Batch 5:**  
  - Address `[attr-defined]` and `[call-arg]` in core modules.
  - Add missing attribute/argument annotations and fix class attribute issues.

### Phase 2: Secondary Production Code & Scripts
- **Batch 6-7:**  
  - Clean up remaining `src/` modules and all scripts in root and `scripts/`
  - Focus on `[no-untyped-def]`, `[import-untyped]`, `[var-annotated]`
  - Enable `warn-unused-ignores = True` for these modules.

### Phase 3: Test Code (`tests/`)
- **Batch 8-12:**  
  - Add type annotations to test files, starting with integration tests, then unit tests.
  - Fix `[import-untyped]` for test imports from internal modules.
  - Use helper scripts to autofix trivial annotation issues.

### Phase 4: Miscellaneous & Final Sweep
- **Batch 13+:**  
  - Address remaining `[assignment]`, `[unreachable]`, `[arg-type]`, and rare errors.
  - Finalize `mypy.ini` with `strict = True` for all production modules.
  - Enable `warn-unused-ignores` globally.

## mypy.ini Refinements (to be introduced gradually)
- Add `py.typed` to all internal packages.
- For each cleaned module, set:
  ```
  [mypy-src.codestory_service.*]
  strict = True
  ```
- After batch 7, add:
  ```
  warn-unused-ignores = True
  ```
- After all production code is clean, enable `strict = True` globally for `src/`.

## Helper Tools & Plugins
- Use `ruff` for autofixing simple annotation and import issues.
- Use `add-trailing-annotations` or similar scripts to add `-> None` where missing.
- Consider `mypy-extensions` for advanced typing needs.
- Use `pytest-mypy-plugins` for test-specific type checks.

## Batch Summary & Ordering

| Batch | Scope | Targeted Error Types | Est. Errors |
|-------|-------|---------------------|-------------|
| 1     | py.typed markers, stubs | import-untyped | 100+ |
| 2-4   | src/ core modules | no-untyped-def, var-annotated | 200 each |
| 5     | src/ core modules | attr-defined, call-arg | 100+ |
| 6-7   | scripts, secondary src/ | no-untyped-def, import-untyped | 200 each |
| 8-12  | tests/ | no-untyped-def, import-untyped | 100-200 each |
| 13+   | all | assignment, unreachable, arg-type | remainder |

- **Total batches:** ~13-15
- **Order:** Production code and scripts first, then tests, then final sweep.

## Key Config Changes Planned
- Add `py.typed` markers to all internal packages.
- Gradually enable `strict = True` and `warn-unused-ignores` in `mypy.ini`.

## Confirmation
This plan is based on the latest `mypy` output and is written to guide incremental, reviewable PRs. [`TEST_ANALYSIS_AND_FIX_PLAN.md`](TEST_ANALYSIS_AND_FIX_PLAN.md) has been updated accordingly.