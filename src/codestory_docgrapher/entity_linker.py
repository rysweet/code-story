from typing import Any, Dict, List, Tuple

'Entity linker for linking documentation entities to code entities.\n\nThis module provides functionality for linking documentation entities to code\nentities in the Neo4j database.\n'
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

    def __init__(self, connector: Neo4jConnector, repository_path: str) -> None:
        """Initialize the entity linker.

        Args:
            connector: Neo4j database connector
            repository_path: Path to the repository
        """
        self.connector = connector
        self.repository_path = repository_path
        self.path_matcher = PathMatcher(connector, repository_path)
        self.file_ref_pattern = re.compile(r'(?:^|[^\w/])(\w+\.\w+)(?:$|[^\w])')
        self.class_ref_pattern = re.compile(r'(?:^|[^\w/])([A-Z]\w+)(?:$|[^\w])')
        self.function_ref_pattern = re.compile(r'(?:^|[^\w/])(\w+\(\))(?:$|[^\w])')
        self.module_ref_pattern = re.compile(r'(?:^|[^\w/])([\w.]+)(?:$|[^\w])')
        self.entity_cache: Dict[str, List[str]] = {}

    def link_entities(self, entities: List[DocumentationEntity]) -> List[DocumentationRelationship]:
        """Link documentation entities to code entities.

        Args:
            entities: List of documentation entities

        Returns:
            List of relationships between documentation and code entities
        """
        relationships: List[DocumentationRelationship] = []
        for entity in entities:
            entity_rels = self._link_entity(entity)
            relationships.extend(entity_rels)
        logger.info(f'Created {len(relationships)} relationships between documentation and code entities')
        return relationships

    def _link_entity(self, entity: DocumentationEntity) -> List[DocumentationRelationship]:
        """Link a documentation entity to code entities.

        Args:
            entity: Documentation entity to link

        Returns:
            List of relationships
        """
        relationships: List[DocumentationRelationship] = []
        if entity.referenced_code:
            for code_id in entity.referenced_code:
                relationship = DocumentationRelationship(type=RelationType.DESCRIBES, source_id=entity.id, target_id=code_id)
                relationships.append(relationship)
        content_refs = self._extract_code_references(entity.content)
        for code_type, code_name in content_refs:
            code_ids = self._find_code_entities(code_type, code_name)
            for code_id in code_ids:
                relationship = DocumentationRelationship(type=RelationType.REFERENCES, source_id=entity.id, target_id=code_id, properties={'reference_type': code_type, 'reference_name': code_name})
                relationships.append(relationship)
        location_rels = self._link_by_location(entity)
        relationships.extend(location_rels)
        return relationships

    def _extract_code_references(self, content: str) -> List[Tuple[str, str]]:
        """Extract references to code entities from text content.

        Args:
            content: Text content to analyze

        Returns:
            List of (entity_type, entity_name) tuples
        """
        references: List[Tuple[str, str]] = []
        for match in self.file_ref_pattern.finditer(content):
            ref = match.group(1)
            if self._is_likely_file(ref):
                references.append(('file', ref))
        for match in self.class_ref_pattern.finditer(content):
            ref = match.group(1)
            if self._is_likely_class(ref):
                references.append(('class', ref))
        for match in self.function_ref_pattern.finditer(content):
            ref = match.group(1).rstrip('()')
            references.append(('function', ref))
        for match in self.module_ref_pattern.finditer(content):
            ref = match.group(1)
            if '.' in ref and self._is_likely_module(ref):
                references.append(('module', ref))
        return references

    def _is_likely_file(self, name: str) -> bool:
        """Check if a name is likely to be a file reference.

        Args:
            name: Name to check

        Returns:
            True if the name is likely a file reference, False otherwise
        """
        return '.' in name and (not name.startswith('.'))

    def _is_likely_class(self, name: str) -> bool:
        """Check if a name is likely to be a class reference.

        Args:
            name: Name to check

        Returns:
            True if the name is likely a class reference, False otherwise
        """
        return name[0].isupper() and '.' not in name and (len(name) > 1)

    def _is_likely_module(self, name: str) -> bool:
        """Check if a name is likely to be a module reference.

        Args:
            name: Name to check

        Returns:
            True if the name is likely a module reference, False otherwise
        """
        return '.' in name and ' ' not in name

    def _find_code_entities(self, entity_type: str, entity_name: str) -> List[str]:
        """Find code entities matching a reference.

        Args:
            entity_type: Type of entity to find
            entity_name: Name of entity to find

        Returns:
            List of Neo4j IDs for matching entities
        """
        cache_key = f'{entity_type}:{entity_name}'
        if cache_key in self.entity_cache:
            return self.entity_cache[cache_key]
        results: List[str] = []
        if entity_type == 'file':
            query = (
                '\n            MATCH (f:File)\n            WHERE f.name = $name OR f.path = $name OR f.path ENDS WITH $name\n            RETURN ID(f) as id\n            '
            )
            records = self.connector.execute_query(query, params={'name': entity_name})
            results = [str(record['id']) for record in records]
        elif entity_type == 'class':
            query = (
                '\n            MATCH (c:Class)\n            WHERE c.name = $name OR c.qualified_name = $name OR c.qualified_name ENDS WITH $name\n            RETURN ID(c) as id\n            '
            )
            records = self.connector.execute_query(query, params={'name': entity_name})
            results = [str(record['id']) for record in records]
        elif entity_type == 'function':
            query = (
                '\n            MATCH (f:Function)\n            WHERE f.name = $name OR f.qualified_name = $name OR f.qualified_name ENDS WITH $name\n            RETURN ID(f) as id\n            UNION\n            MATCH (m:Method)\n            WHERE m.name = $name OR m.qualified_name = $name OR m.qualified_name ENDS WITH $name\n            RETURN ID(m) as id\n            '
            )
            records = self.connector.execute_query(query, params={'name': entity_name})
            results = [str(record['id']) for record in records]
        elif entity_type == 'module':
            query = (
                "\n            MATCH (f:File)\n            WHERE f.path = $name OR f.path ENDS WITH $name OR \n                  replace(f.path, '/', '.') CONTAINS $name\n            RETURN ID(f) as id\n            "
            )
            records = self.connector.execute_query(query, params={'name': entity_name})
            results = [str(record['id']) for record in records]
        self.entity_cache[cache_key] = results
        return results

    def _link_by_location(self, entity: DocumentationEntity) -> List[DocumentationRelationship]:
        """Link a documentation entity to code entities based on its location.

        This is used for docstrings to link them to their containing entities.

        Args:
            entity: Documentation entity to link

        Returns:
            List of relationships
        """
        relationships: List[DocumentationRelationship] = []
        owner_type = entity.metadata.get('owner_type')
        owner_name = entity.metadata.get('owner_name')
        if not owner_type or not owner_name:
            return relationships
        code_entities: List[str] = []
        if owner_type == 'function':
            query = (
                '\n            MATCH (f:Function)\n            WHERE f.name = $name AND f.path = $path\n            RETURN ID(f) as id\n            '
            )
            records = self.connector.execute_query(query, params={'name': owner_name, 'path': entity.file_path})
            code_entities = [str(record['id']) for record in records]
        elif owner_type == 'method':
            query = (
                '\n            MATCH (m:Method)\n            WHERE m.name = $name AND m.path = $path\n            RETURN ID(m) as id\n            '
            )
            records = self.connector.execute_query(query, params={'name': owner_name, 'path': entity.file_path})
            code_entities = [str(record['id']) for record in records]
        elif owner_type == 'class':
            query = (
                '\n            MATCH (c:Class)\n            WHERE c.name = $name AND c.path = $path\n            RETURN ID(c) as id\n            '
            )
            records = self.connector.execute_query(query, params={'name': owner_name, 'path': entity.file_path})
            code_entities = [str(record['id']) for record in records]
        elif owner_type == 'module':
            query = (
                '\n            MATCH (f:File)\n            WHERE f.path = $path\n            RETURN ID(f) as id\n            '
            )
            records = self.connector.execute_query(query, params={'path': entity.file_path})
            code_entities = [str(record['id']) for record in records]
        for code_id in code_entities:
            relationship = DocumentationRelationship(
                type=RelationType.DESCRIBES,
                source_id=entity.id,
                target_id=code_id,
                properties={'owner_type': owner_type, 'owner_name': owner_name},
            )
            relationships.append(relationship)
        return relationships