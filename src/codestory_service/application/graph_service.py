"""Graph service for Code Story Service.

This module provides application-level services for interacting with
the graph database, including query execution, vector search, and
path finding, as well as visualization generation.
"""
import json
import logging
from typing import Any
from fastapi import Depends, HTTPException, status
from ..domain.graph import AskAnswer, AskRequest, CypherQuery, DatabaseClearRequest, DatabaseClearResponse, PathRequest, PathResult, QueryResult, VectorQuery, VectorResult, VisualizationRequest
from ..infrastructure.neo4j_adapter import Neo4jAdapter, get_neo4j_adapter
from ..infrastructure.openai_adapter import OpenAIAdapter, get_openai_adapter
logger = logging.getLogger(__name__)

class GraphService:
    """Application service for graph operations.

    This service orchestrates interactions with the graph database,
    providing high-level methods for the API layer.
    """

    def __init__(self: Any, neo4j_adapter: Neo4jAdapter, openai_adapter: OpenAIAdapter) -> None:
        """Initialize the graph service.

        Args:
            neo4j_adapter: Neo4j adapter instance
            openai_adapter: OpenAI adapter instance
        """
        self.neo4j = neo4j_adapter
        self.openai = openai_adapter

    async def execute_cypher_query(self: Any, query: CypherQuery) -> QueryResult:
        """Execute a Cypher query against the graph database.

        Args:
            query: Cypher query details

        Returns:
            QueryResult with the results of the query

        Raises:
            HTTPException: If the query execution fails
        """
        try:
            logger.info(f'Executing Cypher query: {query.query[:100]}...')
            result = await self.neo4j.execute_cypher_query(query)
            logger.info(f'Query returned {result.row_count} rows')
            return result
        except Exception as e:
            logger.error(f'Error executing Cypher query: {e!s}')
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error executing query: {e!s}') from e

    async def execute_vector_search(self: Any, query: VectorQuery) -> VectorResult:
        """Execute a vector similarity search.

        Args:
            query: Vector search query

        Returns:
            VectorResult with the search results

        Raises:
            HTTPException: If the search fails
        """
        try:
            logger.info(f'Generating embedding for vector search: {query.query}')
            embeddings = await self.openai.create_embeddings([query.query])
            if not embeddings or len(embeddings) == 0:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Failed to generate embedding for query')
            logger.info(f'Executing vector search for entity type: {query.entity_type}')
            result = await self.neo4j.execute_vector_search(query, embeddings[0])
            logger.info(f'Vector search returned {result.total_count} results')
            return result
        except Exception as e:
            logger.error(f'Error executing vector search: {e!s}')
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error executing vector search: {e!s}') from e

    async def find_path(self: Any, path_request: PathRequest) -> PathResult:
        """Find paths between nodes in the graph.

        Args:
            path_request: Path finding request

        Returns:
            PathResult with the found paths

        Raises:
            HTTPException: If the path finding fails
        """
        try:
            logger.info(f'Finding paths from {path_request.start_node_id} to {path_request.end_node_id} using algorithm {path_request.algorithm}')
            result = await self.neo4j.find_path(path_request)
            logger.info(f'Path finding returned {result.total_paths_found} paths')
            return result
        except Exception as e:
            logger.error(f'Error finding paths: {e!s}')
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error finding paths: {e!s}') from e

    async def answer_question(self: Any, request: AskRequest) -> AskAnswer:
        """Answer a natural language question about the codebase.

        Args:
            request: The question and parameters

        Returns:
            AskAnswer with the generated answer

        Raises:
            HTTPException: If answering fails
        """
        try:
            logger.info(f'Generating embedding for question: {request.question}')
            embeddings = await self.openai.create_embeddings([request.question])
            if not embeddings or len(embeddings) == 0:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Failed to generate embedding for question')
            context_size = request.context_size or 5
            vector_query = VectorQuery(query=request.question, entity_type=None, limit=context_size, min_score=0.5)
            search_result = await self.neo4j.execute_vector_search(vector_query, embeddings[0])
            context_items: list[Any] = []
            for result in search_result.results:
                node_query = CypherQuery(query='MATCH (n) WHERE elementId(n) = $id RETURN n', parameters={'id': result.id}, query_type='read')  # type: ignore[assignment]
                node_result = await self.neo4j.execute_cypher_query(node_query)
                if node_result.rows and len(node_result.rows) > 0 and (len(node_result.rows[0]) > 0):
                    node = node_result.rows[0][0]
                    node['score'] = result.score
                    context_items.append(node)
            logger.info(f'Generating answer using {len(context_items)} context items')
            answer = await self.openai.answer_question(request, context_items)
            logger.info('Answer generated successfully')
            return answer
        except Exception as e:
            logger.error(f'Error answering question: {e!s}')
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error answering question: {e!s}') from e

    async def generate_visualization(self: Any, request: VisualizationRequest) -> str:
        """Generate an interactive HTML visualization of the code graph.

        Args:
            request: Visualization parameters

        Returns:
            HTML content for the visualization

        Raises:
            HTTPException: If visualization generation fails
        """
        try:
            logger.info(f'Generating {request.type} visualization with {request.theme} theme')
            graph_data = await self._get_graph_data_for_visualization(request)
            html_content = self._generate_visualization_html(graph_data, request)
            logger.info('Visualization generated successfully')
            return html_content
        except Exception as e:
            logger.error(f'Error generating visualization: {e!s}')
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error generating visualization: {e!s}') from e

    async def _get_graph_data_for_visualization(self: Any, request: VisualizationRequest) -> dict[str, Any]:
        """Get graph data from Neo4j for visualization.

        Args:
            request: Visualization parameters

        Returns:
            Graph data dictionary with nodes and links
        """
        cypher_query = '\n        MATCH (n)\n        WHERE n.name IS NOT NULL  // Filter out nodes without names\n        WITH n LIMIT $max_nodes\n        OPTIONAL MATCH (n)-[r]->(m)\n        WHERE m.name IS NOT NULL  // Filter out relationships to unnamed nodes\n        RETURN \n          COLLECT(DISTINCT {\n            id: toString(id(n)), \n            label: labels(n)[0], \n            properties: properties(n)\n          }) AS nodes,\n          COLLECT(DISTINCT {\n            id: toString(id(r)), \n            source: toString(id(n)), \n            target: toString(id(m)), \n            type: type(r), \n            properties: properties(r)\n          }) AS relationships\n        '
        params = {'max_nodes': request.filter.max_nodes if request.filter else 100}
        if request.focus_node_id:
            cypher_query = '\n            MATCH (focus_node) \n            WHERE elementId(focus_node) = $focus_node_id\n            OPTIONAL MATCH path = (focus_node)-[*1..$depth]-(related)\n            WHERE related.name IS NOT NULL  // Filter out unnamed nodes\n            WITH focus_node, collect(path) as paths\n            // Unwind paths to get all nodes and relationships\n            UNWIND paths as p\n            WITH focus_node, p, nodes(p) as path_nodes, relationships(p) as path_rels\n            // Collect all nodes including focus_node\n            WITH \n              collect(DISTINCT focus_node) + \n              [node IN path_nodes WHERE node <> focus_node | node] as all_nodes,\n              collect(DISTINCT path_rels) as all_rels\n            UNWIND all_nodes as node\n            WITH collect(DISTINCT {\n              id: toString(id(node)), \n              label: labels(node)[0], \n              properties: properties(node), \n              is_focus: node = focus_node\n            }) as nodes, \n            all_rels\n            UNWIND all_rels as rel\n            RETURN \n              nodes, \n              collect(DISTINCT {\n                id: toString(id(rel)), \n                source: toString(id(startNode(rel))), \n                target: toString(id(endNode(rel))), \n                type: type(rel), \n                properties: properties(rel)\n              }) as relationships\n            '
            params['focus_node_id'] = request.focus_node_id  # type: ignore[assignment]
            params['depth'] = request.depth
        if request.filter and request.filter.node_types:
            node_types = request.filter.node_types
            cypher_query = cypher_query.replace('WHERE n.name IS NOT NULL', 'WHERE n.name IS NOT NULL AND labels(n)[0] IN $node_types')
            params['node_types'] = node_types  # type: ignore[assignment]
        if request.filter and request.filter.search_query:
            search_query = request.filter.search_query
            cypher_query = cypher_query.replace('WHERE n.name IS NOT NULL', 'WHERE n.name IS NOT NULL AND (n.name CONTAINS $search_query OR n.path CONTAINS $search_query)')
            params['search_query'] = search_query  # type: ignore[assignment]
        if request.filter and (not request.filter.include_orphans):
            cypher_query = cypher_query.replace('MATCH (n)', 'MATCH (n) WHERE EXISTS((n)--())')
        query = CypherQuery(query=cypher_query, parameters=params, query_type='read')  # type: ignore[assignment]
        result = await self.neo4j.execute_cypher_query(query)
        if not result.rows or len(result.rows) == 0:
            return {'nodes': [], 'links': []}
        nodes = result.rows[0][0]
        relationships = result.rows[0][1]
        if request.filter and request.filter.max_nodes < len(nodes):
            nodes = nodes[:request.filter.max_nodes]
            node_ids = {node['id'] for node in nodes}
            relationships = [rel for rel in relationships if rel['source'] in node_ids and rel['target'] in node_ids]
        graph_data = {'nodes': [{'id': node['id'], 'label': node['label'], 'name': node['properties'].get('name', 'Unnamed'), 'type': node['label'], 'properties': node['properties'], 'is_focus': node.get('is_focus', False)} for node in nodes], 'links': [{'id': rel['id'], 'source': rel['source'], 'target': rel['target'], 'type': rel['type'], 'properties': rel['properties']} for rel in relationships]}
        return graph_data

    def _generate_visualization_html(self: Any, graph_data: dict[str, Any], request: VisualizationRequest) -> str:
        """Generate HTML for graph visualization.

        Args:
            graph_data: Graph data with nodes and links
            request: Visualization parameters

        Returns:
            HTML content
        """
        viz_type = request.type.value
        theme = request.theme.value
        if theme == 'auto':
            theme = 'dark'
        title = 'Code Story Graph Visualization'
        if request.focus_node_id:
            for node in graph_data['nodes']:
                if node.get('is_focus', False):
                    title = f"Code Story Graph: {node.get('name', 'Unknown')}"
                    break
        for node in graph_data['nodes']:
            clean_props: dict[Any, Any] = {}
            if 'name' in node['properties']:
                clean_props['name'] = node['properties']['name']
            if 'path' in node['properties']:
                clean_props['path'] = node['properties']['path']
            if 'summary' in node['properties']:
                summary = node['properties']['summary']
                if summary and len(summary) > 100:
                    clean_props['summary'] = summary[:100] + '...'
                else:
                    clean_props['summary'] = summary
            for key, value in node['properties'].items():
                if key not in ['name', 'path', 'summary', 'embedding'] and isinstance(value, str | int | float | bool):
                    if isinstance(value, str) and len(value) > 100:
                        clean_props[key] = value[:100] + '...'
                    else:
                        clean_props[key] = value
            node['properties'] = clean_props
        js_data = f'\n        const graphData = {json.dumps(graph_data)};\n        const vizType = "{viz_type}";\n        const theme = "{theme}";\n        const title = "{title}";\n        const maxNodes = {(request.filter.max_nodes if request.filter else 100)};\n        const focusNodeId = {json.dumps(request.focus_node_id)};\n        '
        html_template = '\n        <!DOCTYPE html>\n        <html lang="en">\n        <head>\n            <meta charset="UTF-8">\n            <meta name="viewport" content="width=device-width, initial-scale=1.0">\n            <title>{title}</title>\n            <script src="https://d3js.org/d3.v7.min.js"></script>\n            <style>\n                :root {{\n                    --bg-color: {bg_color};\n                    --text-color: {text_color};\n                    --node-color-file: #4285F4;\n                    --node-color-directory: #0F9D58;\n                    --node-color-function: #F4B400;\n                    --node-color-class: #DB4437;\n                    --node-color-module: #9C27B0;\n                    --node-color-default: #757575;\n                    --link-color: {link_color};\n                    --focus-color: #FF5722;\n                }}\n                \n                body {{\n                    margin: 0;\n                    overflow: hidden;\n                    background-color: var(--bg-color);\n                    color: var(--text-color);\n                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, \n                                 Helvetica, Arial, sans-serif;\n                }}\n                \n                .container {{\n                    display: flex;\n                    height: 100vh;\n                }}\n                \n                .sidebar {{\n                    width: 300px;\n                    padding: 20px;\n                    overflow-y: auto;\n                    border-right: 1px solid {border_color};\n                }}\n                \n                .visualization {{\n                    flex-grow: 1;\n                    position: relative;\n                }}\n                \n                svg {{\n                    width: 100%;\n                    height: 100%;\n                }}\n                \n                .controls {{\n                    position: absolute;\n                    top: 20px;\n                    right: 20px;\n                    background-color: var(--bg-color);\n                    padding: 10px;\n                    border-radius: 5px;\n                    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);\n                }}\n                \n                .legend {{\n                    margin-top: 20px;\n                }}\n                \n                .legend-item {{\n                    display: flex;\n                    align-items: center;\n                    margin-bottom: 8px;\n                }}\n                \n                .legend-color {{\n                    width: 16px;\n                    height: 16px;\n                    border-radius: 50%;\n                    margin-right: 8px;\n                }}\n                \n                .node {{\n                    cursor: pointer;\n                }}\n                \n                .link {{\n                    stroke: var(--link-color);\n                    stroke-opacity: 0.6;\n                }}\n                \n                .node-label {{\n                    font-size: 12px;\n                    pointer-events: none;\n                }}\n                \n                .search-box {{\n                    margin-bottom: 20px;\n                }}\n                \n                .search-box input {{\n                    width: 100%;\n                    padding: 8px;\n                    border-radius: 4px;\n                    border: 1px solid {border_color};\n                    background-color: var(--bg-color);\n                    color: var(--text-color);\n                }}\n                \n                .node-details {{\n                    padding-top: 20px;\n                    border-top: 1px solid {border_color};\n                }}\n                \n                .property {{\n                    margin-bottom: 5px;\n                }}\n                \n                .property-name {{\n                    font-weight: bold;\n                }}\n                \n                .expandable {{\n                    cursor: pointer;\n                    border: 2px dashed #FF5722;\n                }}\n                \n                .tooltip {{\n                    position: absolute;\n                    padding: 10px;\n                    background-color: var(--bg-color);\n                    border: 1px solid {border_color};\n                    border-radius: 5px;\n                    pointer-events: none;\n                    opacity: 0;\n                    transition: opacity 0.3s;\n                    max-width: 300px;\n                    z-index: 1000;\n                }}\n            </style>\n        </head>\n        <body>\n            <div class="container">\n                <div class="sidebar">\n                    <h1>Code Story</h1>\n                    <p>Interactive visualization of your codebase structure</p>\n                    \n                    <div class="search-box">\n                        <input type="text" id="search" placeholder="Search nodes..." />\n                    </div>\n                    \n                    <div class="legend">\n                        <h3>Node Types</h3>\n                        <div class="legend-item">\n                            <div class="legend-color" \n                                 style="background-color: var(--node-color-file)"></div>\n                            <div>File</div>\n                        </div>\n                        <div class="legend-item">\n                            <div class="legend-color" \n                                 style="background-color: var(--node-color-directory)"></div>\n                            <div>Directory</div>\n                        </div>\n                        <div class="legend-item">\n                            <div class="legend-color" \n                                 style="background-color: var(--node-color-function)"></div>\n                            <div>Function</div>\n                        </div>\n                        <div class="legend-item">\n                            <div class="legend-color" \n                                 style="background-color: var(--node-color-class)"></div>\n                            <div>Class</div>\n                        </div>\n                        <div class="legend-item">\n                            <div class="legend-color" \n                                 style="background-color: var(--node-color-module)"></div>\n                            <div>Module</div>\n                        </div>\n                    </div>\n                    \n                    <div class="node-details" id="node-details">\n                        <h3>Node Details</h3>\n                        <p>Click on a node to see details</p>\n                    </div>\n                </div>\n                \n                <div class="visualization">\n                    <svg id="graph"></svg>\n                    \n                    <div class="controls">\n                        <button id="zoom-in">+</button>\n                        <button id="zoom-out">-</button>\n                        <button id="reset">Reset</button>\n                    </div>\n                    \n                    <div class="tooltip" id="tooltip"></div>\n                </div>\n            </div>\n            \n            <script>\n                // Graph data from server\n                {js_data}\n                \n                // Initialize visualization\n                document.addEventListener(\'DOMContentLoaded\', () => {{\n                    // Visualization variables\n                    let svg = d3.select(\'#graph\');\n                    let width = svg.node().parentElement.clientWidth;\n                    let height = svg.node().parentElement.clientHeight;\n                    let nodeRadius = 10;\n                    let simulation;\n                    let nodeElements;\n                    let linkElements;\n                    let textElements;\n                    \n                    // Color function for nodes based on type\n                    function getNodeColor(node) {{\n                        if (node.id === focusNodeId || node.is_focus) {{\n                            return \'var(--focus-color)\';\n                        }}\n                        \n                        const type = node.type.toLowerCase();\n                        if (type.includes(\'file\')) return \'var(--node-color-file)\';\n                        if (type.includes(\'directory\')) return \'var(--node-color-directory)\';\n                        if (type.includes(\'function\')) return \'var(--node-color-function)\';\n                        if (type.includes(\'class\')) return \'var(--node-color-class)\';\n                        if (type.includes(\'module\')) return \'var(--node-color-module)\';\n                        return \'var(--node-color-default)\';\n                    }}\n                    \n                    // Node size based on connections\n                    function getNodeSize(node) {{\n                        let size = nodeRadius;\n                        const links = graphData.links.filter(link => \n                            link.source === node.id || link.source.id === node.id || \n                            link.target === node.id || link.target.id === node.id\n                        );\n                        \n                        if (links.length > 0) {{\n                            size += Math.min(links.length * 2, 10);  // Cap the size increase\n                        }}\n                        \n                        if (node.id === focusNodeId || node.is_focus) {{\n                            size += 5;  // Make focus node larger\n                        }}\n                        \n                        return size;\n                    }}\n                    \n                    // Check if node is expandable\n                    function isExpandable(node) {{\n                        // A node is expandable if it\'s not a focus node and has properties \n                        // indicating more connections\n                        return !node.is_focus && node.properties && \n                              (node.properties.has_children === true || \n                               node.properties.has_more_connections === true);\n                    }}\n                    \n                    // Initialize the visualization\n                    function initializeVisualization() {{\n                        // Clear any existing visualization\n                        svg.selectAll(\'*\').remove();\n                        \n                        // Create zoom behavior\n                        const zoom = d3.zoom()\n                            .scaleExtent([0.1, 8])\n                            .on(\'zoom\', (event) => {{\n                                container.attr(\'transform\', event.transform);\n                            }});\n                        \n                        svg.call(zoom);\n                        \n                        // Create container for the graph\n                        const container = svg.append(\'g\');\n                        \n                        // Add a border to make the visualization area more visible\n                        svg.append(\'rect\')\n                            .attr(\'width\', width)\n                            .attr(\'height\', height)\n                            .attr(\'fill\', \'none\')\n                            .attr(\'stroke\', \'{border_color}\');\n                        \n                        // Create arrow markers for directed graphs\n                        svg.append(\'defs\').selectAll(\'marker\')\n                            .data([\'end\'])\n                            .enter().append(\'marker\')\n                            .attr(\'id\', d => d)\n                            .attr(\'viewBox\', \'0 -5 10 10\')\n                            .attr(\'refX\', 20)\n                            .attr(\'refY\', 0)\n                            .attr(\'markerWidth\', 6)\n                            .attr(\'markerHeight\', 6)\n                            .attr(\'orient\', \'auto\')\n                            .append(\'path\')\n                            .attr(\'fill\', \'var(--link-color)\')\n                            .attr(\'d\', \'M0,-5L10,0L0,5\');\n                        \n                        // Create links, nodes, and labels\n                        linkElements = container.append(\'g\')\n                            .selectAll(\'line\')\n                            .data(graphData.links)\n                            .enter().append(\'line\')\n                            .attr(\'class\', \'link\')\n                            .attr(\'stroke-width\', 1)\n                            .attr(\'marker-end\', \'url(#end)\');\n                        \n                        nodeElements = container.append(\'g\')\n                            .selectAll(\'circle\')\n                            .data(graphData.nodes)\n                            .enter().append(\'circle\')\n                            .attr(\'class\', \'node\')\n                            .attr(\'r\', getNodeSize)\n                            .attr(\'fill\', getNodeColor)\n                            .classed(\'expandable\', isExpandable)\n                            .call(d3.drag()\n                                .on(\'start\', dragStarted)\n                                .on(\'drag\', dragged)\n                                .on(\'end\', dragEnded));\n                        \n                        textElements = container.append(\'g\')\n                            .selectAll(\'text\')\n                            .data(graphData.nodes)\n                            .enter().append(\'text\')\n                            .attr(\'class\', \'node-label\')\n                            .attr(\'text-anchor\', \'middle\')\n                            .attr(\'fill\', \'var(--text-color)\')\n                            .text(d => d.name || d.label);\n                        \n                        // Setup force simulation\n                        if (vizType === \'force\') {{\n                            simulation = d3.forceSimulation(graphData.nodes)\n                                .force(\'charge\', d3.forceManyBody().strength(-200))\n                                .force(\'center\', d3.forceCenter(width / 2, height / 2))\n                                .force(\'link\', d3.forceLink(graphData.links)\n                                    .id(d => d.id)\n                                    .distance(100))\n                                .force(\'collision\', d3.forceCollide().radius(30))\n                                .on(\'tick\', ticked);\n                        }} else if (vizType === \'radial\') {{\n                            simulation = d3.forceSimulation(graphData.nodes)\n                                .force(\'charge\', d3.forceManyBody().strength(-200))\n                                .force(\'center\', d3.forceCenter(width / 2, height / 2))\n                                .force(\'link\', d3.forceLink(graphData.links)\n                                    .id(d => d.id)\n                                    .distance(100))\n                                .force(\'radial\', d3.forceRadial(200, width / 2, height / 2))\n                                .force(\'collision\', d3.forceCollide().radius(30))\n                                .on(\'tick\', ticked);\n                        }} else if (vizType === \'hierarchy\') {{\n                            // Find root node (typically a directory or focus node)\n                            let rootNode = graphData.nodes.find(n => n.is_focus) || \n                                          graphData.nodes.find(n => n.type === \'Directory\') ||\n                                          graphData.nodes[0];\n                            \n                            const hierarchyLinks = graphData.links.map(link => ({{\n                                source: link.source.id || link.source,\n                                target: link.target.id || link.target,\n                                value: 1\n                            }}));\n                            \n                            // Create a hierarchical layout\n                            const root = d3.stratify()\n                                .id(d => d.id)\n                                .parentId(d => {{\n                                    // Find a parent link\n                                    const parentLink = hierarchyLinks.find(\n                                        link => link.target === d.id\n                                    );\n                                    return parentLink ? parentLink.source : null;\n                                }})\n                                (graphData.nodes);\n                            \n                            // Apply tree layout\n                            const treeLayout = d3.tree()\n                                .size([width - 100, height - 100]);\n                            \n                            treeLayout(root);\n                            \n                            // Update node positions\n                            root.descendants().forEach(node => {{\n                                const dataNode = graphData.nodes.find(n => n.id === node.id);\n                                if (dataNode) {{\n                                    dataNode.x = node.x + 50;\n                                    dataNode.y = node.y + 50;\n                                }}\n                            }});\n                            \n                            // Update the visualization\n                            ticked();\n                        }} else {{\n                            // Default to force-directed for other types\n                            simulation = d3.forceSimulation(graphData.nodes)\n                                .force(\'charge\', d3.forceManyBody().strength(-200))\n                                .force(\'center\', d3.forceCenter(width / 2, height / 2))\n                                .force(\'link\', d3.forceLink(graphData.links)\n                                    .id(d => d.id)\n                                    .distance(100))\n                                .force(\'collision\', d3.forceCollide().radius(30))\n                                .on(\'tick\', ticked);\n                        }}\n                        \n                        // Setup node events\n                        setupNodeEvents();\n                        \n                        // Setup controls\n                        setupControls(zoom);\n                        \n                        // Setup search\n                        setupSearch();\n                    }}\n                    \n                    // Update visualization on each tick\n                    function ticked() {{\n                        linkElements\n                            .attr(\'x1\', d => d.source.x)\n                            .attr(\'y1\', d => d.source.y)\n                            .attr(\'x2\', d => d.target.x)\n                            .attr(\'y2\', d => d.target.y);\n                        \n                        nodeElements\n                            .attr(\'cx\', d => d.x)\n                            .attr(\'cy\', d => d.y);\n                        \n                        textElements\n                            .attr(\'x\', d => d.x)\n                            .attr(\'y\', d => d.y + getNodeSize(d) + 10);\n                    }}\n                    \n                    // Drag functions\n                    function dragStarted(event, d) {{\n                        if (!event.active) simulation.alphaTarget(0.3).restart();\n                        d.fx = d.x;\n                        d.fy = d.y;\n                    }}\n                    \n                    function dragged(event, d) {{\n                        d.fx = event.x;\n                        d.fy = event.y;\n                    }}\n                    \n                    function dragEnded(event, d) {{\n                        if (!event.active) simulation.alphaTarget(0);\n                        d.fx = null;\n                        d.fy = null;\n                    }}\n                    \n                    // Setup node events (hover, click)\n                    function setupNodeEvents() {{\n                        const tooltip = d3.select(\'#tooltip\');\n                        \n                        nodeElements\n                            .on(\'mouseover\', (event, d) => {{\n                                // Highlight node and connected links\n                                nodeElements.style(\'opacity\', n => isConnected(d, n) ? 1 : 0.3);\n                                linkElements.style(\'opacity\', l => \n                                    l.source.id === d.id || l.target.id === d.id ? 1 : 0.1\n                                );\n                                textElements.style(\'opacity\', n => isConnected(d, n) ? 1 : 0.3);\n                                \n                                // Show tooltip\n                                tooltip\n                                    .style(\'left\', (event.pageX + 10) + \'px\')\n                                    .style(\'top\', (event.pageY - 10) + \'px\')\n                                    .style(\'opacity\', 0.9)\n                                    .html(`\n                                        <strong>${d.name || d.label}</strong><br>\n                                        <span>Type: ${d.type}</span>\n                                        ${d.properties.path ? \n                                            `<br><span>Path: ${d.properties.path}</span>` : \'\'}\n                                    `);\n                            }})\n                            .on(\'mouseout\', () => {{\n                                // Reset highlights\n                                nodeElements.style(\'opacity\', 1);\n                                linkElements.style(\'opacity\', 0.6);\n                                textElements.style(\'opacity\', 1);\n                                \n                                // Hide tooltip\n                                tooltip.style(\'opacity\', 0);\n                            }})\n                            .on(\'click\', (event, d) => {{\n                                // Show node details\n                                showNodeDetails(d);\n                                \n                                // Prevent event from propagating\n                                event.stopPropagation();\n                            }});\n                    }}\n                    \n                    // Check if two nodes are connected\n                    function isConnected(a, b) {{\n                        return a === b ||\n                            graphData.links.some(l => \n                                (l.source === a && l.target === b) || \n                                (l.source === b && l.target === a) ||\n                                (l.source.id === a.id && l.target.id === b.id) || \n                                (l.source.id === b.id && l.target.id === a.id)\n                            );\n                    }}\n                    \n                    // Show node details in sidebar\n                    function showNodeDetails(node) {{\n                        const detailsDiv = document.getElementById(\'node-details\');\n                        \n                        // Create details HTML\n                        let detailsHTML = `\n                            <h3>${node.name || node.label}</h3>\n                            <div class="property">\n                                <span class="property-name">Type:</span> ${node.type}\n                            </div>\n                        `;\n                        \n                        // Add other properties\n                        for (const [key, value] of Object.entries(node.properties)) {{\n                            if (key !== \'name\' && key !== \'type\') {{\n                                detailsHTML += `\n                                    <div class="property">\n                                        <span class="property-name">${key}:</span> ${value}\n                                    </div>\n                                `;\n                            }}\n                        }}\n                        \n                        // Add connected nodes\n                        const connectedNodes = graphData.links\n                            .filter(l => l.source.id === node.id || l.source === node.id || \n                                         l.target.id === node.id || l.target === node.id)\n                            .map(l => {{\n                                const connectedId = (\n                                    l.source.id === node.id || l.source === node.id\n                                ) ? (l.target.id || l.target) : (l.source.id || l.source);\n                                const connectedNode = graphData.nodes.find(\n                                    n => n.id === connectedId\n                                );\n                                return {{\n                                    node: connectedNode,\n                                    relationship: l.type\n                                }};\n                            }});\n                        \n                        if (connectedNodes.length > 0) {{\n                            detailsHTML += `<h4>Connected to:</h4>`;\n                            connectedNodes.forEach(conn => {{\n                                if (conn.node) {{\n                                    detailsHTML += `\n                                        <div class="property">\n                                            <span class="property-name">${conn.relationship}:</span>\n                                            ${conn.node.name || conn.node.label}\n                                        </div>\n                                    `;\n                                }}\n                            }});\n                        }}\n                        \n                        // Update details div\n                        detailsDiv.innerHTML = detailsHTML;\n                    }}\n                    \n                    // Setup zoom/reset controls\n                    function setupControls(zoom) {{\n                        document.getElementById(\'zoom-in\').addEventListener(\'click\', () => {{\n                            svg.transition().call(zoom.scaleBy, 1.5);\n                        }});\n                        \n                        document.getElementById(\'zoom-out\').addEventListener(\'click\', () => {{\n                            svg.transition().call(zoom.scaleBy, 0.75);\n                        }});\n                        \n                        document.getElementById(\'reset\').addEventListener(\'click\', () => {{\n                            svg.transition().call(zoom.transform, d3.zoomIdentity);\n                        }});\n                    }}\n                    \n                    // Setup search functionality\n                    function setupSearch() {{\n                        const searchInput = document.getElementById(\'search\');\n                        \n                        searchInput.addEventListener(\'input\', () => {{\n                            const query = searchInput.value.toLowerCase();\n                            \n                            // If query is empty, reset all nodes\n                            if (query === \'\') {{\n                                nodeElements.style(\'opacity\', 1);\n                                textElements.style(\'opacity\', 1);\n                                linkElements.style(\'opacity\', 0.6);\n                                return;\n                            }}\n                            \n                            // Highlight matching nodes\n                            nodeElements.style(\'opacity\', d => {{\n                                const matchesSearch = \n                                    (d.name && d.name.toLowerCase().includes(query)) ||\n                                    (d.label && d.label.toLowerCase().includes(query)) ||\n                                    (d.properties.path && \n                                     d.properties.path.toLowerCase().includes(query));\n                                \n                                return matchesSearch ? 1 : 0.2;\n                            }});\n                            \n                            // Highlight matching text\n                            textElements.style(\'opacity\', d => {{\n                                const matchesSearch = \n                                    (d.name && d.name.toLowerCase().includes(query)) ||\n                                    (d.label && d.label.toLowerCase().includes(query)) ||\n                                    (d.properties.path && \n                                     d.properties.path.toLowerCase().includes(query));\n                                \n                                return matchesSearch ? 1 : 0.2;\n                            }});\n                            \n                            // Dim all links\n                            linkElements.style(\'opacity\', 0.1);\n                        }});\n                    }}\n                    \n                    // Initialize the visualization when DOM is loaded\n                    initializeVisualization();\n                    \n                    // Resize handler\n                    window.addEventListener(\'resize\', () => {{\n                        width = svg.node().parentElement.clientWidth;\n                        height = svg.node().parentElement.clientHeight;\n                        \n                        if (simulation) {{\n                            simulation.force(\'center\', d3.forceCenter(width / 2, height / 2));\n                            simulation.alpha(0.3).restart();\n                        }}\n                    }});\n                }});\n            </script>\n        </body>\n        </html>\n        '
        color_scheme = {'light': {'bg_color': '#ffffff', 'text_color': '#333333', 'link_color': '#999999', 'border_color': '#cccccc'}, 'dark': {'bg_color': '#1e1e1e', 'text_color': '#e0e0e0', 'link_color': '#666666', 'border_color': '#444444'}}
        colors = color_scheme.get(theme, color_scheme['dark'])
        formatted_html = html_template.format(title=title, bg_color=colors['bg_color'], text_color=colors['text_color'], link_color=colors['link_color'], border_color=colors['border_color'], js_data=js_data)
        return formatted_html

    async def clear_database(self: Any, request: DatabaseClearRequest) -> DatabaseClearResponse:
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
            logger.warning('Clearing all data from database')
            delete_query = CypherQuery(query='MATCH (n) DETACH DELETE n', query_type='write')  # type: ignore[assignment]
            await self.execute_cypher_query(delete_query)
            if request.preserve_schema:
                logger.info('Preserving schema - reinitializing')
                schema_query = CypherQuery(query='CALL apoc.schema.assert({}, {})', query_type='write')  # type: ignore[assignment]
                await self.execute_cypher_query(schema_query)
            logger.info('Database successfully cleared')
            return DatabaseClearResponse(status='success', message='Database successfully cleared')
        except Exception as e:
            logger.error(f'Error clearing database: {e!s}')
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Error clearing database: {e!s}') from e

async def get_graph_service(neo4j: Neo4jAdapter=Depends(get_neo4j_adapter), openai: OpenAIAdapter=Depends(get_openai_adapter)) -> GraphService:
    """Factory function to create a graph service.

    This is used as a FastAPI dependency.

    Args:
        neo4j: Neo4j adapter instance
        openai: OpenAI adapter instance

    Returns:
        GraphService instance
    """
    return GraphService(neo4j, openai)