"""Graph service for Code Story Service.

This module provides application-level services for interacting with
the graph database, including query execution, vector search, and
path finding, as well as visualization generation.
"""

import json
import logging
from typing import Any

from fastapi import Depends, HTTPException, status

from ..domain.graph import (
    AskAnswer,
    AskRequest,
    CypherQuery,
    DatabaseClearRequest,
    DatabaseClearResponse,
    PathRequest,
    PathResult,
    QueryResult,
    VectorQuery,
    VectorResult,
    VisualizationRequest,
)
from ..infrastructure.neo4j_adapter import Neo4jAdapter, get_neo4j_adapter
from ..infrastructure.openai_adapter import OpenAIAdapter, get_openai_adapter

# Set up logging
logger = logging.getLogger(__name__)


class GraphService:
    """Application service for graph operations.

    This service orchestrates interactions with the graph database,
    providing high-level methods for the API layer.
    """

    def __init__(self, neo4j_adapter: Neo4jAdapter, openai_adapter: OpenAIAdapter) -> None:
        """Initialize the graph service.

        Args:
            neo4j_adapter: Neo4j adapter instance
            openai_adapter: OpenAI adapter instance
        """
        self.neo4j = neo4j_adapter
        self.openai = openai_adapter

    async def execute_cypher_query(self, query: CypherQuery) -> QueryResult:
        """Execute a Cypher query against the graph database.

        Args:
            query: Cypher query details

        Returns:
            QueryResult with the results of the query

        Raises:
            HTTPException: If the query execution fails
        """
        try:
            logger.info(f"Executing Cypher query: {query.query[:100]}...")
            result = await self.neo4j.execute_cypher_query(query)
            logger.info(f"Query returned {result.row_count} rows")
            return result
        except Exception as e:
            logger.error(f"Error executing Cypher query: {e!s}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error executing query: {e!s}",
            ) from e

    async def execute_vector_search(self, query: VectorQuery) -> VectorResult:
        """Execute a vector similarity search.

        Args:
            query: Vector search query

        Returns:
            VectorResult with the search results

        Raises:
            HTTPException: If the search fails
        """
        try:
            # First, generate embedding for the query text
            logger.info(f"Generating embedding for vector search: {query.query}")
            embeddings = await self.openai.create_embeddings([query.query])

            if not embeddings or len(embeddings) == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate embedding for query",
                )

            # Execute the search with the generated embedding
            logger.info(f"Executing vector search for entity type: {query.entity_type}")
            result = await self.neo4j.execute_vector_search(query, embeddings[0])
            logger.info(f"Vector search returned {result.total_count} results")
            return result
        except Exception as e:
            logger.error(f"Error executing vector search: {e!s}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error executing vector search: {e!s}",
            ) from e

    async def find_path(self, path_request: PathRequest) -> PathResult:
        """Find paths between nodes in the graph.

        Args:
            path_request: Path finding request

        Returns:
            PathResult with the found paths

        Raises:
            HTTPException: If the path finding fails
        """
        try:
            logger.info(
                f"Finding paths from {path_request.start_node_id} to "
                f"{path_request.end_node_id} using algorithm {path_request.algorithm}"
            )
            result = await self.neo4j.find_path(path_request)
            logger.info(f"Path finding returned {result.total_paths_found} paths")
            return result
        except Exception as e:
            logger.error(f"Error finding paths: {e!s}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error finding paths: {e!s}",
            ) from e

    async def answer_question(self, request: AskRequest) -> AskAnswer:
        """Answer a natural language question about the codebase.

        Args:
            request: The question and parameters

        Returns:
            AskAnswer with the generated answer

        Raises:
            HTTPException: If answering fails
        """
        try:
            # First, generate embedding for the question
            logger.info(f"Generating embedding for question: {request.question}")
            embeddings = await self.openai.create_embeddings([request.question])

            if not embeddings or len(embeddings) == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate embedding for question",
                )

            # Search for relevant context in the graph
            context_size = request.context_size or 5

            # Create a query to find relevant nodes
            vector_query = VectorQuery(
                query=request.question,
                entity_type=None,  # Search across all entity types
                limit=context_size,
                min_score=0.5,  # Minimum relevance threshold
            )

            # Execute the search
            search_result = await self.neo4j.execute_vector_search(vector_query, embeddings[0])

            # Retrieve full content for each context item
            context_items: list[Any] = []
            for result in search_result.results:
                # Fetch the full node with all properties
                node_query = CypherQuery(
                    query="MATCH (n) WHERE elementId(n) = $id RETURN n",
                    parameters={"id": result.id},
                    query_type="read",  # type: ignore[arg-type]
                )

                node_result = await self.neo4j.execute_cypher_query(node_query)

                if node_result.rows and len(node_result.rows) > 0 and len(node_result.rows[0]) > 0:
                    node = node_result.rows[0][0]  # First column of first row
                    node["score"] = result.score  # Add the relevance score
                    context_items.append(node)

            # Generate the answer using the OpenAI adapter
            logger.info(f"Generating answer using {len(context_items)} context items")
            answer = await self.openai.answer_question(request, context_items)  # type: ignore[attr-defined]

            logger.info("Answer generated successfully")
            return answer  # type: ignore[no-any-return]
        except Exception as e:
            logger.error(f"Error answering question: {e!s}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error answering question: {e!s}",
            ) from e

    async def generate_visualization(self, request: VisualizationRequest) -> str:
        """Generate an interactive HTML visualization of the code graph.

        Args:
            request: Visualization parameters

        Returns:
            HTML content for the visualization

        Raises:
            HTTPException: If visualization generation fails
        """
        try:
            logger.info(f"Generating {request.type} visualization with {request.theme} theme")

            # Get graph data from Neo4j based on the request parameters
            graph_data = await self._get_graph_data_for_visualization(request)

            # Generate HTML
            html_content = self._generate_visualization_html(graph_data, request)

            logger.info("Visualization generated successfully")
            return html_content
        except Exception as e:
            logger.error(f"Error generating visualization: {e!s}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating visualization: {e!s}",
            ) from e

    async def _get_graph_data_for_visualization(
        self, request: VisualizationRequest
    ) -> dict[str, Any]:
        """Get graph data from Neo4j for visualization.

        Args:
            request: Visualization parameters

        Returns:
            Graph data dictionary with nodes and links
        """
        # Default query to get a limited set of nodes and relationships
        cypher_query = """
        MATCH (n)
        WHERE n.name IS NOT NULL  // Filter out nodes without names
        WITH n LIMIT $max_nodes
        OPTIONAL MATCH (n)-[r]->(m)
        WHERE m.name IS NOT NULL  // Filter out relationships to unnamed nodes
        RETURN 
          COLLECT(DISTINCT {
            id: toString(id(n)), 
            label: labels(n)[0], 
            properties: properties(n)
          }) AS nodes,
          COLLECT(DISTINCT {
            id: toString(id(r)), 
            source: toString(id(n)), 
            target: toString(id(m)), 
            type: type(r), 
            properties: properties(r)
          }) AS relationships
        """

        params = {"max_nodes": request.filter.max_nodes if request.filter else 100}

        # Custom query if focus_node_id is provided
        if request.focus_node_id:
            cypher_query = """
            MATCH (focus_node) 
            WHERE elementId(focus_node) = $focus_node_id
            OPTIONAL MATCH path = (focus_node)-[*1..$depth]-(related)
            WHERE related.name IS NOT NULL  // Filter out unnamed nodes
            WITH focus_node, collect(path) as paths
            // Unwind paths to get all nodes and relationships
            UNWIND paths as p
            WITH focus_node, p, nodes(p) as path_nodes, relationships(p) as path_rels
            // Collect all nodes including focus_node
            WITH 
              collect(DISTINCT focus_node) + 
              [node IN path_nodes WHERE node <> focus_node | node] as all_nodes,
              collect(DISTINCT path_rels) as all_rels
            UNWIND all_nodes as node
            WITH collect(DISTINCT {
              id: toString(id(node)), 
              label: labels(node)[0], 
              properties: properties(node), 
              is_focus: node = focus_node
            }) as nodes, 
            all_rels
            UNWIND all_rels as rel
            RETURN 
              nodes, 
              collect(DISTINCT {
                id: toString(id(rel)), 
                source: toString(id(startNode(rel))), 
                target: toString(id(endNode(rel))), 
                type: type(rel), 
                properties: properties(rel)
              }) as relationships
            """
            params["focus_node_id"] = request.focus_node_id  # type: ignore  # TODO: Fix type compatibility
            params["depth"] = request.depth

        # Apply node type filtering if specified
        if request.filter and request.filter.node_types:
            node_types = request.filter.node_types
            cypher_query = cypher_query.replace(
                "WHERE n.name IS NOT NULL",
                "WHERE n.name IS NOT NULL AND labels(n)[0] IN $node_types",
            )
            params["node_types"] = node_types  # type: ignore  # TODO: Fix type compatibility

        # Apply search query filtering if specified
        if request.filter and request.filter.search_query:
            search_query = request.filter.search_query
            # Add text search condition
            cypher_query = cypher_query.replace(
                "WHERE n.name IS NOT NULL",
                "WHERE n.name IS NOT NULL AND "
                "(n.name CONTAINS $search_query OR n.path CONTAINS $search_query)",
            )
            params["search_query"] = search_query  # type: ignore  # TODO: Fix type compatibility

        # Include/exclude orphan nodes (nodes with no relationships)
        if request.filter and not request.filter.include_orphans:
            cypher_query = cypher_query.replace(
                "MATCH (n)",
                "MATCH (n) WHERE EXISTS((n)--())",  # Only match nodes with connections
            )

        # Execute query
        query = CypherQuery(
            query=cypher_query,
            parameters=params,
            query_type="read",  # type: ignore[arg-type]
        )
        result = await self.neo4j.execute_cypher_query(query)

        if not result.rows or len(result.rows) == 0:
            # Return empty graph data if no results
            return {"nodes": [], "links": []}

        # Process result
        nodes = result.rows[0][0]  # First row, first column (nodes)
        relationships = result.rows[0][1]  # First row, second column (relationships)

        # If we need to limit further due to max_nodes constraint
        if request.filter and request.filter.max_nodes < len(nodes):
            nodes = nodes[: request.filter.max_nodes]
            # Filter relationships to only include those between our nodes
            node_ids = {node["id"] for node in nodes}
            relationships = [
                rel
                for rel in relationships
                if rel["source"] in node_ids and rel["target"] in node_ids
            ]

        # Convert to standard graph data format
        graph_data = {
            "nodes": [
                {
                    "id": node["id"],
                    "label": node["label"],
                    "name": node["properties"].get("name", "Unnamed"),
                    "type": node["label"],
                    "properties": node["properties"],
                    "is_focus": node.get("is_focus", False),
                }
                for node in nodes
            ],
            "links": [
                {
                    "id": rel["id"],
                    "source": rel["source"],
                    "target": rel["target"],
                    "type": rel["type"],
                    "properties": rel["properties"],
                }
                for rel in relationships
            ],
        }

        return graph_data

    def _generate_visualization_html(
        self, graph_data: dict[str, Any], request: VisualizationRequest
    ) -> str:
        """Generate HTML for graph visualization.

        Args:
            graph_data: Graph data with nodes and links
            request: Visualization parameters

        Returns:
            HTML content
        """
        # Get visualization type
        viz_type = request.type.value

        # Get theme
        theme = request.theme.value
        if theme == "auto":
            # Default to dark theme if auto
            theme = "dark"

        # Set visualization title based on focus node if available
        title = "Code Story Graph Visualization"
        if request.focus_node_id:
            for node in graph_data["nodes"]:
                if node.get("is_focus", False):
                    title = f"Code Story Graph: {node.get('name', 'Unknown')}"
                    break

        # Filter and format node properties for visualization
        for node in graph_data["nodes"]:
            # Only keep essential properties for visualization
            clean_props: dict[Any, Any] = {}
            if "name" in node["properties"]:
                clean_props["name"] = node["properties"]["name"]
            if "path" in node["properties"]:
                clean_props["path"] = node["properties"]["path"]
            if "summary" in node["properties"]:
                # Truncate long summaries
                summary = node["properties"]["summary"]
                if summary and len(summary) > 100:
                    clean_props["summary"] = summary[:100] + "..."
                else:
                    clean_props["summary"] = summary

            # Add any other interesting properties, but limit to essentials
            for key, value in node["properties"].items():
                if key not in ["name", "path", "summary", "embedding"] and isinstance(
                    value, str | int | float | bool
                ):
                    if isinstance(value, str) and len(value) > 100:
                        clean_props[key] = value[:100] + "..."
                    else:
                        clean_props[key] = value

            node["properties"] = clean_props

        # Generate JavaScript data initialization
        js_data = f"""
        const graphData = {json.dumps(graph_data)};
        const vizType = "{viz_type}";
        const theme = "{theme}";
        const title = "{title}";
        const maxNodes = {request.filter.max_nodes if request.filter else 100};
        const focusNodeId = {json.dumps(request.focus_node_id)};
        """

        # Basic template with D3.js for visualization
        html_template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <script src="https://d3js.org/d3.v7.min.js"></script>
            <style>
                :root {{
                    --bg-color: {bg_color};
                    --text-color: {text_color};
                    --node-color-file: #4285F4;
                    --node-color-directory: #0F9D58;
                    --node-color-function: #F4B400;
                    --node-color-class: #DB4437;
                    --node-color-module: #9C27B0;
                    --node-color-default: #757575;
                    --link-color: {link_color};
                    --focus-color: #FF5722;
                }}
                
                body {{
                    margin: 0;
                    overflow: hidden;
                    background-color: var(--bg-color);
                    color: var(--text-color);
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, 
                                 Helvetica, Arial, sans-serif;
                }}
                
                .container {{
                    display: flex;
                    height: 100vh;
                }}
                
                .sidebar {{
                    width: 300px;
                    padding: 20px;
                    overflow-y: auto;
                    border-right: 1px solid {border_color};
                }}
                
                .visualization {{
                    flex-grow: 1;
                    position: relative;
                }}
                
                svg {{
                    width: 100%;
                    height: 100%;
                }}
                
                .controls {{
                    position: absolute;
                    top: 20px;
                    right: 20px;
                    background-color: var(--bg-color);
                    padding: 10px;
                    border-radius: 5px;
                    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                }}
                
                .legend {{
                    margin-top: 20px;
                }}
                
                .legend-item {{
                    display: flex;
                    align-items: center;
                    margin-bottom: 8px;
                }}
                
                .legend-color {{
                    width: 16px;
                    height: 16px;
                    border-radius: 50%;
                    margin-right: 8px;
                }}
                
                .node {{
                    cursor: pointer;
                }}
                
                .link {{
                    stroke: var(--link-color);
                    stroke-opacity: 0.6;
                }}
                
                .node-label {{
                    font-size: 12px;
                    pointer-events: none;
                }}
                
                .search-box {{
                    margin-bottom: 20px;
                }}
                
                .search-box input {{
                    width: 100%;
                    padding: 8px;
                    border-radius: 4px;
                    border: 1px solid {border_color};
                    background-color: var(--bg-color);
                    color: var(--text-color);
                }}
                
                .node-details {{
                    padding-top: 20px;
                    border-top: 1px solid {border_color};
                }}
                
                .property {{
                    margin-bottom: 5px;
                }}
                
                .property-name {{
                    font-weight: bold;
                }}
                
                .expandable {{
                    cursor: pointer;
                    border: 2px dashed #FF5722;
                }}
                
                .tooltip {{
                    position: absolute;
                    padding: 10px;
                    background-color: var(--bg-color);
                    border: 1px solid {border_color};
                    border-radius: 5px;
                    pointer-events: none;
                    opacity: 0;
                    transition: opacity 0.3s;
                    max-width: 300px;
                    z-index: 1000;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="sidebar">
                    <h1>Code Story</h1>
                    <p>Interactive visualization of your codebase structure</p>
                    
                    <div class="search-box">
                        <input type="text" id="search" placeholder="Search nodes..." />
                    </div>
                    
                    <div class="legend">
                        <h3>Node Types</h3>
                        <div class="legend-item">
                            <div class="legend-color" 
                                 style="background-color: var(--node-color-file)"></div>
                            <div>File</div>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" 
                                 style="background-color: var(--node-color-directory)"></div>
                            <div>Directory</div>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" 
                                 style="background-color: var(--node-color-function)"></div>
                            <div>Function</div>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" 
                                 style="background-color: var(--node-color-class)"></div>
                            <div>Class</div>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" 
                                 style="background-color: var(--node-color-module)"></div>
                            <div>Module</div>
                        </div>
                    </div>
                    
                    <div class="node-details" id="node-details">
                        <h3>Node Details</h3>
                        <p>Click on a node to see details</p>
                    </div>
                </div>
                
                <div class="visualization">
                    <svg id="graph"></svg>
                    
                    <div class="controls">
                        <button id="zoom-in">+</button>
                        <button id="zoom-out">-</button>
                        <button id="reset">Reset</button>
                    </div>
                    
                    <div class="tooltip" id="tooltip"></div>
                </div>
            </div>
            
            <script>
                // Graph data from server
                {js_data}
                
                // Initialize visualization
                document.addEventListener('DOMContentLoaded', () => {{
                    // Visualization variables
                    let svg = d3.select('#graph');
                    let width = svg.node().parentElement.clientWidth;
                    let height = svg.node().parentElement.clientHeight;
                    let nodeRadius = 10;
                    let simulation;
                    let nodeElements;
                    let linkElements;
                    let textElements;
                    
                    // Color function for nodes based on type
                    function getNodeColor(node) {{
                        if (node.id === focusNodeId || node.is_focus) {{
                            return 'var(--focus-color)';
                        }}
                        
                        const type = node.type.toLowerCase();
                        if (type.includes('file')) return 'var(--node-color-file)';
                        if (type.includes('directory')) return 'var(--node-color-directory)';
                        if (type.includes('function')) return 'var(--node-color-function)';
                        if (type.includes('class')) return 'var(--node-color-class)';
                        if (type.includes('module')) return 'var(--node-color-module)';
                        return 'var(--node-color-default)';
                    }}
                    
                    // Node size based on connections
                    function getNodeSize(node) {{
                        let size = nodeRadius;
                        const links = graphData.links.filter(link => 
                            link.source === node.id || link.source.id === node.id || 
                            link.target === node.id || link.target.id === node.id
                        );
                        
                        if (links.length > 0) {{
                            size += Math.min(links.length * 2, 10);  // Cap the size increase
                        }}
                        
                        if (node.id === focusNodeId || node.is_focus) {{
                            size += 5;  // Make focus node larger
                        }}
                        
                        return size;
                    }}
                    
                    // Check if node is expandable
                    function isExpandable(node) {{
                        // A node is expandable if it's not a focus node and has properties 
                        // indicating more connections
                        return !node.is_focus && node.properties && 
                              (node.properties.has_children === true || 
                               node.properties.has_more_connections === true);
                    }}
                    
                    // Initialize the visualization
                    function initializeVisualization() {{
                        // Clear any existing visualization
                        svg.selectAll('*').remove();
                        
                        // Create zoom behavior
                        const zoom = d3.zoom()
                            .scaleExtent([0.1, 8])
                            .on('zoom', (event) => {{
                                container.attr('transform', event.transform);
                            }});
                        
                        svg.call(zoom);
                        
                        // Create container for the graph
                        const container = svg.append('g');
                        
                        // Add a border to make the visualization area more visible
                        svg.append('rect')
                            .attr('width', width)
                            .attr('height', height)
                            .attr('fill', 'none')
                            .attr('stroke', '{border_color}');
                        
                        // Create arrow markers for directed graphs
                        svg.append('defs').selectAll('marker')
                            .data(['end'])
                            .enter().append('marker')
                            .attr('id', d => d)
                            .attr('viewBox', '0 -5 10 10')
                            .attr('refX', 20)
                            .attr('refY', 0)
                            .attr('markerWidth', 6)
                            .attr('markerHeight', 6)
                            .attr('orient', 'auto')
                            .append('path')
                            .attr('fill', 'var(--link-color)')
                            .attr('d', 'M0,-5L10,0L0,5');
                        
                        // Create links, nodes, and labels
                        linkElements = container.append('g')
                            .selectAll('line')
                            .data(graphData.links)
                            .enter().append('line')
                            .attr('class', 'link')
                            .attr('stroke-width', 1)
                            .attr('marker-end', 'url(#end)');
                        
                        nodeElements = container.append('g')
                            .selectAll('circle')
                            .data(graphData.nodes)
                            .enter().append('circle')
                            .attr('class', 'node')
                            .attr('r', getNodeSize)
                            .attr('fill', getNodeColor)
                            .classed('expandable', isExpandable)
                            .call(d3.drag()
                                .on('start', dragStarted)
                                .on('drag', dragged)
                                .on('end', dragEnded));
                        
                        textElements = container.append('g')
                            .selectAll('text')
                            .data(graphData.nodes)
                            .enter().append('text')
                            .attr('class', 'node-label')
                            .attr('text-anchor', 'middle')
                            .attr('fill', 'var(--text-color)')
                            .text(d => d.name || d.label);
                        
                        // Setup force simulation
                        if (vizType === 'force') {{
                            simulation = d3.forceSimulation(graphData.nodes)
                                .force('charge', d3.forceManyBody().strength(-200))
                                .force('center', d3.forceCenter(width / 2, height / 2))
                                .force('link', d3.forceLink(graphData.links)
                                    .id(d => d.id)
                                    .distance(100))
                                .force('collision', d3.forceCollide().radius(30))
                                .on('tick', ticked);
                        }} else if (vizType === 'radial') {{
                            simulation = d3.forceSimulation(graphData.nodes)
                                .force('charge', d3.forceManyBody().strength(-200))
                                .force('center', d3.forceCenter(width / 2, height / 2))
                                .force('link', d3.forceLink(graphData.links)
                                    .id(d => d.id)
                                    .distance(100))
                                .force('radial', d3.forceRadial(200, width / 2, height / 2))
                                .force('collision', d3.forceCollide().radius(30))
                                .on('tick', ticked);
                        }} else if (vizType === 'hierarchy') {{
                            // Find root node (typically a directory or focus node)
                            let rootNode = graphData.nodes.find(n => n.is_focus) || 
                                          graphData.nodes.find(n => n.type === 'Directory') ||
                                          graphData.nodes[0];
                            
                            const hierarchyLinks = graphData.links.map(link => ({{
                                source: link.source.id || link.source,
                                target: link.target.id || link.target,
                                value: 1
                            }}));
                            
                            // Create a hierarchical layout
                            const root = d3.stratify()
                                .id(d => d.id)
                                .parentId(d => {{
                                    // Find a parent link
                                    const parentLink = hierarchyLinks.find(
                                        link => link.target === d.id
                                    );
                                    return parentLink ? parentLink.source : null;
                                }})
                                (graphData.nodes);
                            
                            // Apply tree layout
                            const treeLayout = d3.tree()
                                .size([width - 100, height - 100]);
                            
                            treeLayout(root);
                            
                            // Update node positions
                            root.descendants().forEach(node => {{
                                const dataNode = graphData.nodes.find(n => n.id === node.id);
                                if (dataNode) {{
                                    dataNode.x = node.x + 50;
                                    dataNode.y = node.y + 50;
                                }}
                            }});
                            
                            // Update the visualization
                            ticked();
                        }} else {{
                            // Default to force-directed for other types
                            simulation = d3.forceSimulation(graphData.nodes)
                                .force('charge', d3.forceManyBody().strength(-200))
                                .force('center', d3.forceCenter(width / 2, height / 2))
                                .force('link', d3.forceLink(graphData.links)
                                    .id(d => d.id)
                                    .distance(100))
                                .force('collision', d3.forceCollide().radius(30))
                                .on('tick', ticked);
                        }}
                        
                        // Setup node events
                        setupNodeEvents();
                        
                        // Setup controls
                        setupControls(zoom);
                        
                        // Setup search
                        setupSearch();
                    }}
                    
                    // Update visualization on each tick
                    function ticked() {{
                        linkElements
                            .attr('x1', d => d.source.x)
                            .attr('y1', d => d.source.y)
                            .attr('x2', d => d.target.x)
                            .attr('y2', d => d.target.y);
                        
                        nodeElements
                            .attr('cx', d => d.x)
                            .attr('cy', d => d.y);
                        
                        textElements
                            .attr('x', d => d.x)
                            .attr('y', d => d.y + getNodeSize(d) + 10);
                    }}
                    
                    // Drag functions
                    function dragStarted(event, d) {{
                        if (!event.active) simulation.alphaTarget(0.3).restart();
                        d.fx = d.x;
                        d.fy = d.y;
                    }}
                    
                    function dragged(event, d) {{
                        d.fx = event.x;
                        d.fy = event.y;
                    }}
                    
                    function dragEnded(event, d) {{
                        if (!event.active) simulation.alphaTarget(0);
                        d.fx = null;
                        d.fy = null;
                    }}
                    
                    // Setup node events (hover, click)
                    function setupNodeEvents() {{
                        const tooltip = d3.select('#tooltip');
                        
                        nodeElements
                            .on('mouseover', (event, d) => {{
                                // Highlight node and connected links
                                nodeElements.style('opacity', n => isConnected(d, n) ? 1 : 0.3);
                                linkElements.style('opacity', l => 
                                    l.source.id === d.id || l.target.id === d.id ? 1 : 0.1
                                );
                                textElements.style('opacity', n => isConnected(d, n) ? 1 : 0.3);
                                
                                // Show tooltip
                                tooltip
                                    .style('left', (event.pageX + 10) + 'px')
                                    .style('top', (event.pageY - 10) + 'px')
                                    .style('opacity', 0.9)
                                    .html(`
                                        <strong>${d.name || d.label}</strong><br>
                                        <span>Type: ${d.type}</span>
                                        ${d.properties.path ? 
                                            `<br><span>Path: ${d.properties.path}</span>` : ''}
                                    `);
                            }})
                            .on('mouseout', () => {{
                                // Reset highlights
                                nodeElements.style('opacity', 1);
                                linkElements.style('opacity', 0.6);
                                textElements.style('opacity', 1);
                                
                                // Hide tooltip
                                tooltip.style('opacity', 0);
                            }})
                            .on('click', (event, d) => {{
                                // Show node details
                                showNodeDetails(d);
                                
                                // Prevent event from propagating
                                event.stopPropagation();
                            }});
                    }}
                    
                    // Check if two nodes are connected
                    function isConnected(a, b) {{
                        return a === b ||
                            graphData.links.some(l => 
                                (l.source === a && l.target === b) || 
                                (l.source === b && l.target === a) ||
                                (l.source.id === a.id && l.target.id === b.id) || 
                                (l.source.id === b.id && l.target.id === a.id)
                            );
                    }}
                    
                    // Show node details in sidebar
                    function showNodeDetails(node) {{
                        const detailsDiv = document.getElementById('node-details');
                        
                        // Create details HTML
                        let detailsHTML = `
                            <h3>${node.name || node.label}</h3>
                            <div class="property">
                                <span class="property-name">Type:</span> ${node.type}
                            </div>
                        `;
                        
                        // Add other properties
                        for (const [key, value] of Object.entries(node.properties)) {{
                            if (key !== 'name' && key !== 'type') {{
                                detailsHTML += `
                                    <div class="property">
                                        <span class="property-name">${key}:</span> ${value}
                                    </div>
                                `;
                            }}
                        }}
                        
                        // Add connected nodes
                        const connectedNodes = graphData.links
                            .filter(l => l.source.id === node.id || l.source === node.id || 
                                         l.target.id === node.id || l.target === node.id)
                            .map(l => {{
                                const connectedId = (
                                    l.source.id === node.id || l.source === node.id
                                ) ? (l.target.id || l.target) : (l.source.id || l.source);
                                const connectedNode = graphData.nodes.find(
                                    n => n.id === connectedId
                                );
                                return {{
                                    node: connectedNode,
                                    relationship: l.type
                                }};
                            }});
                        
                        if (connectedNodes.length > 0) {{
                            detailsHTML += `<h4>Connected to:</h4>`;
                            connectedNodes.forEach(conn => {{
                                if (conn.node) {{
                                    detailsHTML += `
                                        <div class="property">
                                            <span class="property-name">${conn.relationship}:</span>
                                            ${conn.node.name || conn.node.label}
                                        </div>
                                    `;
                                }}
                            }});
                        }}
                        
                        // Update details div
                        detailsDiv.innerHTML = detailsHTML;
                    }}
                    
                    // Setup zoom/reset controls
                    function setupControls(zoom) {{
                        document.getElementById('zoom-in').addEventListener('click', () => {{
                            svg.transition().call(zoom.scaleBy, 1.5);
                        }});
                        
                        document.getElementById('zoom-out').addEventListener('click', () => {{
                            svg.transition().call(zoom.scaleBy, 0.75);
                        }});
                        
                        document.getElementById('reset').addEventListener('click', () => {{
                            svg.transition().call(zoom.transform, d3.zoomIdentity);
                        }});
                    }}
                    
                    // Setup search functionality
                    function setupSearch() {{
                        const searchInput = document.getElementById('search');
                        
                        searchInput.addEventListener('input', () => {{
                            const query = searchInput.value.toLowerCase();
                            
                            // If query is empty, reset all nodes
                            if (query === '') {{
                                nodeElements.style('opacity', 1);
                                textElements.style('opacity', 1);
                                linkElements.style('opacity', 0.6);
                                return;
                            }}
                            
                            // Highlight matching nodes
                            nodeElements.style('opacity', d => {{
                                const matchesSearch = 
                                    (d.name && d.name.toLowerCase().includes(query)) ||
                                    (d.label && d.label.toLowerCase().includes(query)) ||
                                    (d.properties.path && 
                                     d.properties.path.toLowerCase().includes(query));
                                
                                return matchesSearch ? 1 : 0.2;
                            }});
                            
                            // Highlight matching text
                            textElements.style('opacity', d => {{
                                const matchesSearch = 
                                    (d.name && d.name.toLowerCase().includes(query)) ||
                                    (d.label && d.label.toLowerCase().includes(query)) ||
                                    (d.properties.path && 
                                     d.properties.path.toLowerCase().includes(query));
                                
                                return matchesSearch ? 1 : 0.2;
                            }});
                            
                            // Dim all links
                            linkElements.style('opacity', 0.1);
                        }});
                    }}
                    
                    // Initialize the visualization when DOM is loaded
                    initializeVisualization();
                    
                    // Resize handler
                    window.addEventListener('resize', () => {{
                        width = svg.node().parentElement.clientWidth;
                        height = svg.node().parentElement.clientHeight;
                        
                        if (simulation) {{
                            simulation.force('center', d3.forceCenter(width / 2, height / 2));
                            simulation.alpha(0.3).restart();
                        }}
                    }});
                }});
            </script>
        </body>
        </html>
        """

        # Set color scheme based on theme
        color_scheme = {
            "light": {
                "bg_color": "#ffffff",
                "text_color": "#333333",
                "link_color": "#999999",
                "border_color": "#cccccc",
            },
            "dark": {
                "bg_color": "#1e1e1e",
                "text_color": "#e0e0e0",
                "link_color": "#666666",
                "border_color": "#444444",
            },
        }

        # Choose color scheme based on theme
        colors = color_scheme.get(theme, color_scheme["dark"])

        # Format HTML with colors
        formatted_html = html_template.format(
            title=title,
            bg_color=colors["bg_color"],
            text_color=colors["text_color"],
            link_color=colors["link_color"],
            border_color=colors["border_color"],
            js_data=js_data,
        )

        return formatted_html

    async def clear_database(self, request: DatabaseClearRequest) -> DatabaseClearResponse:
        """Clear all data from the database.

        This is a destructive operation that will delete all nodes and relationships
        in the database. Schema constraints and indexes will remain if preserve_schema
        is True.

        Args:
            request: Database clear request parameters

        Returns:
            DatabaseClearResponse with status of the operation

        Raises:
            HTTPException: If clearing the database fails
        """
        try:
            logger.warning("Clearing all data from database")

            # Create a delete query to remove all nodes and relationships
            delete_query = CypherQuery(query="MATCH (n) DETACH DELETE n", query_type="write")  # type: ignore[arg-type]

            # Execute the query
            await self.execute_cypher_query(delete_query)

            # If we need to reinitialize the schema
            if request.preserve_schema:
                logger.info("Preserving schema - reinitializing")
                schema_query = CypherQuery(
                    query="CALL apoc.schema.assert({}, {})", query_type="write"  # type: ignore[arg-type]
                )
                await self.execute_cypher_query(schema_query)

            logger.info("Database successfully cleared")
            return DatabaseClearResponse(status="success", message="Database successfully cleared")

        except Exception as e:
            logger.error(f"Error clearing database: {e!s}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error clearing database: {e!s}",
            ) from e


async def get_graph_service(
    neo4j: Neo4jAdapter = Depends(get_neo4j_adapter),
    openai: OpenAIAdapter = Depends(get_openai_adapter),
) -> GraphService:
    """Factory function to create a graph service.

    This is used as a FastAPI dependency.

    Args:
        neo4j: Neo4j adapter instance
        openai: OpenAI adapter instance

    Returns:
        GraphService instance
    """
    return GraphService(neo4j, openai)