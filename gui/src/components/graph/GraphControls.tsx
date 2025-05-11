import React, { useState } from 'react';
import { 
  Card, 
  TextInput, 
  MultiSelect, 
  Button, 
  Group, 
  Collapse, 
  Stack,
  Switch,
  Title,
  Text,
  NumberInput,
  ActionIcon
} from '@mantine/core';
import { IconSearch, IconFilter, IconChevronDown, IconChevronUp, IconRefresh } from '@tabler/icons-react';
import { nodeColors } from '../../utils/graph';

interface GraphControlsProps {
  onRunQuery: (query: string, parameters?: Record<string, any>) => void;
  onFilterNodesByType: (types: string[]) => void;
  onResetGraph: () => void;
  availableNodeTypes?: string[];
  isLoading?: boolean;
}

/**
 * Component for graph query and filtering controls
 */
const GraphControls: React.FC<GraphControlsProps> = ({
  onRunQuery,
  onFilterNodesByType,
  onResetGraph,
  availableNodeTypes = ['File', 'Directory', 'Class', 'Function', 'Method', 'Module', 'Variable'],
  isLoading = false,
}) => {
  const [query, setQuery] = useState('MATCH (n) RETURN n LIMIT 100');
  const [nodeLimit, setNodeLimit] = useState(100);
  const [includeRelationships, setIncludeRelationships] = useState(true);
  const [expanded, setExpanded] = useState(false);
  const [selectedNodeTypes, setSelectedNodeTypes] = useState<string[]>([]);
  
  // Run the current query
  const handleRunQuery = () => {
    let finalQuery = query;
    
    // If query doesn't already have a LIMIT clause, add one
    if (!finalQuery.toUpperCase().includes('LIMIT') && nodeLimit > 0) {
      finalQuery = `${finalQuery} LIMIT ${nodeLimit}`;
    }
    
    // If including relationships and query doesn't already fetch them
    if (includeRelationships && !finalQuery.includes('-->') && !finalQuery.includes('<--') && !finalQuery.includes('-[')) {
      // Adjust the query to include relationships
      if (finalQuery.includes('RETURN n')) {
        finalQuery = finalQuery.replace(
          'RETURN n', 
          'MATCH (n)-[r]->(m) RETURN n, r, m'
        );
      }
    }
    
    onRunQuery(finalQuery);
  };
  
  // Generate a list of node type options with colors
  const nodeTypeOptions = availableNodeTypes.map(type => ({
    value: type,
    label: type,
    color: nodeColors[type] || nodeColors.default,
  }));
  
  return (
    <Card shadow="sm" radius="md" p="md" withBorder>
      <Stack spacing="md">
        <Group position="apart">
          <Title order={4}>Graph Query</Title>
          <ActionIcon onClick={() => setExpanded(!expanded)}>
            {expanded ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />}
          </ActionIcon>
        </Group>
        
        <Group>
          <TextInput
            placeholder="Enter Cypher query..."
            label="Cypher Query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            sx={{ flex: 1 }}
          />
          
          <NumberInput
            label="Node Limit"
            value={nodeLimit}
            onChange={(val) => setNodeLimit(val || 100)}
            min={1}
            max={1000}
            step={10}
            style={{ width: 120 }}
          />
          
          <Button
            leftIcon={<IconSearch size={16} />}
            onClick={handleRunQuery}
            loading={isLoading}
            style={{ marginTop: 24 }}
          >
            Run Query
          </Button>
          
          <Button
            variant="outline"
            leftIcon={<IconRefresh size={16} />}
            onClick={onResetGraph}
            style={{ marginTop: 24 }}
          >
            Reset
          </Button>
        </Group>
        
        <Collapse in={expanded}>
          <Stack spacing="md" mt="md">
            <Switch
              label="Include relationships"
              checked={includeRelationships}
              onChange={(e) => setIncludeRelationships(e.currentTarget.checked)}
            />
            
            <Text weight={500} size="sm">Filter by Node Type</Text>
            <Group>
              <MultiSelect
                data={nodeTypeOptions}
                value={selectedNodeTypes}
                onChange={setSelectedNodeTypes}
                placeholder="Select node types to display"
                searchable
                clearable
                sx={{ flex: 1 }}
              />
              
              <Button
                leftIcon={<IconFilter size={16} />}
                onClick={() => onFilterNodesByType(selectedNodeTypes)}
                disabled={selectedNodeTypes.length === 0}
                variant="outline"
              >
                Apply Filter
              </Button>
            </Group>
            
            <Text size="xs" color="dimmed">
              Example queries:
            </Text>
            <Text size="xs" color="dimmed">
              • MATCH (n:Class) RETURN n LIMIT 50
            </Text>
            <Text size="xs" color="dimmed">
              • MATCH (n)-[r:IMPORTS]-{'>'}(m) RETURN n, r, m LIMIT 100
            </Text>
            <Text size="xs" color="dimmed">
              • MATCH (n:Function) WHERE n.name CONTAINS 'main' RETURN n
            </Text>
          </Stack>
        </Collapse>
      </Stack>
    </Card>
  );
};

export default GraphControls;