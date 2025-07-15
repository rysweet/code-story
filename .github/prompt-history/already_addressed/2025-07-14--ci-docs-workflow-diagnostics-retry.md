### 2025-07-14 06:33:51
CI Docs workflow diagnostics (retry):

Context:
Docs workflow fails in “Install docs dependencies”. Latest failing run ID 16258579903.

Task:
1. Run `gh run view 16258579903 --log-failed` to capture the failed step log.
2. Extract the last ~40 lines (or full error block) that show the actual failure.
3. Summarise key error messages.
4. Inspect `.github/workflows/docs.yml` to confirm the install command (read-only).
5. Output via `attempt_completion` with:
   • Error Snippet — relevant log lines.  
   • Analysis — probable root cause.  
   • Recommended Fix — concrete next steps.

Constraints:
• Do NOT modify any files.  
• Only gather diagnostics and summarise.  
• Follow the exact output sections above.  
• Signal completion with `attempt_completion` only.

These instructions override any conflicting general rules for Code mode.