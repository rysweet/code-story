import React from 'react';
import { Card, Title, Text, Group, Stack, Badge, Divider, JsonInput, Button } from '@mantine/core';
import { IconArrowRight, IconX } from '@tabler/icons-react';
import { GraphNode } from '../../utils/graph';

interface NodeDetailsProps {
  node: GraphNode | null;
  onClose: () => void;
  onNavigateToNode?: (nodeId: string) => void;
}

/**
 * Component to display detailed information about a graph node
 */
const NodeDetails: React.FC<NodeDetailsProps> = ({ node, onClose, onNavigateToNode }) => {
  if (!node) return null;
  
  // Function to render properties based on their type
  const renderProperty = (key: string, value: any) => {
    if (value === null || value === undefined) {
      return <Text color="dimmed">null</Text>;
    }
    
    if (typeof value === 'boolean') {
      return <Badge color={value ? 'green' : 'red'}>{value.toString()}</Badge>;
    }
    
    if (typeof value === 'number') {
      return <Text>{value}</Text>;
    }
    
    if (typeof value === 'object') {
      return (
        <JsonInput
          value={JSON.stringify(value, null, 2)}
          readOnly
          autosize
          minRows={3}
          maxRows={10}
        />
      );
    }
    
    // String values that might be links to other nodes
    if (typeof value === 'string' && key.endsWith('_id')) {
      return (
        <Group spacing="xs">
          <Text>{value}</Text>
          {onNavigateToNode && (
            <Button 
              variant="subtle" 
              size="xs" 
              compact 
              onClick={() => onNavigateToNode(value)}
              rightIcon={<IconArrowRight size={12} />}
            >
              Go
            </Button>
          )}
        </Group>
      );
    }
    
    return <Text>{String(value)}</Text>;
  };
  
  return (
    <Card shadow="md" radius="md" p="md" withBorder>
      <Card.Section withBorder inheritPadding py="md">
        <Group position="apart">
          <Title order={4}>{node.name || 'Unnamed'}</Title>
          <Button 
            variant="subtle" 
            color="gray" 
            p={0} 
            style={{ width: 24, height: 24 }} 
            onClick={onClose}
          >
            <IconX size={18} />
          </Button>
        </Group>
      </Card.Section>
      
      <Stack spacing="md" mt="md">
        <Group spacing="sm">
          <Text weight={500}>Type:</Text>
          <Badge size="lg" color="blue">{node.type}</Badge>
        </Group>
        
        {node.path && (
          <Group spacing="sm">
            <Text weight={500}>Path:</Text>
            <Text size="sm" style={{ wordBreak: 'break-all' }}>
              {node.path}
            </Text>
          </Group>
        )}
        
        <Divider label="Properties" labelPosition="center" />
        
        <Stack spacing="sm">
          {Object.entries(node.properties || {})
            .filter(([key]) => !['name', 'type', 'path'].includes(key))
            .map(([key, value]) => (
              <Group key={key} position="apart">
                <Text size="sm" weight={500}>{key}:</Text>
                <div style={{ maxWidth: '60%' }}>
                  {renderProperty(key, value)}
                </div>
              </Group>
            ))}
        </Stack>
      </Stack>
    </Card>
  );
};

export default NodeDetails;