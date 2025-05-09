"""Serialization utilities for the MCP Adapter.

This module provides functions for serializing Neo4j nodes and relationships
to formats suitable for MCP responses.
"""

from typing import Any, Dict, List, Optional, Set, Union

from neo4j.graph import Node, Relationship


class NodeSerializer:
    """Serializer for Neo4j nodes.
    
    This class provides methods for serializing Neo4j nodes to dictionaries
    suitable for MCP responses.
    """
    
    @staticmethod
    def to_dict(
        node: Node, 
        score: Optional[float] = None,
        include_properties: Optional[List[str]] = None,
        exclude_properties: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Serialize a Neo4j node to a dictionary.
        
        Args:
            node: Neo4j node to serialize
            score: Optional relevance score
            include_properties: Optional list of properties to include
            exclude_properties: Optional list of properties to exclude
            
        Returns:
            Serialized node as a dictionary
        """
        # Start with basic identification
        result = {
            "id": str(node.id),
            "type": node.labels[0] if node.labels else "Unknown",
            "name": node.get("name", node.get("id", f"node-{node.id}")),
        }
        
        # Add path if available
        if "path" in node:
            result["path"] = node["path"]
            
        # Add content if available and not explicitly excluded
        if "content" in node and (not exclude_properties or "content" not in exclude_properties):
            if not include_properties or "content" in include_properties:
                result["content"] = node["content"]
        
        # Add score if provided
        if score is not None:
            result["score"] = score
            
        # Process properties according to include/exclude lists
        properties = {}
        for key, value in node.items():
            # Skip already handled properties
            if key in ("name", "path", "content"):
                continue
                
            # Apply include/exclude filters
            if include_properties and key not in include_properties:
                continue
            if exclude_properties and key in exclude_properties:
                continue
                
            # Add property to result
            properties[key] = value
            
        result["properties"] = properties
        
        return result
    
    @staticmethod
    def to_mcp_result(
        nodes: List[Union[Node, tuple[Node, float]]],
        include_properties: Optional[List[str]] = None,
        exclude_properties: Optional[List[str]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Serialize a list of Neo4j nodes to an MCP result format.
        
        Args:
            nodes: List of Neo4j nodes or tuples of (node, score)
            include_properties: Optional list of properties to include
            exclude_properties: Optional list of properties to exclude
            
        Returns:
            MCP result dictionary with matches array
        """
        matches = []
        
        for item in nodes:
            if isinstance(item, tuple):
                node, score = item
                matches.append(
                    NodeSerializer.to_dict(
                        node, 
                        score, 
                        include_properties, 
                        exclude_properties
                    )
                )
            else:
                matches.append(
                    NodeSerializer.to_dict(
                        item, 
                        None, 
                        include_properties, 
                        exclude_properties
                    )
                )
                
        return {"matches": matches}


class RelationshipSerializer:
    """Serializer for Neo4j relationships.
    
    This class provides methods for serializing Neo4j relationships to dictionaries
    suitable for MCP responses.
    """
    
    @staticmethod
    def to_dict(
        relationship: Relationship,
        include_properties: Optional[List[str]] = None,
        exclude_properties: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Serialize a Neo4j relationship to a dictionary.
        
        Args:
            relationship: Neo4j relationship to serialize
            include_properties: Optional list of properties to include
            exclude_properties: Optional list of properties to exclude
            
        Returns:
            Serialized relationship as a dictionary
        """
        # Start with basic identification
        result = {
            "id": str(relationship.id),
            "type": relationship.type,
            "start_node_id": str(relationship.start_node.id),
            "end_node_id": str(relationship.end_node.id),
        }
        
        # Process properties according to include/exclude lists
        properties = {}
        for key, value in relationship.items():
            # Apply include/exclude filters
            if include_properties and key not in include_properties:
                continue
            if exclude_properties and key in exclude_properties:
                continue
                
            # Add property to result
            properties[key] = value
            
        result["properties"] = properties
        
        return result
    
    @staticmethod
    def to_mcp_path_result(
        paths: List[List[Union[Node, Relationship]]],
        include_node_properties: Optional[List[str]] = None,
        exclude_node_properties: Optional[List[str]] = None,
        include_rel_properties: Optional[List[str]] = None,
        exclude_rel_properties: Optional[List[str]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Serialize a list of paths to an MCP result format.
        
        A path is a list of alternating nodes and relationships.
        
        Args:
            paths: List of paths (each path is a list of alternating nodes and relationships)
            include_node_properties: Optional list of node properties to include
            exclude_node_properties: Optional list of node properties to exclude
            include_rel_properties: Optional list of relationship properties to include
            exclude_rel_properties: Optional list of relationship properties to exclude
            
        Returns:
            MCP result dictionary with paths array
        """
        result_paths = []
        
        for path in paths:
            path_elements = []
            
            for i, element in enumerate(path):
                if i % 2 == 0:  # Node (even indices)
                    path_elements.append({
                        "element_type": "node",
                        **NodeSerializer.to_dict(
                            element, 
                            None, 
                            include_node_properties, 
                            exclude_node_properties
                        )
                    })
                else:  # Relationship (odd indices)
                    path_elements.append({
                        "element_type": "relationship",
                        **RelationshipSerializer.to_dict(
                            element,
                            include_rel_properties,
                            exclude_rel_properties
                        )
                    })
            
            result_paths.append({
                "elements": path_elements
            })
        
        return {"paths": result_paths}