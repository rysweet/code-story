# 1.6 Error Handling and Propagation (Cross-Component)

**Previous:** [Overview & Architecture](./overview.md) | **Next:** [Scaffolding](../02-scaffolding/scaffolding.md)

**Part of:** [Overview & Architecture](./overview.md)

**Used by:** All components

## 1.6.1 Purpose

Establish a unified, robust error handling and propagation strategy across all Code Story components. This ensures errors are consistently classified, logged, propagated, and surfaced to users and operators, enabling effective troubleshooting and reliable system behavior.

## 1.6.2 Unified Error Taxonomy

All components must use a consistent error classification system, organized in a hierarchy:

- **SystemErrors** – Infrastructure/environment issues
  - `ConfigurationError` – Invalid/missing configuration
  - `ResourceError` – Resource unavailability (Neo4j, Redis, etc.)
  - `AuthenticationError` – Authentication failures
  - `AuthorizationError` – Permission issues

- **ApplicationErrors** – Business logic and application-specific errors
  - `ValidationError` – Invalid input data
  - `NotFoundError` – Requested resource doesn't exist
  - `ConflictError` – Operation conflicts with system state
  - `OperationError` – Failed operations (e.g., ingestion failures)

- **ExternalServiceErrors** – Issues with external services
  - `OpenAIError` – Errors from OpenAI API
  - `BlarifyError` – Errors from Blarify tool
  - `NetworkError` – General communication errors

## 1.6.3 Error Propagation Strategy

- **Contextual Capture**: Errors must be captured with relevant context (e.g., operation, parameters, correlation/request ID).
- **Transformation**: Errors from lower-level components should be transformed into the appropriate error type for the receiving component, preserving the original cause.
- **Metadata Enrichment**: Add propagation path and correlation/request IDs to all errors for traceability.
- **User-Facing Translation**: Errors surfaced to CLI/GUI must be translated into actionable, human-readable messages, with troubleshooting guidance and without leaking sensitive details.
- **Circuit Breaking & Fallbacks**: Components must implement circuit breaking for downstream dependencies (e.g., Neo4j, Redis, OpenAI) to prevent cascading failures. Fallbacks or fast-fail responses should be used when circuits are open.
- **Structured Logging**: All errors must be logged in a structured format with error type, context, and correlation/request ID.
- **Observability**: Error rates, types, and propagation paths must be tracked via metrics and traces (Prometheus, OpenTelemetry).

## 1.6.4 Implementation Across Components

- **Configuration Module**: Validation errors include field-level details; KeyVault errors are mapped to `ResourceError`.
- **Graph Database Service**: All errors include correlation IDs and query context; circuit breaking for Neo4j failures; fallback for read operations where possible.
- **Ingestion Pipeline**: Step-level error recovery and partial failure handling; detailed error context for each step; workflow resumption after error correction.
- **Code Story Service**: API responses use the error taxonomy; errors include troubleshooting URLs and correlation headers; HTTP status codes map to error types.
- **CLI/GUI**: Errors are color-coded and actionable; error IDs are shown for support; verbose/debug output available for troubleshooting.

## 1.6.5 Error Documentation

Each error type must be documented with:
- Description and potential causes
- Troubleshooting steps
- Required remediation actions
- Example occurrences

---

