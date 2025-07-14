# Configuration

CodeStory uses [Pydantic Settings](https://docs.pydantic.dev/latest/usage/pydantic_settings/) to manage configuration. Settings are loaded in the following order:
1. Environment variables (highest precedence)
2. Values from a `.env` file in the project root (if present)
3. (No Pydantic defaults; all fields are required)

## Setting Up

1. Copy `.env.example` to `.env` and edit as needed:
   ```sh
   cp .env.example .env
   ```
2. Set required values for your environment. **Do not hardcode secrets in code or docs.** Use environment variables or the `.env` file (excluded from version control).

## Required Fields

The following environment variables are required for CodeStory to connect to Neo4j:

| Variable         | Description                |
|------------------|---------------------------|
| NEO4J_URI        | Neo4j connection URI      |
| NEO4J_USER       | Neo4j username            |
| NEO4J_PASSWORD   | Neo4j password            |

If any are missing, CodeStory will fail to start.

## Common Configuration Fields

Other important fields (see `.env.example` for full list):

| Variable                    | Description                        |
|-----------------------------|------------------------------------|
| REDIS__URI                  | Redis connection URI               |
| AZURE_OPENAI__ENDPOINT      | Azure OpenAI API endpoint          |
| AZURE_OPENAI__DEPLOYMENT_ID | Azure OpenAI deployment ID         |
| AZURE_TENANT_ID             | Azure tenant for authentication    |
| CODESTORY_SERVICE_PORT      | Service port for CodeStory         |
| CODESTORY_CONFIG_PATH       | Path to TOML config (optional)     |

## Best Practices

- Never commit real secrets or credentials to the repository.
- Document any required environment variables in your `.env.example` and README.
- Use `.env` for local development; use environment variables for production.

For more details, see the [example environment file](https://github.com/your-org/codestory/blob/feature/codestory-scaffold/.env.example).