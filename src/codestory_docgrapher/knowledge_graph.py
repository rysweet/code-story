from typing import Any

"Knowledge graph builder for documentation entities and relationships.\n\nThis module provides functionality for building a knowledge graph of\ndocumentation entities and relationships, and storing it in Neo4j.\n"
import logging
import time

from codestory.graphdb.neo4j_connector import Neo4jConnector

from .entity_linker import EntityLinker
from .models import (
    DocumentationEntity,
    DocumentationFile,
    DocumentationGraph,
    DocumentationRelationship,
    RelationType,
)

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """Builds a knowledge graph of documentation entities and relationships.

    This class takes documentation entities and relationships, builds a
    knowledge graph, and stores it in Neo4j.
    """

    def __init__(self: Any, connector: Neo4jConnector, repository_path: str) -> None:
        """Initialize the knowledge graph.

        Args:
            connector: Neo4j database connector
            repository_path: Path to the repository
        """
        self.connector = connector
        self.repository_path = repository_path
        self.graph = DocumentationGraph()
        self.entity_linker = EntityLinker(connector, repository_path)

    def add_document(self: Any, document: DocumentationFile) -> None:
        """Add a document to the graph.

        Args:
            document: Documentation file to add
        """
        self.graph.add_document(document)

    def add_entities(self: Any, entities: list[DocumentationEntity]) -> None:
        """Add entities to the graph.

        Args:
            entities: List of documentation entities to add
        """
        for entity in entities:
            self.graph.add_entity(entity)

    def add_relationships(
        self: Any, relationships: list[DocumentationRelationship]
    ) -> None:
        """Add relationships to the graph.

        Args:
            relationships: List of documentation relationships to add
        """
        for relationship in relationships:
            self.graph.add_relationship(relationship)

    def link_to_code_entities(self: Any) -> None:
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

    def store_in_neo4j(self: Any) -> None:
        """Store the graph in Neo4j.

        This creates Neo4j nodes and relationships for all documents,
        entities, and relationships in the graph.
        """
        self._create_document_nodes()
        self._create_entity_nodes()
        self._create_relationships()
        logger.info(
            f"Stored documentation graph in Neo4j: {len(self.graph.documents)} documents, {len(self.graph.entities)} entities, {len(self.graph.relationships)} relationships"
        )

    def _create_document_nodes(self: Any) -> None:
        """Create Neo4j nodes for documentation documents."""
        for document in self.graph.documents.values():
            query = "\n            MATCH (d:Documentation {path: $path})\n            RETURN d\n            "
            existing = self.connector.execute_query(
                query, {"path": document.path}
            )
            if existing:
                logger.info(f"Documentation node already exists for {document.path}")
                continue
            query = "\n            CREATE (d:Documentation {\n                path: $path,\n                name: $name,\n                type: $type,\n                timestamp: $timestamp\n            })\n            WITH d\n            MATCH (f:File {path: $path})\n            MERGE (f)-[:HAS_DOCUMENTATION]->(d)\n            RETURN ID(d) as id\n            "
            result = self.connector.execute_query(
                query,
                {
                    "path": document.path,
                    "name": document.name,
                    "type": document.doc_type.value,
                    "timestamp": time.time(),
                },
                write=True
            )
            if result:
                logger.debug(f"Created Documentation node for {document.path}")
            else:
                logger.warning(
                    f"Failed to create Documentation node for {document.path}"
                )

    def _create_entity_nodes(self: Any) -> None:
        """Create Neo4j nodes for documentation entities."""
        import json
        for entity in self.graph.entities.values():
            query = "\n            CREATE (e:DocumentationEntity {\n                id: $id,\n                type: $type,\n                content: $content,\n                file_path: $file_path,\n                source_text: $source_text,\n                line_number: $line_number,\n                metadata_json: $metadata_json\n            })\n            WITH e\n            MATCH (d:Documentation {path: $file_path})\n            MERGE (d)-[:CONTAINS]->(e)\n            RETURN ID(e) as id\n            "
            # Convert metadata to JSON string to avoid Neo4j type issues
            metadata_json = json.dumps(entity.metadata) if entity.metadata else "{}"
            result = self.connector.execute_query(
                query,
                {
                    "id": entity.id,
                    "type": entity.type.value,
                    "content": entity.content,
                    "file_path": entity.file_path,
                    "source_text": entity.source_text[:1000],
                    "line_number": entity.line_number,
                    "metadata_json": metadata_json,
                },
                write=True
            )
            if result:
                logger.debug(f"Created DocumentationEntity node for {entity.id}")
            else:
                logger.warning(
                    f"Failed to create DocumentationEntity node for {entity.id}"
                )

    def _create_relationships(self: Any) -> None:
        """Create Neo4j relationships between entities."""
        import json
        for rel in self.graph.relationships.values():
            if rel.type in [
                RelationType.CONTAINS,
                RelationType.PRECEDES,
                RelationType.FOLLOWS,
                RelationType.PART_OF,
            ]:
                # Filter properties to only include primitive types or convert to JSON
                safe_properties = {}
                for key, value in rel.properties.items():
                    if isinstance(value, (str, int, float, bool, type(None))):
                        safe_properties[key] = value
                    else:
                        safe_properties[f"{key}_json"] = json.dumps(value)
                
                query = f"\n                MATCH (s:DocumentationEntity {{id: $source_id}})\n                MATCH (t:DocumentationEntity {{id: $target_id}})\n                MERGE (s)-[r:{rel.type.value}]->(t)\n                SET r += $properties\n                RETURN ID(r) as id\n                "
                result = self.connector.execute_query(
                    query,
                    {
                        "source_id": rel.source_id,
                        "target_id": rel.target_id,
                        "properties": safe_properties,
                    },
                    write=True
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
                # Filter properties to only include primitive types or convert to JSON
                safe_properties = {}
                for key, value in rel.properties.items():
                    if isinstance(value, (str, int, float, bool, type(None))):
                        safe_properties[key] = value
                    else:
                        safe_properties[f"{key}_json"] = json.dumps(value)
                
                query = f"\n                MATCH (s:DocumentationEntity {{id: $source_id}})\n                MATCH (c) WHERE ID(c) = $target_id\n                MERGE (s)-[r:{rel.type.value}]->(c)\n                SET r += $properties\n                RETURN ID(r) as id\n                "
                result = self.connector.execute_query(
                    query,
                    {
                        "source_id": rel.source_id,
                        "target_id": int(rel.target_id),
                        "properties": safe_properties,
                    },
                    write=True
                )
                if result:
                    logger.debug(
                        f"Created relationship {rel.type.value} between documentation and code entities"
                    )
                else:
                    logger.warning(
                        f"Failed to create relationship {rel.type.value} between documentation and code entities"
                    )

    def get_graph_stats(self: Any) -> dict[str, Any]:
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

    def _count_entity_types(self: Any) -> dict[str, int]:
        """Count entities by type.

        Returns:
            Dict mapping entity types to counts
        """
        counts: dict[str, int] = {}
        for entity in self.graph.entities.values():
            type_name = entity.type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts

    def _count_relationship_types(self: Any) -> dict[str, int]:
        """Count relationships by type.

        Returns:
            Dict mapping relationship types to counts
        """
        counts: dict[str, int] = {}
        for rel in self.graph.relationships.values():
            type_name = rel.type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts
