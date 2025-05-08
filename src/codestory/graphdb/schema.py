"""Schema definitions and initialization for Neo4j database."""

from neo4j import GraphDatabase, basic_auth

from .exceptions import SchemaError

SCHEMA_QUERIES = [
    # Unique constraints (Neo4j 5.x+ syntax)
    """
    CREATE CONSTRAINT file_path_unique IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE
    """,
    """
    CREATE CONSTRAINT dir_path_unique IF NOT EXISTS FOR (d:Directory) REQUIRE d.path IS UNIQUE
    """,
    """
    CREATE CONSTRAINT class_name_module_unique IF NOT EXISTS FOR (c:Class) REQUIRE (c.name, c.module) IS UNIQUE
    """,
    # Full-text indexes
    """
    CREATE FULLTEXT INDEX file_content IF NOT EXISTS FOR (f:File) ON EACH [f.content]
    """,
    """
    CREATE FULLTEXT INDEX code_name IF NOT EXISTS FOR (n:Class|Function|Module) ON EACH [n.name]
    """,
    # Vector indexes
    """
    CREATE VECTOR INDEX summary_embedding IF NOT EXISTS FOR (s:Summary) ON s.embedding OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: "cosine"}}
    """,
    """
    CREATE VECTOR INDEX documentation_embedding IF NOT EXISTS FOR (d:Documentation) ON d.embedding OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: "cosine"}}
    """
]

def initialize_schema(uri: str, username: str, password: str, database: str | None = None) -> None:
    """Create constraints, indexes, and schema elements in Neo4j."""
    if uri is None or username is None or password is None:
        raise SchemaError("uri, username, and password must be provided and not None.")
    try:
        driver = GraphDatabase.driver(uri, auth=basic_auth(username, password))
        with driver.session(database=database) as session:
            for query in SCHEMA_QUERIES:
                session.run(query)
    except Exception as e:
        raise SchemaError(f"Failed to initialize schema: {e}") from e
    finally:
        if "driver" in locals():
            driver.close()
