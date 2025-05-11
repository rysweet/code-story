import { useState, useCallback } from 'react';
import { useExecuteQueryMutation } from '../store';
import { formatGraphData, GraphData, GraphNode, GraphLink } from '../utils/graph';

/**
 * Hook for managing graph data and interactions
 * @returns Graph data and control functions
 */
export function useGraph() {
  const [executeQuery] = useExecuteQueryMutation();
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedLink, setSelectedLink] = useState<GraphLink | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Execute a Cypher query and update the graph data
   * @param query - Cypher query string
   * @param parameters - Query parameters
   */
  const runQuery = useCallback(async (query: string, parameters?: Record<string, any>) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await executeQuery({ query, parameters }).unwrap();
      
      if (response.error) {
        setError(response.error);
        return;
      }
      
      const formattedData = formatGraphData(response);
      setGraphData(formattedData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  }, [executeQuery]);

  /**
   * Find a node by its ID
   * @param nodeId - Node ID to find
   * @returns The found node or null
   */
  const findNodeById = useCallback((nodeId: string): GraphNode | null => {
    return graphData.nodes.find(node => node.id === nodeId) || null;
  }, [graphData.nodes]);

  /**
   * Filter nodes by type
   * @param types - Array of node types to keep
   */
  const filterNodesByType = useCallback((types: string[]) => {
    if (!types.length) {
      return;
    }
    
    setGraphData(prev => {
      const filteredNodes = prev.nodes.filter(node => types.includes(node.type));
      const nodeIds = new Set(filteredNodes.map(node => node.id));
      
      const filteredLinks = prev.links.filter(
        link => nodeIds.has(link.source as string) && nodeIds.has(link.target as string)
      );
      
      return {
        nodes: filteredNodes,
        links: filteredLinks,
      };
    });
  }, []);

  /**
   * Clear the current graph selection
   */
  const clearSelection = useCallback(() => {
    setSelectedNode(null);
    setSelectedLink(null);
  }, []);

  /**
   * Reset the graph data to an empty state
   */
  const resetGraph = useCallback(() => {
    setGraphData({ nodes: [], links: [] });
    clearSelection();
  }, [clearSelection]);

  return {
    graphData,
    selectedNode,
    selectedLink,
    loading,
    error,
    runQuery,
    setSelectedNode,
    setSelectedLink,
    findNodeById,
    filterNodesByType,
    clearSelection,
    resetGraph,
  };
}

export default useGraph;