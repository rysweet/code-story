# GitHub Workflow Guidelines

## Repository Management

- The GitHub repository is https://github.com/rysweet/code-story
- Use the `gh` CLI to manage the repo, PRs, and issues
- Use the `gh` and `git` CLI for all GitHub interactions

## Branch Strategy

- Each stage of the project should progress on a separate branch of the repo
- Upon completion, merge as a PR to the main branch
- Each PR should be reviewed and approved before merging

## Workflow Requirements

- Think carefully about the user's request
- If there is an error message, think carefully about the meaning of the error
- Do not change direction to skip tests or disable features in order to avoid an error
- Think step by step about how to solve the problem
- Once you have crafted a solution, always:
  1. Run all checks using the project's CI tools (e.g., `poe check`)
  2. Run all tests using the project's test tools (e.g., `poe test`)
  3. Iterate over any errors generated, solving them one at a time
  4. Once all checks and tests pass, then you can commit your work
  5. Check if CI is passing and if not try to resolve any errors in CI

## Implementation Notes

- You should not be using the autogen package, use autogen-core
- Do not use autogen-agentchat, only autogen-core
- Any modules that are using pyautogen should be corrected/rewritten to use autogen-core
- For the implementation, you will need to use Azure credentials to access the Azure OpenAI API using Tenant: 3cd87a41-1f61-4aef-a212-cefdecd9a2d1
- You will need to do a commit after each step of the implementation
- If a step of the implementation is not clear, please ask for clarification
- If a step of the implementation fails, try again by attempting to correct the error
- If you are unable to correct the error, update the status.md and ask for help