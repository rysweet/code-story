import React, { useState, useEffect } from 'react';
import { Box, Title, Grid, Text, Stack } from '@mantine/core';
import { useDispatch } from 'react-redux';
import { setActivePage } from '../store/slices/uiSlice';
import {
  McpPlayground,
  TemplateSelector,
  ToolCallHistory
} from '../components/mcp';
import { SavedToolCallTemplate, ToolCallHistoryItem } from '../store';

/**
 * McpPage component for MCP tool playground
 */
const McpPage: React.FC = () => {
  const dispatch = useDispatch();

  // Template and history handling - these would be passed to child components
  const [selectedTemplate, setSelectedTemplate] = useState<SavedToolCallTemplate | null>(null);
  const [selectedHistoryItem, setSelectedHistoryItem] = useState<ToolCallHistoryItem | null>(null);

  // Set active page when component mounts
  useEffect(() => {
    dispatch(setActivePage('mcp'));
  }, [dispatch]);

  // Handle template selection
  const handleSelectTemplate = (template: SavedToolCallTemplate) => {
    setSelectedTemplate(template);
    // This will be used in McpPlayground through props
  };

  // Handle history item selection
  const handleSelectHistoryItem = (historyItem: ToolCallHistoryItem) => {
    setSelectedHistoryItem(historyItem);
    // This will be used in McpPlayground through props
  };

  return (
    <Box p="md">
      <Stack spacing="md">
        <Title order={2}>MCP Playground</Title>

        <Text color="dimmed">
          Use the MCP Playground to execute tool calls and interact with the Code Story graph
          and services programmatically.
        </Text>

        <Grid>
          {/* Main playground area */}
          <Grid.Col xs={12} md={7}>
            <McpPlayground
              selectedTemplate={selectedTemplate}
              selectedHistoryItem={selectedHistoryItem}
              onAfterSelect={() => {
                // Reset selection state after it's been applied
                setSelectedTemplate(null);
                setSelectedHistoryItem(null);
              }}
            />
          </Grid.Col>

          {/* Sidebar with templates and history */}
          <Grid.Col xs={12} md={5}>
            <Stack spacing="md">
              <TemplateSelector onSelectTemplate={handleSelectTemplate} />
              <ToolCallHistory onSelectHistoryItem={handleSelectHistoryItem} />
            </Stack>
          </Grid.Col>
        </Grid>
      </Stack>
    </Box>
  );
};

export default McpPage;