# Project Specifications and Development Methodology

The project is built using a spec driven modular approach. 

The specifications start with the [Main Specification](./../specs/Main.md). Each major component then will have its own specification directory with more detailed specifications that are co-created with LLMs using this document. Each module shall be broken down into small enough components (individual specifications) that the entire component can be regenerated from its specification in a single inference. When there are changes to code the specification must also be updated and the code regenerated from the specification.

The specifications shall include detailed descriptions, architectural notes, dependencies, technical stack, detailed user stories, test criteria, example of api usage for each module or component, and enough instructions to allow the one shot cogeneration of the entire component or module from a single LLM prompt.

## Development Process

The project will be built following these steps:

1. Break down this specification into derived specifications for each major module.
2. Each derived specification will be broken down into smaller specifications for each sub-module or component. 
3. If necessary, each sub-module or component will be broken down into smaller specifications, until each specification captures a single component that can be generated in a single LLM inference.
4. Each final specification will include a detailed prompt for the LLM to use to generate the code for that component. 
5. We will then walk through the specifications and generate the code for each component in the order of the required dependencies. 
6. During each generation stage we will run the tests for each component and ensure that all tests pass before moving on to the next component.
7. The AI Agent will also take the role of a reviewer and will review the generated code for each component and ensure that it meets the specifications, coding guidelines, and best practices before moving on to the next component.
8. We will also run the tests for the entire project after each component is generated to ensure that all components work together as expected.
9. Each component will have its own documentation generated to facilitate understanding and usage.

## Status Tracking

Keep the plan status up to date by updating a file called `/Specifications/status.md`. You can check this file to find out the most recent status of the plan.

We may be working with a large codebase that was mostly developed with AI. The codebase may contain a number of errors and anti-patterns. Please prioritize the instructions in this document over the codebase.