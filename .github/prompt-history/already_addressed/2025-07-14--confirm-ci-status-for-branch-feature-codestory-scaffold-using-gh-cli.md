2025-07-14 06:24:14 - User:  
Context:
• Need to confirm CI status for branch `feature/codestory-scaffold` using `gh` CLI.  
• User requested we always use the `gh` command for GitHub Actions checks.

Task:
1. Execute:
   ```
   gh run list -L 1 -b feature/codestory-scaffold
   ```
   to get the latest workflow run ID and status.  
2. If not obvious, run:
   ```
   gh run view <run-id> --json conclusion,name,status,workflowName
   ```
   to confirm all jobs succeeded.
3. Parse output; if status is not `success`, capture job failures.
4. Report results back via attempt_completion:
   • Latest run ID, workflow name, conclusion.  
   • Any failing jobs (if applicable).  
   • If jobs failed, list next steps to fix; otherwise confirm CI green.

No repo file changes, just command execution and reporting.