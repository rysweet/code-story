// Vector Test Data for similarity search testing using GDS
// This file creates test nodes with embeddings for vector similarity search tests

// First clean up any existing test vector nodes
MATCH (n:VectorNode) DETACH DELETE n;

// Drop existing vector index if it exists
DROP INDEX node_embedding IF EXISTS;

// Create test nodes with embeddings of various dimensions
CREATE (n:VectorNode {
    name: 'Node1',
    description: 'Test node 1 for vector search',
    embedding: [0.1, 0.2, 0.3, 0.4]
});

CREATE (n:VectorNode {
    name: 'Node2',
    description: 'Test node 2 for vector search',
    embedding: [0.5, 0.6, 0.7, 0.8]
});

CREATE (n:VectorNode {
    name: 'Node3',
    description: 'Test node 3 for vector search',
    embedding: [0.9, 0.8, 0.7, 0.6]
});

// Create a vector index for similarity search with GDS
CREATE VECTOR INDEX node_embedding
FOR (n:VectorNode)
ON (n.embedding)
OPTIONS {
    indexConfig: {
        `vector.dimensions`: 4,
        `vector.similarity_function`: 'cosine'
    }
};

// Verify nodes were created
MATCH (n:VectorNode) RETURN n.name, n.embedding;