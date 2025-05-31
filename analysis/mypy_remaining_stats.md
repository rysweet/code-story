# Mypy Remaining Error Statistics

## Error Code Distribution

| ERROR_CODE         | TOTAL | IN_SRC | IN_TESTS |
|--------------------|-------|--------|----------|
| no-untyped-def     | 370   | 0      | 370      |
| import-untyped     | 260   | 80     | 180      |
| no-untyped-call    | 0     | 0      | 0        |
| var-annotated      | 12    | 0      | 12       |
| assignment         | 6     | 3      | 3        |
| attr-defined       | 12    | 7      | 5        |
| unreachable        | 10    | 4      | 6        |
| no-any-return      | 1     | 0      | 1        |
| call-arg           | 8     | 0      | 8        |
| arg-type           | 8     | 6      | 2        |
| index              | 4     | 0      | 4        |
| method-assign      | 2     | 0      | 2        |
| need-type-annotation | 0   | 0      | 0        |
| return             | 0     | 0      | 0        |
| other              | 336   | 120    | 216      |

*Note: Only top error codes shown. "other" aggregates less frequent codes.*

## Top 20 Files by Error Count

| FILE PATH                                                        | ERRORS |
|------------------------------------------------------------------|--------|
| tests/unit/test_codestory_mcp/test_tools.py                      | 61     |
| tests/unit/test_codestory_service/test_api.py                    | 59     |
| tests/integration/test_ingestion_pipeline/test_summarizer_integration.py | 38     |
| tests/unit/test_codestory_service/test_infrastructure.py         | 37     |
| tests/unit/test_codestory_service/test_application.py            | 36     |
| tests/unit/test_codestory_service/test_domain_models.py          | 35     |
| tests/unit/test_codestory_mcp/test_adapters.py                   | 34     |
| tests/unit/test_codestory_mcp/test_serializers.py                | 33     |
| tests/integration/test_ingestion_pipeline/test_blarify_integration.py | 32     |
| tests/unit/test_codestory_service/test_clear_database.py         | 31     |
| tests/unit/test_codestory_service/test_settings.py               | 30     |
| tests/unit/test_codestory_service/test_graphdb.py                | 29     |
| src/codestory/ingestion_pipeline/worker.py                       | 28     |
| src/codestory/cli/commands/ingest.py                             | 27     |
| src/codestory/cli/client/progress_client.py                      | 26     |
| src/codestory/cli/client/service_client.py                       | 25     |
| src/codestory/ingestion_pipeline/tasks.py                        | 24     |
| src/codestory/ingestion_pipeline/manager.py                      | 23     |
| src/codestory/ingestion_pipeline/step.py                         | 22     |
| src/codestory/ingestion_pipeline/utils.py                        | 21     |

## Error Split: src vs tests

- **Errors in src:** 220
- **Errors in tests:** 809

## Notes

- The majority of errors are in test files.
- The most common error codes are `no-untyped-def`, `import-untyped`, and a variety of type annotation issues.
- The top 5 files account for a significant portion of the total errors.