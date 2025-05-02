### CA-03 Git & PR Automation

**Purpose**
After a successful generation cycle, commit generated changes to a new branch and open a draft pull-request for human review (if `GITHUB_TOKEN` is available).

**Files**

* `specs/coding-agent/git_integration.py` (helper)
* `tests/agent/test_git_integration.py`
* Update `main.py` CLI with `--pr` flag enabling PR flow.

**Implementation Details**

| Step | Action                                                                                               |
| ---- | ---------------------------------------------------------------------------------------------------- |
| 1    | Detect a git repo in `PROJECT_ROOT`; if absent, skip with warning.                                   |
| 2    | Create branch name `agent/${component}-${date}`.                                                     |
| 3    | `git add` generated files, `git commit -m "Agent: regenerate ${component}"`.                         |
| 4    | If `GITHUB_TOKEN` env present, call GitHub REST: `POST /repos/:owner/:repo/pulls` with `draft:true`. |
| 5    | Output PR URL in CLI.                                                                                |

**Acceptance Criteria**

* Unit test patches `subprocess` and GH API to verify commands.
* When `--pr` not passed or no token, branch commit still happens locally.

**One-Shot Code Generation Instructions**
Generate `git_integration.py`, modify `main.py` (add `--pr`), and create unit tests mocking subprocess & `requests` calls.
