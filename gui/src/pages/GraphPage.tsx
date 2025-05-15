import React, { useState } from 'react';
import { Box, Grid, Stack } from '@mantine/core';
import GraphViewer from '../components/graph/GraphViewer';
import NodeDetails from '../components/graph/NodeDetails';
import EdgeDetails from '../components/graph/EdgeDetails';
import GraphControls from '../components/graph/GraphControls';
import { GraphNode, GraphLink } from '../utils/graph';
import useGraph from '../hooks/useGraph';

/**
 * GraphPage component for visualizing the knowledge graph
 */
const GraphPage: React.FC = () => {
  const {
    runQuery,
    filterNodesByType,
    resetGraph,
    loading
  } = useGraph();

  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<GraphLink | null>(null);

  // Handle node selection
  const handleNodeClick = (node: GraphNode) => {
    setSelectedNode(node);
    setSelectedEdge(null);
  };

  // Handle edge selection
  const handleEdgeClick = (edge: GraphLink) => {
    setSelectedEdge(edge);
    setSelectedNode(null);
  };

  // Close detail panels
  const handleCloseDetails = () => {
    setSelectedNode(null);
    setSelectedEdge(null);
  };

  // Handle node navigation from relationships
  const handleNavigateToNode = (nodeId: string) => {
    // In a real implementation, this would find the node by ID
    console.log('Navigate to node:', nodeId);
    // setSelectedNode(findNodeById(nodeId));
  };

  return (
    <Box>
      <Grid gutter="md">
        <Grid.Col span={12}>
          <GraphControls
            onRunQuery={runQuery}
            onFilterNodesByType={filterNodesByType}
            onResetGraph={resetGraph}
            isLoading={loading}
          />
        </Grid.Col>

        <Grid.Col span={selectedNode || selectedEdge ? 8 : 12}>
          <GraphViewer
            onNodeClick={handleNodeClick}
            onLinkClick={handleEdgeClick}
          />
        </Grid.Col>

        {(selectedNode || selectedEdge) && (
          <Grid.Col span={4}>
            <Stack>
              {selectedNode && (
                <NodeDetails
                  node={selectedNode}
                  onClose={handleCloseDetails}
                  onNavigateToNode={handleNavigateToNode}
                />
              )}

              {selectedEdge && (
                <EdgeDetails
                  edge={selectedEdge}
                  onClose={handleCloseDetails}
                  onNavigateToNode={handleNavigateToNode}
                />
              )}
            </Stack>
          </Grid.Col>
        )}
      </Grid>
    </Box>
  );
};

export default GraphPage;