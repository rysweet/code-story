# Testing Requirements

## Test Development Standards

- Write tests for each component
- Write unit tests for individual functions and methods
- When creating shared resources or code for unit tests ensure those resources can be safely accessed in parallel
- When unit test failures occur, we do not move on, instead we stop, think carefully about the code being tested, consider carefully the necessary setup conditions, and then carefully construct the test to ensure it is validating the functionality of the code. Then we either fix the code being tested or fix the test
- Write integration tests for module interactions
- Ensure public interfaces are well-tested
- Use dependency injection to make components testable
- Maintain test coverage during refactoring
- Integration tests should not use mocks for the components they are testing
- Do not mark tests as skipped or expected to fail
- Do not disable tests or cause tests to exit true when they would not otherwise succeed
- Always ensure that all tests and CI pass before moving on to the next milestone

## Test Organization

- Organize tests in a parallel structure to the codebase
- Use descriptive names for test files and classes
- Group related functionality in dedicated test modules
- Use clear and consistent naming for test methods

## Test Quality Assurance

- Do not move on to the next milestone until the current milestone is complete with all tests for all milestones passing
- Do not move on to the next milestone while there are test failures anywhere in the project
- When there are test failures, think carefully about the intent of the code being tested, think carefully about the conditions required to test, setup the test conditions, and then think carefully about how to either fix the test or fix the code being tested