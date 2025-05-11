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
  ActionIcon,
  Menu,
  Tooltip,
  ScrollArea,
  Divider,
} from '@mantine/core';
import { 
  IconTemplate, 
  IconTrash, 
  IconDotsVertical, 
  IconAlertCircle,
  IconStar,
} from '@tabler/icons-react';
import { useGetSavedTemplatesQuery, useDeleteTemplateMutation, SavedToolCallTemplate } from '../../store';

interface TemplateSelectorProps {
  onSelectTemplate: (template: SavedToolCallTemplate) => void;
}

/**
 * Component for selecting saved tool call templates
 */
const TemplateSelector: React.FC<TemplateSelectorProps> = ({ onSelectTemplate }) => {
  // Get saved templates
  const { 
    data: templates, 
    isLoading, 
    error 
  } = useGetSavedTemplatesQuery();
  
  // Delete template
  const [deleteTemplate, { isLoading: isDeleting }] = useDeleteTemplateMutation();
  
  // Handle delete template
  const handleDelete = async (templateId: string) => {
    try {
      await deleteTemplate(templateId);
    } catch (error) {
      console.error('Failed to delete template:', error);
    }
  };
  
  // Show loading state
  if (isLoading) {
    return (
      <Card shadow="sm" radius="md" p="md" withBorder>
        <Stack align="center" py="md">
          <Loader />
          <Text>Loading saved templates...</Text>
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
          Failed to load saved templates
        </Alert>
      </Card>
    );
  }
  
  // Show empty state
  if (!templates || templates.length === 0) {
    return (
      <Card shadow="sm" radius="md" p="md" withBorder>
        <Stack align="center" py="md">
          <IconTemplate size={32} opacity={0.5} />
          <Text color="dimmed">No saved templates</Text>
          <Text size="sm" color="dimmed">
            Save your frequently used tool calls as templates for quick access
          </Text>
        </Stack>
      </Card>
    );
  }
  
  return (
    <Card shadow="sm" radius="md" p="md" withBorder>
      <Stack spacing="md">
        <Group position="apart">
          <Text weight={500} size="lg">Saved Templates</Text>
          <Badge>{templates.length}</Badge>
        </Group>
        
        <Divider />
        
        <ScrollArea h={300}>
          <Stack spacing="sm">
            {templates.map((template) => (
              <Card key={template.id} p="xs" radius="sm" withBorder>
                <Group position="apart" noWrap>
                  <Stack spacing={4}>
                    <Group spacing={5}>
                      <IconStar size={14} />
                      <Text weight={500} lineClamp={1}>
                        {template.name}
                      </Text>
                    </Group>
                    
                    <Group spacing={5}>
                      <Badge size="xs" color="blue">
                        {template.tool}
                      </Badge>
                      
                      {template.description && (
                        <Text size="xs" color="dimmed" lineClamp={1}>
                          {template.description}
                        </Text>
                      )}
                    </Group>
                  </Stack>
                  
                  <Group spacing={4} noWrap>
                    <Button
                      size="xs"
                      compact
                      variant="light"
                      onClick={() => onSelectTemplate(template)}
                    >
                      Load
                    </Button>
                    
                    <Menu position="bottom-end" shadow="md">
                      <Menu.Target>
                        <ActionIcon>
                          <IconDotsVertical size={16} />
                        </ActionIcon>
                      </Menu.Target>
                      
                      <Menu.Dropdown>
                        <Menu.Item 
                          icon={<IconTrash size={16} />}
                          color="red"
                          onClick={() => handleDelete(template.id)}
                          disabled={isDeleting}
                        >
                          Delete
                        </Menu.Item>
                      </Menu.Dropdown>
                    </Menu>
                  </Group>
                </Group>
              </Card>
            ))}
          </Stack>
        </ScrollArea>
      </Stack>
    </Card>
  );
};

export default TemplateSelector;