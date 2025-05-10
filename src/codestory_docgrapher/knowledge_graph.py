"""Knowledge graph builder for documentation entities and relationships.

This module provides functionality for building a knowledge graph of
documentation entities and relationships, and storing it in Neo4j.
"""

import logging
import time
from typing import Dict, List, Optional, Set, Tuple

from codestory.graphdb.neo4j_connector import Neo4jConnector
from .models import DocumentationEntity, DocumentationFile
from .models import DocumentationGraph, DocumentationRelationship
from .models import EntityType, RelationType
from .entity_linker import EntityLinker

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """Builds a knowledge graph of documentation entities and relationships.

    This class takes documentation entities and relationships, builds a
    knowledge graph, and stores it in Neo4j.
    """

    def __init__(self, connector: Neo4jConnector, repository_path: str):
        """Initialize the knowledge graph.

        Args:
            connector: Neo4j database connector
            repository_path: Path to the repository
        """
        self.connector = connector
        self.repository_path = repository_path
        self.graph = DocumentationGraph()
        self.entity_linker = EntityLinker(connector, repository_path)

    def add_document(self, document: DocumentationFile) -> None:
        """Add a document to the graph.

        Args:
            document: Documentation file to add
        """
        self.graph.add_document(document)

    def add_entities(self, entities: List[DocumentationEntity]) -> None:
        """Add entities to the graph.

        Args:
            entities: List of documentation entities to add
        """
        for entity in entities:
            self.graph.add_entity(entity)

    def add_relationships(self, relationships: List[DocumentationRelationship]) -> None:
        """Add relationships to the graph.

        Args:
            relationships: List of documentation relationships to add
        """
        for relationship in relationships:
            self.graph.add_relationship(relationship)

    def link_to_code_entities(self) -> None:
        """Link documentation entities to code entities.

        This creates relationships between documentation entities and
        the code entities they reference or describe.
        """
        entities = list(self.graph.entities.values())
        relationships = self.entity_linker.link_entities(entities)
        self.add_relationships(relationships)

        logger.info(
            f"Linked {len(relationships)} documentation entities to code entities"
        )

    def store_in_neo4j(self) -> None:
        """Store the graph in Neo4j.

        This creates Neo4j nodes and relationships for all documents,
        entities, and relationships in the graph.
        """
        # First, create Documentation nodes for documents
        self._create_document_nodes()

        # Then, create nodes for entities
        self._create_entity_nodes()

        # Finally, create relationships
        self._create_relationships()

        logger.info(
            f"Stored documentation graph in Neo4j: {len(self.graph.documents)} documents, {len(self.graph.entities)} entities, {len(self.graph.relationships)} relationships"
        )

    def _create_document_nodes(self) -> None:
        """Create Neo4j nodes for documentation documents."""
        for document in self.graph.documents.values():
            # Check if the document already exists
            query = """
            MATCH (d:Documentation {path: $path})
            RETURN d
            """

            existing = self.connector.run_query(
                query, parameters={"path": document.path}, fetch_one=True
            )

            if existing:
                logger.info(f"Documentation node already exists for {document.path}")
                continue

            # Create a Documentation node
            query = """
            CREATE (d:Documentation {
                path: $path,
                name: $name,
                type: $type,
                timestamp: $timestamp
            })
            WITH d
            MATCH (f:File {path: $path})
            MERGE (f)-[:HAS_DOCUMENTATION]->(d)
            RETURN ID(d) as id
            """

            result = self.connector.run_query(
                query,
                parameters={
                    "path": document.path,
                    "name": document.name,
                    "type": document.doc_type.value,
                    "timestamp": time.time(),
                },
                fetch_one=True,
            )

            if result:
                logger.debug(f"Created Documentation node for {document.path}")
            else:
                logger.warning(
                    f"Failed to create Documentation node for {document.path}"
                )

    def _create_entity_nodes(self) -> None:
        """Create Neo4j nodes for documentation entities."""
        for entity in self.graph.entities.values():
            # Create a DocumentationEntity node
            query = """
            CREATE (e:DocumentationEntity {
                id: $id,
                type: $type,
                content: $content,
                file_path: $file_path,
                source_text: $source_text,
                line_number: $line_number,
                metadata: $metadata
            })
            WITH e
            MATCH (d:Documentation {path: $file_path})
            MERGE (d)-[:CONTAINS]->(e)
            RETURN ID(e) as id
            """

            # Convert metadata to a format compatible with Neo4j
            metadata = {}
            for key, value in entity.metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    metadata[key] = value

            result = self.connector.run_query(
                query,
                parameters={
                    "id": entity.id,
                    "type": entity.type.value,
                    "content": entity.content,
                    "file_path": entity.file_path,
                    "source_text": entity.source_text[:1000],  # Limit length
                    "line_number": entity.line_number,
                    "metadata": metadata,
                },
                fetch_one=True,
            )

            if result:
                logger.debug(f"Created DocumentationEntity node for {entity.id}")
            else:
                logger.warning(
                    f"Failed to create DocumentationEntity node for {entity.id}"
                )

    def _create_relationships(self) -> None:
        """Create Neo4j relationships between entities."""
        # First, create relationships between documentation entities
        for rel in self.graph.relationships.values():
            if rel.type in [
                RelationType.CONTAINS,
                RelationType.PRECEDES,
                RelationType.FOLLOWS,
                RelationType.PART_OF,
            ]:
                # These relationships are between documentation entities
                query = (
                    """
                MATCH (s:DocumentationEntity {id: $source_id})
                MATCH (t:DocumentationEntity {id: $target_id})
                MERGE (s)-[r:%s]->(t)
                SET r += $properties
                RETURN ID(r) as id
                """
                    % rel.type.value
                )

                result = self.connector.run_query(
                    query,
                    parameters={
                        "source_id": rel.source_id,
                        "target_id": rel.target_id,
                        "properties": rel.properties,
                    },
                    fetch_one=True,
                )

                if result:
                    logger.debug(
                        f"Created relationship {rel.type.value} between documentation entities"
                    )
                else:
                    logger.warning(
                        f"Failed to create relationship {rel.type.value} between documentation entities"
                    )

            elif rel.type in [RelationType.DESCRIBES, RelationType.REFERENCES]:
                # These relationships are between documentation entities and code entities
                query = (
                    """
                MATCH (s:DocumentationEntity {id: $source_id})
                MATCH (c) WHERE ID(c) = $target_id
                MERGE (s)-[r:%s]->(c)
                SET r += $properties
                RETURN ID(r) as id
                """
                    % rel.type.value
                )

                result = self.connector.run_query(
                    query,
                    parameters={
                        "source_id": rel.source_id,
                        "target_id": int(rel.target_id),
                        "properties": rel.properties,
                    },
                    fetch_one=True,
                )

                if result:
                    logger.debug(
                        f"Created relationship {rel.type.value} between documentation and code entities"
                    )
                else:
                    logger.warning(
                        f"Failed to create relationship {rel.type.value} between documentation and code entities"
                    )

    def get_graph_stats(self) -> Dict:
        """Get statistics about the graph.

        Returns:
            Dict with graph statistics
        """
        return {
            "documents": len(self.graph.documents),
            "entities": len(self.graph.entities),
            "relationships": len(self.graph.relationships),
            "entity_types": self._count_entity_types(),
            "relationship_types": self._count_relationship_types(),
        }

    def _count_entity_types(self) -> Dict[str, int]:
        """Count entities by type.

        Returns:
            Dict mapping entity types to counts
        """
        counts = {}
        for entity in self.graph.entities.values():
            type_name = entity.type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts

    def _count_relationship_types(self) -> Dict[str, int]:
        """Count relationships by type.

        Returns:
            Dict mapping relationship types to counts
        """
        counts = {}
        for rel in self.graph.relationships.values():
            type_name = rel.type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts
