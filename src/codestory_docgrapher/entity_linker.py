"""Entity linker for linking documentation entities to code entities.

This module provides functionality for linking documentation entities to code
entities in the Neo4j database.
"""

import logging
import re

from codestory.graphdb.neo4j_connector import Neo4jConnector

from .models import DocumentationEntity, DocumentationRelationship, RelationType
from .utils.path_matcher import PathMatcher

logger = logging.getLogger(__name__)


class EntityLinker:
    """Links documentation entities to code entities.

    This class analyzes documentation entities and creates relationships
    between them and relevant code entities in the Neo4j database.
    """

    def __init__(self, connector: Neo4jConnector, repository_path: str):
        """Initialize the entity linker.

        Args:
            connector: Neo4j database connector
            repository_path: Path to the repository
        """
        self.connector = connector
        self.repository_path = repository_path
        self.path_matcher = PathMatcher(connector, repository_path)

        # Regular expressions for identifying references to code entities
        self.file_ref_pattern = re.compile(r"(?:^|[^\w/])(\w+\.\w+)(?:$|[^\w])")
        self.class_ref_pattern = re.compile(r"(?:^|[^\w/])([A-Z]\w+)(?:$|[^\w])")
        self.function_ref_pattern = re.compile(r"(?:^|[^\w/])(\w+\(\))(?:$|[^\w])")
        self.module_ref_pattern = re.compile(r"(?:^|[^\w/])([\w.]+)(?:$|[^\w])")

        # Cache for Neo4j IDs to avoid repeated queries
        self.entity_cache = {}

    def link_entities(
        self, entities: list[DocumentationEntity]
    ) -> list[DocumentationRelationship]:
        """Link documentation entities to code entities.

        Args:
            entities: List of documentation entities

        Returns:
            List of relationships between documentation and code entities
        """
        relationships = []

        # Process each entity
        for entity in entities:
            entity_rels = self._link_entity(entity)
            relationships.extend(entity_rels)

        logger.info(
            f"Created {len(relationships)} relationships between documentation and code entities"
        )
        return relationships

    def _link_entity(
        self, entity: DocumentationEntity
    ) -> list[DocumentationRelationship]:
        """Link a documentation entity to code entities.

        Args:
            entity: Documentation entity to link

        Returns:
            List of relationships
        """
        relationships = []

        # Check for explicit references in entity content
        if entity.referenced_code:
            for code_id in entity.referenced_code:
                relationship = DocumentationRelationship(
                    type=RelationType.DESCRIBES, source_id=entity.id, target_id=code_id
                )
                relationships.append(relationship)

        # Extract references from entity content
        content_refs = self._extract_code_references(entity.content)
        for code_type, code_name in content_refs:
            # Find code entities matching the reference
            code_ids = self._find_code_entities(code_type, code_name)

            for code_id in code_ids:
                relationship = DocumentationRelationship(
                    type=RelationType.REFERENCES,
                    source_id=entity.id,
                    target_id=code_id,
                    properties={
                        "reference_type": code_type,
                        "reference_name": code_name,
                    },
                )
                relationships.append(relationship)

        # Try to link the entity to code based on its location (for docstrings)
        location_rels = self._link_by_location(entity)
        relationships.extend(location_rels)

        return relationships

    def _extract_code_references(self, content: str) -> list[tuple[str, str]]:
        """Extract references to code entities from text content.

        Args:
            content: Text content to analyze

        Returns:
            List of (entity_type, entity_name) tuples
        """
        references = []

        # Extract file references
        for match in self.file_ref_pattern.finditer(content):
            ref = match.group(1)
            if self._is_likely_file(ref):
                references.append(("file", ref))

        # Extract class references
        for match in self.class_ref_pattern.finditer(content):
            ref = match.group(1)
            if self._is_likely_class(ref):
                references.append(("class", ref))

        # Extract function references
        for match in self.function_ref_pattern.finditer(content):
            ref = match.group(1).rstrip("()")
            references.append(("function", ref))

        # Extract module references
        for match in self.module_ref_pattern.finditer(content):
            ref = match.group(1)
            if "." in ref and self._is_likely_module(ref):
                references.append(("module", ref))

        return references

    def _is_likely_file(self, name: str) -> bool:
        """Check if a name is likely to be a file reference.

        Args:
            name: Name to check

        Returns:
            True if the name is likely a file reference, False otherwise
        """
        return "." in name and not name.startswith(".")

    def _is_likely_class(self, name: str) -> bool:
        """Check if a name is likely to be a class reference.

        Args:
            name: Name to check

        Returns:
            True if the name is likely a class reference, False otherwise
        """
        # Classes typically start with an uppercase letter and don't contain dots
        return name[0].isupper() and "." not in name and len(name) > 1

    def _is_likely_module(self, name: str) -> bool:
        """Check if a name is likely to be a module reference.

        Args:
            name: Name to check

        Returns:
            True if the name is likely a module reference, False otherwise
        """
        # Modules typically contain dots and don't have spaces
        return "." in name and " " not in name

    def _find_code_entities(self, entity_type: str, entity_name: str) -> list[str]:
        """Find code entities matching a reference.

        Args:
            entity_type: Type of entity to find
            entity_name: Name of entity to find

        Returns:
            List of Neo4j IDs for matching entities
        """
        # Check cache first
        cache_key = f"{entity_type}:{entity_name}"
        if cache_key in self.entity_cache:
            return self.entity_cache[cache_key]

        results = []

        # Query Neo4j for matching entities
        if entity_type == "file":
            query = """
            MATCH (f:File)
            WHERE f.name = $name OR f.path = $name OR f.path ENDS WITH $name
            RETURN ID(f) as id
            """

            records = self.connector.run_query(
                query, parameters={"name": entity_name}, fetch_all=True
            )

            results = [str(record["id"]) for record in records]

        elif entity_type == "class":
            query = """
            MATCH (c:Class)
            WHERE c.name = $name OR c.qualified_name = $name OR c.qualified_name ENDS WITH $name
            RETURN ID(c) as id
            """

            records = self.connector.run_query(
                query, parameters={"name": entity_name}, fetch_all=True
            )

            results = [str(record["id"]) for record in records]

        elif entity_type == "function":
            query = """
            MATCH (f:Function)
            WHERE f.name = $name OR f.qualified_name = $name OR f.qualified_name ENDS WITH $name
            RETURN ID(f) as id
            UNION
            MATCH (m:Method)
            WHERE m.name = $name OR m.qualified_name = $name OR m.qualified_name ENDS WITH $name
            RETURN ID(m) as id
            """

            records = self.connector.run_query(
                query, parameters={"name": entity_name}, fetch_all=True
            )

            results = [str(record["id"]) for record in records]

        elif entity_type == "module":
            query = """
            MATCH (f:File)
            WHERE f.path = $name OR f.path ENDS WITH $name OR replace(f.path, '/', '.') CONTAINS $name
            RETURN ID(f) as id
            """

            records = self.connector.run_query(
                query, parameters={"name": entity_name}, fetch_all=True
            )

            results = [str(record["id"]) for record in records]

        # Cache the results
        self.entity_cache[cache_key] = results

        return results

    def _link_by_location(
        self, entity: DocumentationEntity
    ) -> list[DocumentationRelationship]:
        """Link a documentation entity to code entities based on its location.

        This is used for docstrings to link them to their containing entities.

        Args:
            entity: Documentation entity to link

        Returns:
            List of relationships
        """
        relationships = []

        # Check if the entity has metadata about its owner
        owner_type = entity.metadata.get("owner_type")
        owner_name = entity.metadata.get("owner_name")

        if not owner_type or not owner_name:
            return relationships

        # Find code entities matching the owner
        code_entities = []

        if owner_type == "function":
            query = """
            MATCH (f:Function)
            WHERE f.name = $name AND f.path = $path
            RETURN ID(f) as id
            """

            records = self.connector.run_query(
                query,
                parameters={"name": owner_name, "path": entity.file_path},
                fetch_all=True,
            )

            code_entities = [str(record["id"]) for record in records]

        elif owner_type == "method":
            query = """
            MATCH (m:Method)
            WHERE m.name = $name AND m.path = $path
            RETURN ID(m) as id
            """

            records = self.connector.run_query(
                query,
                parameters={"name": owner_name, "path": entity.file_path},
                fetch_all=True,
            )

            code_entities = [str(record["id"]) for record in records]

        elif owner_type == "class":
            query = """
            MATCH (c:Class)
            WHERE c.name = $name AND c.path = $path
            RETURN ID(c) as id
            """

            records = self.connector.run_query(
                query,
                parameters={"name": owner_name, "path": entity.file_path},
                fetch_all=True,
            )

            code_entities = [str(record["id"]) for record in records]

        elif owner_type == "module":
            query = """
            MATCH (f:File)
            WHERE f.path = $path
            RETURN ID(f) as id
            """

            records = self.connector.run_query(
                query, parameters={"path": entity.file_path}, fetch_all=True
            )

            code_entities = [str(record["id"]) for record in records]

        # Create relationships for each match
        for code_id in code_entities:
            relationship = DocumentationRelationship(
                type=RelationType.DESCRIBES,
                source_id=entity.id,
                target_id=code_id,
                properties={"owner_type": owner_type, "owner_name": owner_name},
            )
            relationships.append(relationship)

        return relationships
