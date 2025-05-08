"""Primary connector interface with pooling, async, and vector search for Neo4j."""
from collections.abc import Sequence
from typing import Any

from neo4j import AsyncGraphDatabase, GraphDatabase, basic_auth
from neo4j.exceptions import Neo4jError as Neo4jDriverError
from neo4j.exceptions import ServiceUnavailable

from .exceptions import Neo4jConnectionError, QueryError, TransactionError
from .metrics import neo4j_connection_gauge, neo4j_query_counter, neo4j_query_duration


class Neo4jConnector:
    """Neo4j connector with sync/async, pooling, and vector search support."""

    def __init__(
        self,
        uri: str | None = None,
        username: str | None = None,
        password: str | None = None,
        max_connection_pool_size: int = 10,
        connection_timeout: int = 30,
        max_transaction_retry_time: int = 15,
        **config_options: Any
    ) -> None:
        """Initialize connector with connection parameters from env vars or args."""
        if uri is None or username is None or password is None:
            raise ValueError("uri, username, and password must be provided and not None.")
        self._uri: str = uri
        self._username: str = username
        self._password: str = password
        self._max_connection_pool_size: int = max_connection_pool_size
        self._connection_timeout: int = connection_timeout
        self._max_transaction_retry_time: int = max_transaction_retry_time
        self._config_options: dict[str, Any] = config_options
        self._driver = GraphDatabase.driver(
            self._uri,
            auth=basic_auth(self._username, self._password),
            max_connection_pool_size=self._max_connection_pool_size,
            connection_timeout=self._connection_timeout,
            **self._config_options
        )
        self._async_driver = AsyncGraphDatabase.driver(
            self._uri,
            auth=basic_auth(self._username, self._password),
            max_connection_pool_size=self._max_connection_pool_size,
            connection_timeout=self._connection_timeout,
            **self._config_options
        )
        neo4j_connection_gauge.inc()

    def execute_query(
        self,
        query: str,
        params: dict[str, Any] | None = None,
        write: bool = False,
        retry_count: int = 3,
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query with automatic connection management."""
        import time
        operation = "write" if write else "read"
        for attempt in range(retry_count):
            try:
                with neo4j_query_duration.labels(operation=operation).time():
                    with self._driver.session() as session:
                        result = session.run(query, params or {})
                        neo4j_query_counter.labels(operation=operation, success="true").inc()
                        return [record.data() for record in result]
            except ServiceUnavailable as e:
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
                    continue
                neo4j_query_counter.labels(operation=operation, success="false").inc()
                raise Neo4jConnectionError(f"Neo4j service unavailable: {e}") from e
            except Neo4jDriverError as e:
                neo4j_query_counter.labels(operation=operation, success="false").inc()
                raise QueryError(f"Cypher query failed: {e}") from e
            except Exception as e:
                neo4j_query_counter.labels(operation=operation, success="false").inc()
                raise QueryError(f"Unexpected error: {e}") from e
        raise QueryError("Query failed after retries.")

    def execute_many(
        self,
        queries: Sequence[str],
        params_list: Sequence[dict[str, Any]] | None = None,
        write: bool = False,
    ) -> None:
        """Execute multiple queries in a single transaction."""
        operation = "write" if write else "read"
        try:
            with neo4j_query_duration.labels(operation=operation).time():
                with self._driver.session() as session:
                    with session.begin_transaction() as tx:
                        for i, query in enumerate(queries):
                            params = params_list[i] if params_list else None
                            tx.run(query, params or {})
                        tx.commit()
            neo4j_query_counter.labels(operation=operation, success="true").inc()
        except Neo4jDriverError as e:
            neo4j_query_counter.labels(operation=operation, success="false").inc()
            raise TransactionError(f"Transaction failed: {e}") from e
        except Exception as e:
            neo4j_query_counter.labels(operation=operation, success="false").inc()
            raise TransactionError(f"Unexpected error: {e}") from e

    async def execute_query_async(
        self,
        query: str,
        params: dict[str, Any] | None = None,
        write: bool = False,
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query asynchronously."""
        operation = "write" if write else "read"
        try:
            async with self._async_driver.session() as session:
                result = await session.run(query, params or {})
                records = [record.data() async for record in result]
                neo4j_query_counter.labels(operation=operation, success="true").inc()
                return records
        except Neo4jDriverError as e:
            neo4j_query_counter.labels(operation=operation, success="false").inc()
            raise QueryError(f"Cypher query failed: {e}") from e
        except Exception as e:
            neo4j_query_counter.labels(operation=operation, success="false").inc()
            raise QueryError(f"Unexpected error: {e}") from e

    async def check_connection_async(self) -> bool:
        """Check database connectivity asynchronously."""
        try:
            async with self._async_driver.session() as session:
                await session.run("RETURN 1")
            return True
        except Exception:
            return False

    async def close_async(self) -> None:
        """Close connections asynchronously."""
        await self._async_driver.close()
        neo4j_connection_gauge.dec()

    def initialize_schema(self) -> None:
        """Create constraints, indexes, and schema elements."""
        from .schema import initialize_schema as _init_schema
        _init_schema(self._uri, self._username, self._password)

    def create_vector_index(self, label: str, property_name: str, dimensions: int, similarity: str = "cosine") -> None:
        """Create a vector index for semantic search (Neo4j 5.x+ syntax)."""
        cypher = (
            f"""
            CREATE VECTOR INDEX {label.lower()}_{property_name}_embedding IF NOT EXISTS FOR (n:{label})
            ON n.{property_name} OPTIONS {{indexConfig: {{`vector.dimensions`: {dimensions}, `vector.similarity_function`: '{similarity}'}}}}
            """
        )
        # Remove leading/trailing whitespace and newlines for Cypher compatibility
        cypher = " ".join(line.strip() for line in cypher.strip().splitlines())
        self.execute_query(cypher, write=True)

    def semantic_search(self, query_embedding: list[float], node_label: str, limit: int = 10) -> list[dict[str, Any]]:
        """Perform vector similarity search using the provided embedding."""
        cypher = f"""
        MATCH (n:{node_label})
        WHERE n.embedding IS NOT NULL
        WITH n, gds.similarity.cosine(n.embedding, $embedding) AS score
        ORDER BY score DESC
        LIMIT $limit
        RETURN n, score
        """
        return self.execute_query(cypher, {"embedding": query_embedding, "limit": limit})

    def check_connection(self) -> bool:
        """Check if database is accessible and return basic info."""
        try:
            with self._driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Close all connections in the pool."""
        self._driver.close()
        neo4j_connection_gauge.dec()

    def __enter__(self) -> "Neo4jConnector":
        """Support for context manager protocol."""
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Clean up resources when exiting context."""
        self.close()
