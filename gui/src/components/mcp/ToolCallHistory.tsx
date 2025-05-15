import React from 'react';
import {
  Card,
  Text,
  Stack,
  Group,
  Button,
  Loader,
  Alert,
  Badge,
  Divider,
  ScrollArea,
  Timeline,
  ActionIcon,
  Menu,
  Tooltip,
} from '@mantine/core';
import { 
  IconHistory, 
  IconAlertCircle, 
  IconClock, 
  IconRefresh,
  IconCheck,
  IconX,
  IconDotsVertical,
  IconUsb,
  IconCopy,
  IconTrash,
} from '@tabler/icons-react';
import { useGetToolCallHistoryQuery, ToolCallHistoryItem } from '../../store';
import { formatDate } from '../../utils/formatters';

interface ToolCallHistoryProps {
  onSelectHistoryItem: (historyItem: ToolCallHistoryItem) => void;
}

/**
 * Component for displaying tool call history
 */
const ToolCallHistory: React.FC<ToolCallHistoryProps> = ({ onSelectHistoryItem }) => {
  // Get history
  const { 
    data: history, 
    isLoading, 
    error, 
    refetch 
  } = useGetToolCallHistoryQuery();
  
  // Format parameters for display
  const formatParameters = (parameters: Record<string, any>) => {
    try {
      return JSON.stringify(parameters);
    } catch (e) {
      return 'Error formatting parameters';
    }
  };
  
  // Get status icon
  const getStatusIcon = (historyItem: ToolCallHistoryItem) => {
    if (historyItem.error) {
      return <IconX size={16} color="red" />;
    }
    return <IconCheck size={16} color="green" />;
  };
  
  // Show loading state
  if (isLoading) {
    return (
      <Card shadow="sm" radius="md" p="md" withBorder>
        <Stack align="center" py="md">
          <Loader />
          <Text>Loading tool call history...</Text>
        </Stack>
      </Card>
    );
  }
  
  // Show error state
  if (error) {
    return (
      <Card shadow="sm" radius="md" p="md" withBorder>
        <Alert 
          icon={<IconAlertCircle size={16} />} 
          title="Error" 
          color="red"
        >
          Failed to load tool call history
        </Alert>
      </Card>
    );
  }
  
  // Show empty state
  if (!history || history.length === 0) {
    return (
      <Card shadow="sm" radius="md" p="md" withBorder>
        <Stack align="center" py="md">
          <IconHistory size={32} opacity={0.5} />
          <Text color="dimmed">No tool call history</Text>
          <Text size="sm" color="dimmed">
            Your tool call history will appear here
          </Text>
        </Stack>
      </Card>
    );
  }
  
  return (
    <Card shadow="sm" radius="md" p="md" withBorder>
      <Stack spacing="md">
        <Group position="apart">
          <Text weight={500} size="lg">Tool Call History</Text>
          
          <Group spacing={5}>
            <Badge>{history.length}</Badge>
            <Tooltip label="Refresh">
              <ActionIcon size="sm" onClick={() => refetch()}>
                <IconRefresh size={16} />
              </ActionIcon>
            </Tooltip>
          </Group>
        </Group>
        
        <Divider />
        
        <ScrollArea h={400}>
          <Timeline>
            {history.map((item) => (
              <Timeline.Item
                key={item.id}
                title={
                  <Group spacing={5}>
                    <Text weight={500}>{item.tool}</Text>
                    <Badge size="xs" color={item.error ? 'red' : 'green'}>
                      {item.error ? 'Failed' : 'Success'}
                    </Badge>
                  </Group>
                }
                bullet={<IconUsb size={16} />}
                lineVariant={item.error ? 'dashed' : 'solid'}
              >
                <Text size="xs" color="dimmed">
                  <IconClock size={12} style={{ display: 'inline', marginRight: 5 }} />
                  {formatDate(item.timestamp)}
                </Text>
                
                <Text size="sm" mt={5}>
                  Parameters: {formatParameters(item.parameters)}
                </Text>
                
                <Group position="apart" mt={10}>
                  <Button
                    size="xs"
                    variant="light"
                    onClick={() => onSelectHistoryItem(item)}
                  >
                    Reuse
                  </Button>
                  
                  <Menu position="bottom-end" shadow="md">
                    <Menu.Target>
                      <ActionIcon>
                        <IconDotsVertical size={16} />
                      </ActionIcon>
                    </Menu.Target>
                    
                    <Menu.Dropdown>
                      <Menu.Item 
                        icon={<IconCopy size={16} />}
                        onClick={() => onSelectHistoryItem(item)}
                      >
                        Copy to Playground
                      </Menu.Item>
                    </Menu.Dropdown>
                  </Menu>
                </Group>
              </Timeline.Item>
            ))}
          </Timeline>
        </ScrollArea>
      </Stack>
    </Card>
  );
};

export default ToolCallHistory;