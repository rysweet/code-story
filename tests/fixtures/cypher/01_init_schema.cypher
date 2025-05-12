// Neo4j Schema Initialization for Test Environment
// This script defines the schema constraints and indexes for the test database

// Clear any existing database content
MATCH (n) DETACH DELETE n;

// Create constraints for unique identifiers
CREATE CONSTRAINT unique_file_path IF NOT EXISTS
FOR (f:File) REQUIRE f.path IS UNIQUE;

CREATE CONSTRAINT unique_directory_path IF NOT EXISTS
FOR (d:Directory) REQUIRE d.path IS UNIQUE;

CREATE CONSTRAINT unique_function_id IF NOT EXISTS
FOR (f:Function) REQUIRE f.id IS UNIQUE;

CREATE CONSTRAINT unique_class_id IF NOT EXISTS
FOR (c:Class) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT unique_module_id IF NOT EXISTS
FOR (m:Module) REQUIRE m.id IS UNIQUE;

// Create indexes for common lookup fields
CREATE INDEX file_name IF NOT EXISTS FOR (f:File) ON (f.name);
CREATE INDEX directory_name IF NOT EXISTS FOR (d:Directory) ON (d.name);
CREATE INDEX function_name IF NOT EXISTS FOR (f:Function) ON (f.name);
CREATE INDEX class_name IF NOT EXISTS FOR (c:Class) ON (c.name);
CREATE INDEX module_name IF NOT EXISTS FOR (m:Module) ON (m.name);

// Create standard indexes for text fields (instead of full-text search)
CREATE INDEX file_content IF NOT EXISTS FOR (f:File) ON (f.content);
CREATE INDEX file_summary IF NOT EXISTS FOR (f:File) ON (f.summary);
CREATE INDEX function_summary IF NOT EXISTS FOR (f:Function) ON (f.summary);
CREATE INDEX class_summary IF NOT EXISTS FOR (c:Class) ON (c.summary);
CREATE INDEX module_summary IF NOT EXISTS FOR (m:Module) ON (m.summary);

// Initial seed data for testing
CREATE (r:Repository {
  name: 'test-repo',
  path: '/test/repo',
  description: 'Test repository for integration tests',
  created_at: datetime()
});

// Create some minimal structure for basic tests
CREATE (root:Directory {
  name: 'src',
  path: '/test/repo/src',
  created_at: datetime()
});

MATCH (r:Repository {name: 'test-repo'})
MATCH (d:Directory {path: '/test/repo/src'})
CREATE (r)-[:CONTAINS]->(d);

RETURN 'Schema initialization complete' as status;