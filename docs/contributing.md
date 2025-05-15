# Contributing to Code Story

Thank you for your interest in contributing to Code Story! This guide will help you get started with the contribution process.

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker and Docker Compose
- Poetry 1.8+
- Git

### Setting Up the Development Environment

1. Fork the repository on GitHub
2. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/code-story.git
   cd code-story
   ```

3. Set up the development environment:
   ```bash
   # Install Python dependencies
   poetry install
   
   # Install Node.js dependencies
   npm install
   ```

4. Start the development environment:
   ```bash
   # Start dependencies using Docker Compose
   docker compose up -d neo4j redis
   
   # Run the service in development mode
   poetry run uvicorn src.codestory_service.main:app --reload
   
   # In another terminal, run the GUI
   npm run dev
   ```

## Development Workflow

1. Create a branch for your feature or fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes, following the code style guidelines

3. Write tests for your changes

4. Run the tests to ensure they pass:
   ```bash
   # Run Python tests
   poetry run pytest
   
   # Run JavaScript/TypeScript tests
   npm test
   ```

5. Run linting and type checking:
   ```bash
   # Python linting
   poetry run ruff check .
   
   # Python type checking
   poetry run mypy .
   
   # JavaScript/TypeScript linting
   npm run lint
   ```

6. Commit your changes with a descriptive message:
   ```bash
   git commit -m "Add feature: your feature description"
   ```

7. Push your branch to GitHub:
   ```bash
   git push origin feature/your-feature-name
   ```

8. Submit a pull request to the main repository

## Code Style Guidelines

### Python

- Follow PEP 8 and the Google Python Style Guide
- Use Google-style docstrings for all modules, classes, and functions
- Add type annotations for all function parameters and return values
- Use meaningful variable and function names
- Keep functions and methods focused on a single responsibility
- Write comprehensive unit tests

### JavaScript/TypeScript

- Follow the project's ESLint configuration
- Use functional components and hooks for React components
- Add TypeScript interfaces for props and state
- Use destructuring for props
- Follow the container/presentational component pattern
- Write tests using Jest and React Testing Library

## Pull Request Process

1. Update the documentation with details of your changes
2. Add tests for your changes
3. Ensure all tests and linting checks pass
4. Submit the pull request to the main repository
5. Address any feedback from code reviewers

## Testing Guidelines

- Write unit tests for all new functionality
- Ensure existing tests continue to pass
- Aim for high test coverage, especially for critical paths
- Use integration tests for key workflows
- Mock external dependencies appropriately

## Documentation Guidelines

- Update the documentation for any feature changes
- Write clear, concise, and grammatically correct documentation
- Use Markdown for all documentation
- Include examples where appropriate
- Follow the documentation structure in the project

## Community

- Be respectful and considerate in all communications
- Help other contributors with their questions
- Participate in code reviews and discussions
- Report bugs and issues through the GitHub issue tracker

Thank you for contributing to Code Story!