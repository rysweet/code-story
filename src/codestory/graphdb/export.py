"""Export functionality for the graph database module."""

import csv
import json
from pathlib import Path
from typing import Any

from .exceptions import ExportError
from .neo4j_connector import Neo4jConnector


def export_to_json(
    connector: Neo4jConnector,
    output_path: str | Path,
    query: str,
    params: dict[str, Any] | None = None,
    pretty: bool = False,
) -> str:
    """
    Export query results to a JSON file.

    Args:
        connector: Neo4jConnector instance
        output_path: Path to the output JSON file
        query: Cypher query to execute
        params: Query parameters
        pretty: Whether to format the JSON output with indentation

    Returns:
        Path to the created JSON file

    Raises:
        ExportError: If the export operation fails
    """
    try:
        # Execute query
        results = connector.execute_query(query, params)

        # Convert to string
        indent = 2 if pretty else None
        json_data = json.dumps(results, indent=indent)

        # Write to file
        with open(output_path, "w") as f:
            f.write(json_data)

        return str(output_path)
    except Exception as e:
        raise ExportError(f"Failed to export data to JSON: {e!s}") from e


def export_to_csv(
    connector: Neo4jConnector,
    output_path: str | Path,
    query: str,
    params: dict[str, Any] | None = None,
    delimiter: str = ",",
    include_headers: bool = True,
) -> str:
    """
    Export query results to a CSV file.

    Args:
        connector: Neo4jConnector instance
        output_path: Path to the output CSV file
        query: Cypher query to execute
        params: Query parameters
        delimiter: CSV delimiter character
        include_headers: Whether to include header row

    Returns:
        Path to the created CSV file

    Raises:
        ExportError: If the export operation fails
    """
    try:
        # Execute query
        results = connector.execute_query(query, params)

        if not results:
            # Create empty file with headers if needed
            with open(output_path, "w") as f:
                f.write("")
            return str(output_path)

        # Get headers from first result
        headers = list(results[0].keys())

        # Write to CSV
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers, delimiter=delimiter)

            if include_headers:
                writer.writeheader()

            writer.writerows(results)

        return str(output_path)
    except Exception as e:
        raise ExportError(f"Failed to export data to CSV: {e!s}") from e


def export_graph_data(
    connector: Neo4jConnector, output_dir: str | Path, file_format: str = "json"
) -> dict[str, str]:
    """
    Export complete graph data (nodes and relationships) to files.

    Args:
        connector: Neo4jConnector instance
        output_dir: Directory to store export files
        file_format: Export format ('json' or 'csv')

    Returns:
        Dictionary mapping export type to file path

    Raises:
        ExportError: If the export operation fails
    """
    export_dir = Path(output_dir)
    if not export_dir.exists():
        export_dir.mkdir(parents=True)

    export_files = {}

    try:
        # Export nodes
        nodes_query = "MATCH (n) RETURN n"
        nodes_file = export_dir / f"nodes.{file_format}"

        if file_format.lower() == "json":
            export_to_json(connector, nodes_file, nodes_query)
        elif file_format.lower() == "csv":
            export_to_csv(connector, nodes_file, nodes_query)
        else:
            raise ExportError(f"Unsupported export format: {file_format}")

        export_files["nodes"] = str(nodes_file)

        # Export relationships
        relationships_query = "MATCH ()-[r]->() RETURN r"
        relationships_file = export_dir / f"relationships.{file_format}"

        if file_format.lower() == "json":
            export_to_json(connector, relationships_file, relationships_query)
        elif file_format.lower() == "csv":
            export_to_csv(connector, relationships_file, relationships_query)

        export_files["relationships"] = str(relationships_file)

        return export_files
    except Exception as e:
        raise ExportError(f"Failed to export graph data: {e!s}") from e


def export_cypher_script(
    connector: Neo4jConnector, output_path: str | Path
) -> str:
    """
    Export database as a Cypher script that can recreate the graph.

    Args:
        connector: Neo4jConnector instance
        output_path: Path to the output Cypher script

    Returns:
        Path to the created Cypher script

    Raises:
        ExportError: If the export operation fails
    """
    try:
        # Get all nodes
        nodes = connector.execute_query("MATCH (n) RETURN n")

        # Get all relationships
        relationships = connector.execute_query(
            "MATCH ()-[r]->() RETURN r, startNode(r) as source, endNode(r) as target"
        )

        # Create Cypher script
        with open(output_path, "w") as f:
            # Write header
            f.write("// Neo4j database export\n")
            f.write("// Generated by CodeStory\n\n")

            # Clear existing data
            f.write("// Clear existing data\n")
            f.write("MATCH (n) DETACH DELETE n;\n\n")

            # Create nodes
            f.write("// Create nodes\n")
            for node_data in nodes:
                node = node_data["n"]
                labels = ":".join(node.get("labels", []))

                properties = {}
                for key, value in node.get("properties", {}).items():
                    # Skip null values
                    if value is not None:
                        properties[key] = value

                properties_str = json.dumps(properties)
                f.write(f"CREATE (:{labels} {properties_str});\n")

            f.write("\n// Create relationships\n")
            for rel_data in relationships:
                rel = rel_data["r"]
                source = rel_data["source"]
                target = rel_data["target"]

                source_labels = ":".join(source.get("labels", []))
                target_labels = ":".join(target.get("labels", []))

                # Get identifying properties for source and target
                source_props = {}
                for key, value in source.get("properties", {}).items():
                    if value is not None:
                        source_props[key] = value

                target_props = {}
                for key, value in target.get("properties", {}).items():
                    if value is not None:
                        target_props[key] = value

                source_props_str = json.dumps(source_props)
                target_props_str = json.dumps(target_props)

                # Relationship properties
                rel_props = {}
                for key, value in rel.get("properties", {}).items():
                    if value is not None:
                        rel_props[key] = value

                rel_props_str = json.dumps(rel_props)
                rel_type = rel.get("type", "")

                # Create relationship
                f.write(f"MATCH (a:{source_labels}), (b:{target_labels})\n")
                f.write(f"WHERE a = {source_props_str} AND b = {target_props_str}\n")
                f.write(f"CREATE (a)-[:{rel_type} {rel_props_str}]->(b);\n\n")

        return str(output_path)
    except Exception as e:
        raise ExportError(f"Failed to export Cypher script: {e!s}") from e
