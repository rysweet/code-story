<SYSTEM>
You are an AI programming assistant that is specialized in applying code changes to an existing document.
Follow Microsoft content policies.
Avoid content that violates copyrights.
If you are asked to generate content that is harmful, hateful, racist, sexist, lewd, violent, or completely irrelevant to software engineering, only respond with "Sorry, I can't assist with that."
Keep your answers short and impersonal.
The user has a code block that represents a suggestion for a code change and a instructions file opened in a code editor.
Rewrite the existing document to fully incorporate the code changes in the provided code block.
For the response, always follow these instructions:
1. Analyse the code block and the existing document to decide if the code block should replace existing code or should be inserted.
2. If necessary, break up the code block in multiple parts and insert each part at the appropriate location.
3. Preserve whitespace and newlines right after the parts of the file that you modify.
4. The final result must be syntactically valid, properly formatted, and correctly indented. It should not contain any ...existing code... comments.
5. Finally, provide the fully rewritten file. You must output the complete file.
</SYSTEM>

```instructions
Please consider the following instructions when implementing the software.

We may be working with a large codebase that was mostly developed with AI. The codebase may contain a number of errors and anti-patterns. Please prioritize the instructions in this document over the codebase. 
Keep the plan status up to date by updating a file called /Specifications/status.md. You can check this file to find out the most recent status of the plan.

## Code Design Guidelines

Please follow these guidelines for code design and implementation:

### Modularity

- Maintain clear separation between different concerns (e.g., knowledge ingestion, code ingestion, analysis)
- Create dedicated modules for distinct functionality
- Use composition over inheritance where appropriate
- Design for extensibility with interfaces and dependency injection
- Follow the module structure established in the codebase (shared, code_analysis, etc.)

### Code Reuse

- Extract shared code into dedicated utility modules
- Avoid duplicating functionality across different modules
- Prefer composition and delegation over inheritance for code reuse
- Create reusable abstractions for common patterns
- Utilize the shared module for cross-cutting concerns

### Design Patterns

- Use the Strategy pattern for varying behaviors 
- Apply the Factory pattern for object creation where appropriate
- Implement interfaces (abstract base classes) for polymorphic behavior
- Use composition to combine behaviors flexibly
- Follow established patterns in the codebase for consistency

### Function/Method Design

- Keep functions and methods short (generally under 50 lines)
- Each function should have a single responsibility
- Extract complex logic into smaller, well-named helper functions
- Limit function parameters (generally 5 or fewer)
- Use descriptive naming that indicates purpose

### Error Handling

- Handle errors explicitly at appropriate levels
- Use specific exception types rather than generic exceptions
- Document expected exceptions in function docstrings
- Log errors with appropriate context before re-raising

### Testing

- Write tests for each component
- Write unit tests for individual functions and methods
- When creating shared resources or code for unit tests
- When unit test failures occur, we do not move on, instead we stop, think carefully about the code being tested, consider carefully the necessary setup conditions, and then carefully construct the test to ensure it is validating the functionality of the code. Then we either fix the code being tested or fix the test.
- Write integration tests for module interactions
- Ensure public interfaces are well-tested
- Use dependency injection to make components testable
- Maintain test coverage during refactoring
- Integration tests should not use mocks for the components they are testing
- Do not mark tests as skipped or expected to fail
- Do not disable tests or cause tests to exit true when they would not otherwise succeed

### Code Organization

- Group related functionality in dedicated modules and packages
- Use a consistent file structure within modules
- Place interfaces in base.py files at the package root
- Use __init__.py files to expose public APIs
- Follow established naming conventions for files and directories
- Use clear and consistent naming for modules and packages
- Organize tests in a parallel structure to the codebase
- Use descriptive names for test files and classes

## Resources

You should also use the following resources to help you implement the software - If you think that a resource may be useful during a phase of the Implementation (eg Autogen Core Documentation when woring with Agents) please ensure that you add that document to the context during that phase. 

 - [Blarify website](https://github.com/blarApp/blarify)
 - [AutoGen Core Documentation Online](https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/index.html)
 - [AutoGen API Documentation](https://microsoft.github.io/autogen/stable/api/index.html)
 - [AutoGen Examples](https://microsoft.github.io/autogen/stable/examples/index.html)
 - [Neo4J Documentation](https://neo4j.com/docs/)
 - [Rich CLI Documentation](https://rich.readthedocs.io/en/stable/)
 - [Neo4J Blog on Semantic indexes](https://neo4j.com/blog/developer/knowledge-graph-structured-semantic-search/)

## Implementation Notes

You should not be using the autogen package, use autogen-core. 
Do not use autogen-agentchat, only autogen-core. 
Any modules that are using pyautogen should be corrected/rewritten to use autogen-core. 
For the implementation, you will need to use my az credentials to access the Azure OpenAI API using Tenant: Microsoft
Subscription: adapt-appsci1 (be51a72b-4d76-4627-9a17-7dd26245da7b). You will need to use my Github credentials using the gh cli. You will need to do a commit after each step of the implementation. If a step of the implementation is not clear, please ask me for clarification.
Do not move on to the next milestone until the current milestone is complete with all tests for all milestones passing.
Do not move on to the next milestone while there are test failures anywhere in the project. 
When there are test failures, think carefully about the intent of the code being tested, think carefully about the conditions required to test, setup the test conditions, and then think carefully about how to either fix the test or fix the code being tested.
If a step of the implementation fails, try again by attempting to correct the error. If you are unable to correct the error, update the status.md and please ask me for help.

# Prompt History - MANDATORY REQUIREMENT

IMPORTANT: You MUST maintain a running history of all user prompts with brief summaries of your responses in the file `/Specifications/prompt-history.md`.

Requirements for maintaining prompt history:
- Update the file AFTER EVERY USER INTERACTION before responding to the next prompt
- Follow the format: "## Prompt N (current date)" followed by:
  - "**Prompt**: [exact user request]" 
  - "**Response**: [3-7 bullet points summarizing your actions]"
- Use bullet points for the response summary
- Keep summaries concise but comprehensive
- Increment the prompt number sequentially
- Include the current date

This is a critical requirement for project documentation and continuity. Failure to maintain this file correctly will impact project tracking.

# Shell Command history

Maintain a running history of all shell commands you run successfully, *except "git commit" commands* and *"git add" commands*, along with a comment explaining why you ran it, in a file called /Specifications/shell_history.md. This file should be updated after each command.
- Ensure that the history is clear and concise, focusing on commands that impact the project significantly.
- **After updating shell_history.md, always stage and commit it with a descriptive message.**, otherwise you will end up trying to push a PR and there will be uncommitted changes on the shell history.