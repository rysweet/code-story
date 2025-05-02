### CA-02 Static Analysis Pre-check

**Purpose**
Run Ruff, Black check, mypy, ESLint, Prettier before executing tests; count any error as failure.

**Files**

* `specs/coding-agent/static_check.py`
* `tests/agent/test_static_check.py`

**Acceptance**

* Returns non-zero when Ruff finds error.
* Integrated into `iterative_generate` before pytest.

**One-Shot Code Generation Instructions**
Implement static\_check helper and tests, modify loop.
