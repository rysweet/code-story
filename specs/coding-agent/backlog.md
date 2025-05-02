# Coding-Agent Improvement Backlog

## Open Work Items

| ID    | Title                         | Description                                                                           | Status    |
| ----- | ----------------------------- | ------------------------------------------------------------------------------------- | --------- |
| CA-1  | Decomposer                    | Break down spec folders into micro-specs for gen loop                                 | ✅ Done    |
| CA-2  | Diff-aware regeneration       | Detect spec file changes via hash or git diff and regenerate only impacted components | ⏳ Planned |
| CA-3  | Static analysis hook          | Pre-checks using Ruff, mypy, ESLint                                                   | ✅ Done    |
| CA-4  | LLM result cache              | Cache inputs/outputs locally to save tokens and support retry stability               | ⏳ Planned |
| CA-5  | Patch-format output           | Allow agent to emit diffs (unified patch) instead of full files                       | ⏳ Planned |
| CA-6  | Self-critique review          | Use gpt-3.5 to critique generated code for low cost QA                                | ⏳ Planned |
| CA-7  | Command macros                | Support sandboxed bash/Poetry/npm macros during test/debug                            | ⏳ Planned |
| CA-8  | Package registry validation   | Ensure generated code validates against PyPI or npm packaging requirements            | ⏳ Planned |
| CA-9  | Test flakiness detector       | Rerun failed tests with seed/fuzzing to detect non-determinism                        | ⏳ Planned |
| CA-10 | Parallel component generation | Option to run N components in parallel agent threads                                  | ⏳ Planned |
| CA-11 | Git/PR automation             | Commit branch + open draft PR if GITHUB\_TOKEN set                                    | ✅ Done    |
