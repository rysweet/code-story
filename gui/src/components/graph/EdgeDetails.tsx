import React from 'react';
import { Card, Title, Text, Group, Stack, Badge, Divider, JsonInput, Button } from '@mantine/core';
import { IconArrowRight, IconX } from '@tabler/icons-react';
import { GraphLink } from '../../utils/graph';

interface EdgeDetailsProps {
  edge: GraphLink | null;
  onClose: () => void;
  onNavigateToNode?: (nodeId: string) => void;
}

/**
 * Component to display detailed information about a graph edge
 */
const EdgeDetails: React.FC<EdgeDetailsProps> = ({ edge, onClose, onNavigateToNode }) => {
  if (!edge) return null;
  
  return (
    <Card shadow="md" radius="md" p="md" withBorder>
      <Card.Section withBorder inheritPadding py="md">
        <Group position="apart">
          <Title order={4}>{edge.type || 'Relationship'}</Title>
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
          <Badge size="lg" color="violet">{edge.type}</Badge>
        </Group>
        
        <Group spacing="sm">
          <Text weight={500}>Source:</Text>
          <Text>{edge.source}</Text>
          {onNavigateToNode && (
            <Button 
              variant="subtle" 
              size="xs" 
              compact 
              onClick={() => onNavigateToNode(edge.source)}
              rightIcon={<IconArrowRight size={12} />}
            >
              Go
            </Button>
          )}
        </Group>
        
        <Group spacing="sm">
          <Text weight={500}>Target:</Text>
          <Text>{edge.target}</Text>
          {onNavigateToNode && (
            <Button 
              variant="subtle" 
              size="xs" 
              compact 
              onClick={() => onNavigateToNode(edge.target)}
              rightIcon={<IconArrowRight size={12} />}
            >
              Go
            </Button>
          )}
        </Group>
        
        <Divider label="Properties" labelPosition="center" />
        
        <Stack spacing="sm">
          {Object.entries(edge.properties || {}).length > 0 ? (
            Object.entries(edge.properties || {}).map(([key, value]) => (
              <Group key={key} position="apart">
                <Text size="sm" weight={500}>{key}:</Text>
                <div style={{ maxWidth: '60%' }}>
                  {typeof value === 'object' ? (
                    <JsonInput
                      value={JSON.stringify(value, null, 2)}
                      readOnly
                      autosize
                      minRows={3}
                      maxRows={10}
                    />
                  ) : (
                    <Text>{String(value)}</Text>
                  )}
                </div>
              </Group>
            ))
          ) : (
            <Text color="dimmed" align="center">No properties</Text>
          )}
        </Stack>
      </Stack>
    </Card>
  );
};

export default EdgeDetails;