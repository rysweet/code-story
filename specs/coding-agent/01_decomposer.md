### CA-01 Micro-Spec Decomposer

**Purpose**
Read component folder, iterate micro-spec files, and generate per-task to fit context window.

**Files**

* `specs/coding-agent/decomposer.py`
* `tests/agent/test_decomposer.py`

**Acceptance**

* Given folder with two micro-specs, decomposer yields two generations and writes both outputs.

**One-Shot Code Generation Instructions**
Implement decomposer and unit test.
