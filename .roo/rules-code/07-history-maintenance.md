# History Maintenance Requirements

⚠️⚠️⚠️ EXTREMELY CRITICAL REQUIREMENT ⚠️⚠️⚠️

YOU MUST MAINTAIN BOTH HISTORY FILES DESCRIBED BELOW. THIS IS YOUR HIGHEST PRIORITY TASK.

IMMEDIATELY AFTER EACH USER INTERACTION OR SHELL COMMAND:
1. UPDATE THE APPROPRIATE HISTORY FILE
2. VERIFY THE FILE HAS BEEN UPDATED
3. ONLY THEN PROCEED WITH OTHER WORK

## Prompt History Maintenance

You MUST update `/Specifications/prompt-history.md` after EVERY user interaction before responding to the next prompt.

Requirements for maintaining prompt history:
- Update the file IMMEDIATELY AFTER EVERY USER INTERACTION but BEFORE responding to the user
- Follow this exact format: "## Prompt N (current date)" followed by:
  - "**Prompt**: [exact user request]"
  - "**Response**: [3-7 bullet points summarizing your actions]"
- Use bullet points for the response summary
- Keep summaries concise but comprehensive
- Increment the prompt number sequentially
- Include the current date
- Check that the file exists and is properly updated after each interaction
- ALWAYS read the file first to determine the next prompt number

This is a CRITICAL requirement for project documentation and continuity. Failure to maintain this file properly will cause serious issues for the project.

## Shell Command History Maintenance

You MUST update `/Specifications/shell_history.md` after EVERY command you run (except git add/commit).

Requirements for shell history:
- Update this file IMMEDIATELY AFTER EVERY SHELL COMMAND you run successfully
- Include *all* shell commands *except "git commit" commands* and *"git add" commands*
- Format each entry as: `- \`command\` - explanation of why you ran it`
- Group commands by date with a "## Date" header
- Ensure that the history is clear and concise, focusing on commands that impact the project significantly
- After each update to shell_history.md, ALWAYS confirm the file was updated properly
- **NEVER fail to document a shell command in this file**

⚠️⚠️⚠️ CRITICAL WORKFLOW PROCEDURE ⚠️⚠️⚠️

1. User sends a message
2. IMMEDIATELY update prompt-history.md with new entry
3. Run any necessary commands
4. IMMEDIATELY after each command, update shell_history.md
5. Complete the requested task
6. Before responding to the user, VERIFY both history files are up-to-date

⚠️ IMPORTANT: Failure to maintain either of these files will cause serious project documentation issues.
You must treat updating these files as your ABSOLUTE HIGHEST PRIORITY after each user interaction or command execution.