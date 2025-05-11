/**
 * Types for graph data
 */
export interface GraphNode {
  id: string;
  name: string;
  type: string;
  path?: string;
  properties: Record<string, any>;
  [key: string]: any;
}

export interface GraphLink {
  source: string;
  target: string;
  type: string;
  properties: Record<string, any>;
  [key: string]: any;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

/**
 * Node type colors for visualization
 */
export const nodeColors: Record<string, string> = {
  File: '#4299E1',
  Directory: '#805AD5', 
  Function: '#38A169',
  Class: '#DD6B20',
  Module: '#D69E2E',
  Namespace: '#3182CE',
  Interface: '#0BC5EA',
  Method: '#48BB78',
  Variable: '#F56565',
  Constant: '#ED8936',
  Enum: '#A0AEC0',
  Document: '#9F7AEA',
  default: '#718096',
};

/**
 * Get color for a node based on its type
 * @param node - Graph node
 * @returns Hex color code
 */
export const getNodeColor = (node: GraphNode): string => {
  return nodeColors[node.type] || nodeColors.default;
};

/**
 * Format Neo4j response into graph data for visualization
 * @param response - Neo4j query response
 * @returns Formatted graph data
 */
export const formatGraphData = (response: any): GraphData => {
  const nodes: GraphNode[] = [];
  const links: GraphLink[] = [];
  const nodeMap = new Map<string, boolean>();

  if (response?.records) {
    response.records.forEach((record: any) => {
      Object.keys(record).forEach((key) => {
        const value = record[key];

        // Handle nodes
        if (value && typeof value === 'object' && 'properties' in value) {
          const id = value.id || value.properties.id || `node-${Math.random()}`;
          
          if (!nodeMap.has(id)) {
            nodeMap.set(id, true);
            nodes.push({
              id,
              name: value.properties.name || 'Unnamed',
              type: (value.labels && value.labels[0]) || 'Unknown',
              path: value.properties.path,
              properties: value.properties,
              ...value.properties,
            });
          }
        }

        // Handle relationships (if data contains them)
        if (
          value && 
          typeof value === 'object' && 
          'start' in value && 
          'end' in value &&
          'type' in value
        ) {
          links.push({
            source: value.start,
            target: value.end,
            type: value.type,
            properties: value.properties || {},
            ...value.properties,
          });
        }
      });
    });
  }

  return { nodes, links };
};

/**
 * Generate a simple 3D force graph configuration
 * @returns Force graph configuration
 */
export const getForceGraphConfig = () => ({
  nodeRelSize: 6,
  nodeAutoColorBy: 'type',
  linkWidth: 1.5,
  linkAutoColorBy: 'type',
  linkDirectionalParticles: 2,
  linkDirectionalParticleSpeed: 0.003,
  d3AlphaDecay: 0.02,
  d3VelocityDecay: 0.2,
});