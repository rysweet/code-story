### CA-00 Core Generation Loop

**Purpose**
Implement `iterative_generate` loop (in `test_loop.py`) that:

1. Builds prompt from spec/micro-spec.
2. Calls LLM.
3. Writes files.
4. Runs static analysis + tests.
5. Feeds failures back up to `MAX_ITER`.

**Acceptance**

* Loop exits success when tests pass; raises after max iterations.

**One-Shot Code Generation Instructions**
Implement `test_loop.py`, integrate with `llm_client`, `prompt_builder`, `file_writer`.
