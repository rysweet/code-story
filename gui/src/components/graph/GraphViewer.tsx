import React, { useEffect, useRef, useState } from 'react';
import { Card, Text, Box, Loader, Group, Select, Slider, ActionIcon } from '@mantine/core';
import ForceGraph3D from 'force-graph';
import { IconPlus, IconMinus, IconRefresh, IconSearch } from '@tabler/icons-react';
import { useExecuteQueryMutation } from '../../store';
import { formatGraphData, getNodeColor, GraphNode, GraphLink, GraphData } from '../../utils/graph';

interface GraphViewerProps {
  initialQuery?: string;
  onNodeClick?: (node: GraphNode) => void;
  onLinkClick?: (link: GraphLink) => void;
}

/**
 * 3D force graph component for visualizing Code Story graph data
 */
const GraphViewer: React.FC<GraphViewerProps> = ({ 
  initialQuery = 'MATCH (n) RETURN n LIMIT 100',
  onNodeClick,
  onLinkClick
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [executeQuery, { isLoading, error }] = useExecuteQueryMutation();
  const [nodeSize, setNodeSize] = useState(6);
  const [linkWidth, setLinkWidth] = useState(1.5);
  const [colorBy, setColorBy] = useState<string>('type');
  
  // Initialize the graph when the component mounts
  useEffect(() => {
    if (!containerRef.current) return;
    
    const graph = ForceGraph3D()(containerRef.current)
      .nodeRelSize(nodeSize)
      .nodeAutoColorBy(colorBy)
      .linkWidth(linkWidth)
      .linkAutoColorBy('type')
      .linkDirectionalParticles(2)
      .linkDirectionalParticleSpeed(0.003)
      .d3AlphaDecay(0.02)
      .d3VelocityDecay(0.2)
      .onNodeClick((node: any) => {
        if (onNodeClick) {
          onNodeClick(node as GraphNode);
        }
      })
      .onLinkClick((link: any) => {
        if (onLinkClick) {
          onLinkClick(link as GraphLink);
        }
      });
    
    graphRef.current = graph;
    
    return () => {
      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
    };
  }, [onNodeClick, onLinkClick, nodeSize, linkWidth, colorBy]);
  
  // Update graph data when it changes
  useEffect(() => {
    if (graphRef.current && graphData) {
      graphRef.current.graphData(graphData);
    }
  }, [graphData]);

  // Initial query when component mounts
  useEffect(() => {
    fetchGraphData(initialQuery);
    
    // Handle window resize
    const handleResize = () => {
      if (graphRef.current) {
        graphRef.current.width(containerRef.current?.clientWidth || 800);
        graphRef.current.height(containerRef.current?.clientHeight || 600);
      }
    };
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [initialQuery]);
  
  // Fetch graph data from API
  const fetchGraphData = async (query: string, parameters?: Record<string, any>) => {
    try {
      const response = await executeQuery({ 
        query, 
        parameters: parameters || {} 
      }).unwrap();
      
      if (response.error) {
        console.error('Query error:', response.error);
        return;
      }
      
      const formattedData = formatGraphData(response);
      setGraphData(formattedData);
    } catch (err) {
      console.error('Failed to fetch graph data:', err);
    }
  };
  
  // Zoom controls
  const zoomIn = () => {
    if (graphRef.current) {
      const distance = graphRef.current.cameraPosition().z;
      graphRef.current.cameraPosition({ z: distance * 0.8 });
    }
  };
  
  const zoomOut = () => {
    if (graphRef.current) {
      const distance = graphRef.current.cameraPosition().z;
      graphRef.current.cameraPosition({ z: distance * 1.2 });
    }
  };
  
  const resetView = () => {
    if (graphRef.current) {
      graphRef.current.cameraPosition({ x: 0, y: 0, z: 1000 }, { x: 0, y: 0, z: 0 });
    }
  };
  
  return (
    <Card shadow="sm" radius="md" style={{ height: 'calc(100vh - 180px)' }}>
      <Card.Section withBorder inheritPadding py="md">
        <Group position="apart">
          <Text weight={500}>Graph Visualization</Text>
          <Group spacing="xs">
            <ActionIcon onClick={zoomIn} variant="light">
              <IconPlus size={16} />
            </ActionIcon>
            <ActionIcon onClick={zoomOut} variant="light">
              <IconMinus size={16} />
            </ActionIcon>
            <ActionIcon onClick={resetView} variant="light">
              <IconRefresh size={16} />
            </ActionIcon>
          </Group>
        </Group>
      </Card.Section>
      
      <Card.Section withBorder inheritPadding py="md">
        <Group spacing="md">
          <Select
            label="Color By"
            value={colorBy}
            onChange={(val) => setColorBy(val || 'type')}
            data={[
              { value: 'type', label: 'Node Type' },
              { value: 'name', label: 'Node Name' },
              { value: 'path', label: 'File Path' },
            ]}
            style={{ width: 150 }}
          />
          
          <Box sx={{ flex: 1 }}>
            <Text size="sm">Node Size</Text>
            <Slider
              value={nodeSize}
              onChange={setNodeSize}
              min={1}
              max={15}
              step={1}
              marks={[
                { value: 1, label: '1' },
                { value: 8, label: '8' },
                { value: 15, label: '15' },
              ]}
            />
          </Box>
          
          <Box sx={{ flex: 1 }}>
            <Text size="sm">Link Width</Text>
            <Slider
              value={linkWidth}
              onChange={setLinkWidth}
              min={0.5}
              max={5}
              step={0.5}
              marks={[
                { value: 0.5, label: '0.5' },
                { value: 2.5, label: '2.5' },
                { value: 5, label: '5' },
              ]}
            />
          </Box>
        </Group>
      </Card.Section>
      
      <Card.Section style={{ height: 'calc(100% - 160px)', position: 'relative' }}>
        {isLoading && (
          <Box 
            sx={{ 
              position: 'absolute', 
              top: 0, 
              left: 0, 
              right: 0, 
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'rgba(255,255,255,0.7)',
              zIndex: 10,
            }}
          >
            <Loader size="lg" />
          </Box>
        )}
        
        {error && (
          <Box p="md">
            <Text color="red">Error loading graph data: {JSON.stringify(error)}</Text>
          </Box>
        )}
        
        <div 
          ref={containerRef} 
          style={{ width: '100%', height: '100%' }}
        />
      </Card.Section>
    </Card>
  );
};

export default GraphViewer;