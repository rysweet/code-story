import React, { useState, useEffect } from 'react';
import {
  Card,
  Text,
  Select,
  Button,
  Group,
  Stack,
  Loader,
  Alert,
  TextInput,
  Divider,
  ActionIcon,
  Tooltip,
  Modal,
} from '@mantine/core';
import { IconSend, IconSave, IconAlertCircle, IconInfoCircle } from '@tabler/icons-react';
import {
  useExecuteToolMutation,
  useGetAvailableToolsQuery,
  useSaveToolCallTemplateMutation,
  ToolCall,
  SavedToolCallTemplate,
  ToolCallHistoryItem
} from '../../store';
import McpParameterForm from './McpParameterForm';
import ResponseViewer from './ResponseViewer';

interface McpPlaygroundProps {
  selectedTemplate?: SavedToolCallTemplate | null;
  selectedHistoryItem?: ToolCallHistoryItem | null;
  onAfterSelect?: () => void;
}

/**
 * Component for MCP tool call playground
 */
const McpPlayground: React.FC<McpPlaygroundProps> = ({
  selectedTemplate,
  selectedHistoryItem,
  onAfterSelect,
}) => {
  // State
  const [selectedTool, setSelectedTool] = useState<string | null>(null);
  const [parameters, setParameters] = useState<Record<string, any>>({});
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [templateName, setTemplateName] = useState('');
  const [templateDescription, setTemplateDescription] = useState('');
  
  // Tool call execution
  const [executeTool, { isLoading, data: response, error, reset }] = useExecuteToolMutation();
  
  // Get available tools
  const { 
    data: availableTools, 
    isLoading: isLoadingTools, 
    error: toolsError 
  } = useGetAvailableToolsQuery();
  
  // Save template
  const [saveTemplate, { isLoading: isSaving, error: saveError }] = useSaveToolCallTemplateMutation();
  
  // Get tool schema
  const getToolSchema = () => {
    if (!availableTools || !selectedTool) return null;
    return availableTools.tools.find(tool => tool.name === selectedTool);
  };
  
  // Reset parameters when tool changes
  useEffect(() => {
    setParameters({});
    reset();
  }, [selectedTool, reset]);

  // Handle selected template
  useEffect(() => {
    if (selectedTemplate) {
      setSelectedTool(selectedTemplate.tool);
      setParameters(selectedTemplate.parameters);

      // Notify parent that we've handled the selection
      if (onAfterSelect) {
        onAfterSelect();
      }
    }
  }, [selectedTemplate, onAfterSelect]);

  // Handle selected history item
  useEffect(() => {
    if (selectedHistoryItem) {
      setSelectedTool(selectedHistoryItem.tool);
      setParameters(selectedHistoryItem.parameters);

      // Notify parent that we've handled the selection
      if (onAfterSelect) {
        onAfterSelect();
      }
    }
  }, [selectedHistoryItem, onAfterSelect]);
  
  // Handle parameter changes
  const handleParameterChange = (name: string, value: any) => {
    setParameters(prev => ({
      ...prev,
      [name]: value,
    }));
  };
  
  // Execute tool call
  const handleExecute = async () => {
    if (!selectedTool) return;
    
    const toolCall: ToolCall = {
      tool: selectedTool,
      parameters,
    };
    
    try {
      await executeTool(toolCall);
    } catch (error) {
      console.error('Failed to execute tool call:', error);
    }
  };
  
  // Save as template
  const handleSaveTemplate = async () => {
    if (!selectedTool || !templateName) return;
    
    try {
      await saveTemplate({
        id: `template_${Date.now()}`,
        name: templateName,
        description: templateDescription,
        tool: selectedTool,
        parameters,
      });
      
      setShowSaveModal(false);
      setTemplateName('');
      setTemplateDescription('');
    } catch (error) {
      console.error('Failed to save template:', error);
    }
  };
  
  // Generate tool options
  const toolOptions = availableTools?.tools.map(tool => ({
    value: tool.name,
    label: tool.name,
  })) || [];
  
  // Get current tool schema
  const currentToolSchema = getToolSchema();
  
  return (
    <Stack spacing="md">
      <Card shadow="sm" radius="md" p="md" withBorder>
        <Stack spacing="md">
          <Text weight={500} size="lg">MCP Tool Playground</Text>
          
          {/* Tool selection */}
          <Select
            label="Select Tool"
            placeholder="Choose a tool to execute"
            data={toolOptions}
            value={selectedTool}
            onChange={setSelectedTool}
            searchable
            nothingFound="No tools available"
            disabled={isLoadingTools}
            error={toolsError ? 'Failed to load tools' : undefined}
            rightSection={isLoadingTools ? <Loader size="xs" /> : null}
          />
          
          {/* Tool description */}
          {currentToolSchema && (
            <Alert 
              icon={<IconInfoCircle size={16} />} 
              color="blue" 
              variant="light"
            >
              {currentToolSchema.description}
            </Alert>
          )}
          
          {/* Parameters form */}
          {currentToolSchema && (
            <>
              <Divider label="Parameters" labelPosition="center" />
              <McpParameterForm
                parameters={currentToolSchema.parameters}
                values={parameters}
                onChange={handleParameterChange}
              />
            </>
          )}
          
          {/* Execute button */}
          <Group position="apart">
            <Button
              leftIcon={<IconSend size={16} />}
              onClick={handleExecute}
              loading={isLoading}
              disabled={!selectedTool}
            >
              Execute Tool
            </Button>
            
            <Tooltip label="Save as template">
              <ActionIcon
                onClick={() => setShowSaveModal(true)}
                disabled={!selectedTool}
                variant="light"
                color="blue"
              >
                <IconSave size={16} />
              </ActionIcon>
            </Tooltip>
          </Group>
          
          {/* Error message */}
          {error && (
            <Alert 
              icon={<IconAlertCircle size={16} />} 
              title="Error" 
              color="red"
            >
              {JSON.stringify(error)}
            </Alert>
          )}
        </Stack>
      </Card>
      
      {/* Response viewer */}
      {response && (
        <Card shadow="sm" radius="md" p="md" withBorder>
          <Stack spacing="md">
            <Text weight={500} size="lg">Response</Text>
            <ResponseViewer response={response} />
          </Stack>
        </Card>
      )}
      
      {/* Save template modal */}
      <Modal
        opened={showSaveModal}
        onClose={() => setShowSaveModal(false)}
        title="Save as Template"
      >
        <Stack spacing="md">
          <TextInput
            label="Template Name"
            placeholder="Enter a name for this template"
            value={templateName}
            onChange={(e) => setTemplateName(e.target.value)}
            required
          />
          
          <TextInput
            label="Description (Optional)"
            placeholder="Enter a description for this template"
            value={templateDescription}
            onChange={(e) => setTemplateDescription(e.target.value)}
          />
          
          {saveError && (
            <Alert 
              icon={<IconAlertCircle size={16} />} 
              title="Error" 
              color="red"
            >
              {JSON.stringify(saveError)}
            </Alert>
          )}
          
          <Group position="right">
            <Button variant="outline" onClick={() => setShowSaveModal(false)}>
              Cancel
            </Button>
            
            <Button 
              onClick={handleSaveTemplate} 
              loading={isSaving}
              disabled={!templateName}
            >
              Save Template
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
};

export default McpPlayground;